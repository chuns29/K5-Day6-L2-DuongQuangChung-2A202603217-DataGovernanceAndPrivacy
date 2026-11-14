"""T06 release gate. Run through python -m src.main."""

from collections import Counter
from math import isfinite
from pathlib import Path

import pandas as pd

from .common.contact_sheet import render_contact_sheet
from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.io import read_json, sha256_file, write_json
from .common.manifest import verify_manifest
from .common.review import (
    apply_overrides,
    load_review_decisions,
    make_review_queue,
    write_review_queue,
)
from .examples.t06_baseline import check_release


def load(ctx: RunContext) -> dict:
    root = ctx.input_dir
    manifest = root / "manifest.csv"
    problems = verify_manifest(manifest) if manifest.is_file() else [{"problem": "no_manifest"}]
    if problems:
        ctx.audit.log("pipeline", "provenance_problems", str(manifest), after=problems[:20])
        if ctx.config.get("strict_provenance", True):
            raise ValueError(f"Input manifest failed verification: {problems[:3]}")

    parent = root / ctx.param("parent_release", "releases/v1.0")
    parent_file = parent / "annotations.json"
    releases = pd.read_csv(root / "releases.csv", dtype=str)
    if releases.empty or releases.release_id.isna().any() or releases.release_id.duplicated().any():
        raise ValueError("releases.csv must contain unique release IDs")
    return {
        "releases": releases,
        "parent": read_json(parent_file),
        "parent_meta": read_json(parent / "release_meta.json"),
        "parent_hash": sha256_file(parent_file),
        "label_maps": read_json(root / "releases/label_maps.json"),
    }


def valid_box(box, image):
    if not isinstance(box, list) or len(box) != 4:
        return False
    if not all(type(value) in (int, float) and isfinite(value) for value in box):
        return False
    x, y, width, height = box
    return (
        x >= -0.02 and y >= -0.02 and width > 0 and height > 0
        and x + width <= image["width"] + 0.02
        and y + height <= image["height"] + 0.02
    )


def inspect_release(root, relative_path, data, shift_px):
    path = root / relative_path
    parent = data["parent"]
    expected_version = data["parent_meta"]["label_map_version"]
    expected_map = data["label_maps"][expected_version]
    findings = []

    def record(code, detail, **evidence):
        findings.append({"code": code, "detail": detail, **evidence})

    try:
        check_release(root, path)
        candidate = read_json(path / "annotations.json")
        meta = read_json(path / "release_meta.json")
    except (OSError, ValueError) as exc:
        record("input_invalid", str(exc))
        return findings

    if (
        meta["parent_version"] != data["parent_meta"]["version"]
        or meta["parent_sha256"] != data["parent_hash"]
    ):
        record("parent_mismatch", "Parent version or SHA-256 differs",
               expected=data["parent_hash"], actual=meta["parent_sha256"])

    for section in ("images", "annotations", "categories"):
        ids = [row["id"] for row in candidate[section]]
        if any(type(item) is not int for item in ids):
            record("input_invalid", f"{section} IDs must be integers")
            return findings
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        if duplicates:
            record("id_collision", f"Duplicate IDs in {section}: {duplicates[:5]}",
                   ids=duplicates)

    names = {str(row["id"]): row["name"] for row in candidate["categories"]}
    if meta["label_map_version"] != expected_version or set(expected_map) - names.keys():
        record("stale_map", "Label map version differs or expected classes are missing",
               expected_version=expected_version, actual_version=meta["label_map_version"],
               missing_ids=sorted(set(expected_map) - names.keys()))
    swapped = [
        {"category_id": key, "before": expected_map[key], "after": name}
        for key, name in names.items() if key in expected_map and name != expected_map[key]
    ]
    if swapped:
        record("class_swap", f"Category meanings changed: {swapped}", changes=swapped)

    images = {row["id"]: row for row in candidate["images"]}
    missing = [row for row in parent["images"] if row["id"] not in images]
    if missing:
        record("dropped_frames", f"{len(missing)} parent frames are absent",
               image_ids=[row["id"] for row in missing], image=missing[0]["file_name"])

    old_annotations = {row["id"]: row for row in parent["annotations"]}
    changes = {"class_swap": [], "bbox_shift": [], "input_invalid": []}
    for row in candidate["annotations"]:
        image = images.get(row["image_id"])
        if image is None:
            changes["dropped_frames"] = changes.get("dropped_frames", []) + [
                {"annotation_id": row["id"], "image_id": row["image_id"]}
            ]
            continue
        previous = old_annotations.get(row["id"])
        box = row["bbox"]
        evidence = {
            "annotation_id": row["id"], "image": image["file_name"],
            "before_class": previous["category_id"] if previous else None,
            "after_class": row["category_id"],
            "before_box": previous["bbox"] if previous else None, "after_box": box,
        }
        if str(row["category_id"]) not in names:
            changes["stale_map"] = changes.get("stale_map", []) + [evidence]
        if not valid_box(box, image):
            changes["bbox_shift"].append(evidence)
        if previous is None or previous["image_id"] != row["image_id"]:
            continue
        if previous["category_id"] != row["category_id"]:
            changes["class_swap"].append(evidence)
        if valid_box(box, image) and max(abs(a - b) for a, b in zip(previous["bbox"], box)) > shift_px:
            changes["bbox_shift"].append(evidence)

    for code, rows in changes.items():
        if rows:
            record(code, f"{len(rows)} annotations flagged for {code}",
                   examples=rows[:10], image=rows[0].get("image", ""))
    return findings


