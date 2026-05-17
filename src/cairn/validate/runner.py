"""Compose individual checks into a single validation report."""

from __future__ import annotations

from ..errors import SchemaError
from ..io.state_io import load_state
from ..paths import CairnPaths
from . import checks
from .report import ValidationReport


def run_all(paths: CairnPaths, *, strict: bool = False) -> ValidationReport:
    """Run every check against the cairn at ``paths``.

    Schema and YAML problems short-circuit the cross-reference checks: there
    is no useful CairnState to build if the YAML doesn't parse or doesn't
    fit the schema. In that case, the report contains the parse/schema
    issues only, and a follow-up `cairn validate` after a fix will surface
    the next layer of problems.
    """
    issues = []
    issues.extend(checks.required_dirs_exist(paths))
    issues.extend(checks.yaml_parses(paths))
    issues.extend(checks.schemas_validate(paths))
    issues.extend(checks.meeting_filenames(paths))

    if not issues:
        try:
            state = load_state(paths)
        except SchemaError as exc:
            from .report import Issue
            issues.append(Issue(file=None, entity_id=None, message=str(exc)))
        else:
            issues.extend(checks.xrefs_resolve(state, paths))
            if strict:
                issues.extend(checks.strict_warnings(state, paths))

    return ValidationReport(issues=issues)
