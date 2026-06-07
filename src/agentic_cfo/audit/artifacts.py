from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from agentic_cfo.core.models import EvidenceSpan, ReleaseDecisionRecord, ReportArtifact, RunManifest, VerificationRecord, stable_hash
from agentic_cfo.provenance.prompts import PromptRecord


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"Cannot serialize {type(value)!r}")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_to_dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_to_dict(row), sort_keys=True, default=str) + "\n")


@dataclass(frozen=True)
class ArtifactBundle:
    run_root: str
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunArtifactStore:
    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.run_root.mkdir(parents=True, exist_ok=True)

    def _checksums(self) -> dict[str, str]:
        checksums = {}
        for path in sorted(self.run_root.iterdir()):
            if path.is_file() and path.name not in {"checksums.json", "audit_events.jsonl"}:
                checksums[path.name] = stable_hash(path.read_text(encoding="utf-8"))
        return checksums

    def write_bundle(
        self,
        *,
        manifest: RunManifest,
        report: ReportArtifact,
        verification: VerificationRecord,
        release: ReleaseDecisionRecord,
        evidence_spans: tuple[EvidenceSpan, ...] = (),
        prompt_records: tuple[PromptRecord, ...] = (),
    ) -> ArtifactBundle:
        _write_json(self.run_root / "manifest.json", manifest)
        _write_json(self.run_root / "report.json", report)
        _write_json(self.run_root / "verification.json", verification)
        _write_json(self.run_root / "release.json", release)
        _write_jsonl(self.run_root / "claims.jsonl", report.claims)
        _write_jsonl(self.run_root / "evidence_spans.jsonl", evidence_spans)
        _write_jsonl(self.run_root / "prompt_log.jsonl", prompt_records)
        checksums = self._checksums()
        (self.run_root / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")
        return ArtifactBundle(run_root=str(self.run_root), files=checksums)

    def verify_bundle(self) -> bool:
        checksum_path = self.run_root / "checksums.json"
        if not checksum_path.exists():
            return False
        expected = json.loads(checksum_path.read_text(encoding="utf-8"))
        return expected == self._checksums()
