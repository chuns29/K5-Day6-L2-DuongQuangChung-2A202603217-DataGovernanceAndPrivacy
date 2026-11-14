from pathlib import Path

import pandas as pd

from src import main as runner


def test_t06_passes_a_dev_release_with_benign_changes(tmp_path):
    assert runner.main(["--track", "t06", "--offline", "--output", str(tmp_path)]) == 0
    decisions = pd.read_csv(tmp_path / "release_decisions.csv").set_index("release_id")
    expected = pd.read_csv(Path("fixtures/t06_release_gate/releases.csv"))
    assert decisions.index.tolist() == expected.release_id.tolist()
    assert decisions.loc["r03", "decision"] == "PASS"


def test_t06_blocks_class_swap_and_audits_reviewer_override(tmp_path):
    assert runner.main(["--track", "t06", "--offline", "--output", str(tmp_path)]) == 0
    output = tmp_path / "release_decisions.csv"
    original = pd.read_csv(output).set_index("release_id")
    assert original.loc["r07", ["decision", "root_cause"]].tolist() == ["HOLD", "class_swap"]
    queue = pd.read_csv(tmp_path / "review_queue.csv", dtype=str).fillna("")
    row = queue.item_id.eq("r07")
    queue.loc[row, ["reviewer", "reviewer_decision", "review_note"]] = [
        "Test reviewer", "reject", "Correct the class map",
    ]
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)
    assert runner.main(["--track", "t06", "--offline", "--output", str(tmp_path)]) == 0
    assert pd.read_csv(output).set_index("release_id").loc["r07", "decision"] == "REWORK"
    assert "Correct the class map" in (tmp_path / "audit_log.jsonl").read_text()
