"""T06 baseline: JSON structure and file existence checks."""

import json
from pathlib import Path

import pandas as pd

from ..common.decision import Decision, write_decision


COCO_FIELDS = {
    "images": ("id", "file_name", "width", "height"),
    "annotations": ("id", "image_id", "category_id", "bbox"),
    "categories": ("id", "name"),
}
META_FIELDS = {"version", "parent_version", "parent_sha256", "label_map_version"}


def read_object(path):
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return value


def check_release(root, release_path):
    annotations = read_object(release_path / "annotations.json")
    metadata = read_object(release_path / "release_meta.json")
    if not META_FIELDS <= metadata.keys():
        raise ValueError("release_meta.json: missing required fields")

    for section, fields in COCO_FIELDS.items():
        rows = annotations.get(section)
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or not set(fields) <= row.keys() for row in rows
        ):
            raise ValueError(f"annotations.json: invalid {section} structure")

    for image in annotations["images"]:
        filename = image["file_name"]
        if not isinstance(filename, str) or not filename:
            raise ValueError("annotations.json: invalid image filename")
        relative = Path(filename)
        if relative.anchor or ".." in relative.parts:
            raise ValueError(f"annotations.json: invalid image path {filename}")
        if not (root / relative).is_file():
            raise FileNotFoundError(filename)


def run(ctx):
    releases = pd.read_csv(ctx.input_dir / "releases.csv", dtype=str)
    results = []
    for release in releases.itertuples(index=False):
        try:
            check_release(ctx.input_dir, ctx.input_dir / release.path)
        except (OSError, ValueError) as exc:
            results.append((release.release_id, "HOLD", str(exc)))
        else:
            results.append((release.release_id, "PASS", "Basic checks passed"))

    decisions = pd.DataFrame(results, columns=["release_id", "decision", "reason"])
    output = ctx.out("release_decisions.csv")
    decisions.to_csv(output, index=False)
    ctx.stats["n_items"] = len(decisions)
    held = int(decisions["decision"].eq("HOLD").sum())
    write_decision(
        Decision(
            status="HOLD" if held else "PASS",
            reason_code="BASELINE_FILE_OR_SCHEMA_ERROR" if held else "BASELINE_CHECKS_PASSED",
            reason=f"Basic checks held {held} of {len(decisions)} candidates.",
            owner=ctx.config["owner"],
            scope=ctx.track,
            evidence=[str(output)],
        ),
        ctx.out("decision.json"),
    )
