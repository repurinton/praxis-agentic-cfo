# Human Audit Status

## Current Repository Status

The repository implements the human-audit workflow mechanics:

- four-level ordinal rubric,
- blinded sample IDs,
- de-identified reviewer IDs,
- pre-adjudication ratings,
- deterministic adjudication,
- raw agreement,
- weighted Cohen's kappa,
- outcome distributions.

The current `scripts/run_human_audit_demo.py` command and UI human-audit page use synthetic demo ratings. These ratings validate workflow mechanics only.

## Not Included

- Actual CPA reviewer ratings.
- Reviewer credentials or identity records.
- Reviewer assignment logs from a real study.
- IRB/OHR/advisor determination documentation.
- Human-audit source packets reviewed by CPA reviewers.

## Defensible Interpretation

The current human-audit implementation supports claims about the existence and testability of the workflow. It does not support claims about actual CPA reviewer findings or inter-rater reliability from a completed human audit.

## Required Before Final Empirical Claim

Before representing human-audit results as final study evidence, add:

- documented advisor/OHR/IRB status,
- reviewer recruitment/eligibility documentation,
- locked rubric version,
- blinded artifact sample manifest,
- independent reviewer rating files,
- adjudication records,
- final agreement and distribution outputs.
