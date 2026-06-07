from __future__ import annotations

from enum import Enum


class GovernanceRole(str, Enum):
    PREPARER = "Preparer"
    REVIEWER = "Reviewer"
    APPROVER = "Approver"
