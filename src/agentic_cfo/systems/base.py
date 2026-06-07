from __future__ import annotations

from abc import ABC, abstractmethod

from agentic_cfo.core.models import ReportArtifact
from agentic_cfo.data.schema import ReportingCase


class SystemRunner(ABC):
    system_name: str

    @abstractmethod
    def run(self, case: ReportingCase, *, run_id: str) -> ReportArtifact:
        raise NotImplementedError
