from __future__ import annotations

import json
import subprocess
import sys


def test_agentic_cfo_fixture_cli(tmp_path):
    fixture = tmp_path / "fixture"
    runs_dir = tmp_path / "runs"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agentic_cfo.cli",
            "run-fixture",
            "--fixture",
            str(fixture),
            "--runs-dir",
            str(runs_dir),
            "--run-id",
            "run:test",
            "--create-fixture",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["generation_owner"] == "AgenticCFOControllerAgent"
    assert payload["release_action"] == "release"
    assert payload["audit_valid"] is True
    assert (runs_dir / "run_test" / "audit_events.jsonl").exists()