PRIORITY = (
    "input_invalid", "parent_mismatch", "id_collision", "dropped_frames",
    "stale_map", "class_swap", "bbox_shift",
)


def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    shift_px = float(ctx.param("bbox_shift_px", 5.0))
    if not isfinite(shift_px) or shift_px < 0:
        raise ValueError("bbox_shift_px must be finite and nonnegative")
    rows = []
    evidence = {}
    for release in data["releases"].itertuples(index=False):
        path = Path(release.path)
        if path.anchor or ".." in path.parts:
            raise ValueError(f"Invalid candidate path: {release.path}")
        findings = inspect_release(ctx.input_dir, path, data, shift_px)
        findings.sort(key=lambda finding: PRIORITY.index(finding["code"]))
        evidence[release.release_id] = {"path": release.path, "findings": findings}
        rows.append({
            "release_id": release.release_id,
            "decision": "HOLD" if findings else "PASS",
            "root_cause": findings[0]["code"] if findings else "clean",
            "score": len({finding["code"] for finding in findings}),
            "reason": f"{release.path}: " + (
                "; ".join(finding["detail"] for finding in findings) if findings else "Checks passed"
            ),
            "image": next((finding["image"] for finding in findings if finding.get("image")), ""),
            "split": release.split,
        })
    write_json(ctx.out("rework_report.json"), evidence)
    return pd.DataFrame(rows)


def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    budget = int(ctx.param("budget", 20))
    if budget < 0:
        raise ValueError("Review budget must be nonnegative")
    queue = make_review_queue(
        scored, "release_id", "score", budget,
        reason_col="reason", action_col="decision", slice_col="split", evidence_col="image",
    )
    write_review_queue(queue, ctx.out("review_queue.csv"))
    render_contact_sheet(queue, ctx.out("contact_sheet.html"), image_root=ctx.input_dir,
                         title="T06 release review")
    return queue


def review(ctx: RunContext, scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    path = ctx.output_dir / "review_queue_reviewed.csv"
    if not path.exists():
        return scored
    reviewed = load_review_decisions(path)
    if reviewed.item_id.duplicated().any() or not set(reviewed.item_id) <= set(queue.item_id):
        raise ValueError("Reviewed rows must refer to distinct IDs in the current review queue")

    for row in reviewed.itertuples():
        action = row.reviewer_decision
        if action in {"approve", "skip"}:
            ctx.audit.log(row.reviewer, action, row.item_id, reason=row.review_note)
            continue
        value = row.override_value.strip().upper()
        if action == "reject":
            value = value or "REWORK"
        if action == "escalate":
            value = "HOLD"
        if value not in {"PASS", "HOLD", "REWORK"}:
            raise ValueError(f"{row.item_id}: override must be PASS, HOLD or REWORK")
        reviewed.loc[row.Index, ["reviewer_decision", "override_value"]] = ["edit", value]
    ctx.stats["n_reviewed"] = len(reviewed)
    final = apply_overrides(scored, reviewed, "release_id", "decision", ctx.audit)
    final.loc[final.decision.eq("PASS"), "root_cause"] = "clean"
    final.loc[final.decision.ne("PASS") & final.root_cause.eq("clean"), "root_cause"] = "manual_review"
    return final


def decide(ctx: RunContext, final: pd.DataFrame) -> None:
    output = ctx.out("release_decisions.csv")
    final[["release_id", "decision", "root_cause"]].to_csv(output, index=False)
    blocked = int(final.decision.ne("PASS").sum())
    write_decision(
        Decision(
            status="HOLD" if blocked else "PASS",
            reason_code="CANDIDATES_BLOCKED" if blocked else "ALL_CANDIDATES_PASSED",
            reason=f"{blocked} of {len(final)} candidates need review or rework.",
            owner=ctx.config["owner"],
            scope=ctx.track,
            evidence=[str(output), str(ctx.out("rework_report.json"))],
        ),
        ctx.out("decision.json"),
        ctx.out("decision_log.csv"),
    )


def run(ctx: RunContext) -> None:
    if ctx.track != "t06":
        raise NotImplementedError(f"This pipeline implements T06 (requested {ctx.track})")
    scored = process(ctx, load(ctx))
    ctx.stats["n_items"] = len(scored)
    queue = rank(ctx, scored)
    decide(ctx, review(ctx, scored, queue))
