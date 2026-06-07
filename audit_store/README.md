# Audit Store

The active implementation writes per-run hash-chained audit events to
`runs/<run_id>/audit_events.jsonl`.

The fixture CLI also writes a durable run bundle:

- `manifest.json`
- `report.json`
- `claims.jsonl`
- `evidence_spans.jsonl`
- `prompt_log.jsonl`
- `verification.json`
- `release.json`
- `checksums.json`

Use:

```bash
python -m agentic_cfo.cli audit verify runs/<run_id>
```

This directory is reserved for future shared, append-only, or externalized audit-store backends.
