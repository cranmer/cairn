"""Validation issue + report types."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Issue:
    file: Path | None
    entity_id: str | None
    message: str
    severity: Severity = "error"

    def render(self) -> str:
        loc = str(self.file) if self.file else "<cairn>"
        eid = f" [{self.entity_id}]" if self.entity_id else ""
        return f"{loc}:{eid} {self.message}"


@dataclass
class ValidationReport:
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        if not self.issues:
            return "OK"
        grouped: dict[str, list[Issue]] = defaultdict(list)
        for issue in self.issues:
            key = str(issue.file) if issue.file else "<cairn>"
            grouped[key].append(issue)
        out: list[str] = []
        for key in sorted(grouped):
            out.append(key)
            for issue in grouped[key]:
                marker = "!" if issue.severity == "error" else "?"
                eid = f" [{issue.entity_id}]" if issue.entity_id else ""
                out.append(f"  {marker}{eid} {issue.message}")
        return "\n".join(out)

    def exit_code(self) -> int:
        return 1 if self.errors else 0
