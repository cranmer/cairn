"""The three fictional fixture projects used by the multi-user/multi-cairn
methodology. Each instance below is the machine-readable counterpart of one
section of ``tests/agent_smoke/multi-user-multi-cairn/fixtures/README.md``.

If you update one, update the other in the same commit.
"""

from __future__ import annotations

from .fixtures import (
    Fixture,
    FixtureCollaborator,
    FixtureCommit,
    FixtureDecision,
    FixtureFile,
    FixtureFinding,
    FixtureQuestion,
)

_CORAL_BLEACH = Fixture(
    name="coral-bleach",
    project_files=[
        FixtureFile(
            relpath="README.md",
            content="""\
            # coral-bleach

            Marine biology group monitoring coral cover at three transect sites
            in the Coral Triangle.

            TODO:
            - Decide on the 2018 baseline window.
            - Backfill missing 2022 transect.
            """,
        ),
        FixtureFile(
            relpath="analysis/transect_summary.py",
            content='''\
            """Computes coral cover percentages from raw transect rows."""

            from __future__ import annotations
            import csv

            def cover_pct(rows: list[dict]) -> float:
                return sum(float(r["cover_pct"]) for r in rows) / max(len(rows), 1)

            if __name__ == "__main__":
                with open("data/transects-2024.csv") as fh:
                    rows = list(csv.DictReader(fh))
                print(cover_pct(rows))
            ''',
        ),
        FixtureFile(
            relpath="data/transects-2024.csv",
            content="""\
            site,date,cover_pct
            T1,2024-03-12,42
            T2,2024-03-13,38
            T3,2024-03-14,30
            T1,2024-09-20,40
            T3,2024-09-21,28
            """,
        ),
    ],
    commits=[
        FixtureCommit(
            author_name="Kyle",
            author_email="kyle@example.com",
            message="initial transect summary skeleton",
            files=["README.md", "analysis/transect_summary.py"],
        ),
        FixtureCommit(
            author_name="Lila",
            author_email="lila@example.com",
            message="add 2024 transect data",
            files=["data/transects-2024.csv"],
        ),
    ],
    collaborators=[
        FixtureCollaborator(id="kyle", name="Kyle", role="PI", email="kyle@example.com"),
        FixtureCollaborator(id="lila", name="Lila", role="postdoc", email="lila@example.com"),
    ],
    decisions=[
        FixtureDecision(
            text="Adopt PIT-tagged colonies as the primary monitoring unit.",
            author="kyle",
            context=(
                "Replaces ad-hoc transect labels; tags give unambiguous identity across years."
            ),
        ),
    ],
    questions=[
        FixtureQuestion(
            id="Q-001",
            question=("Should 2018 baseline use pre-bleach or post-bleach surveys?"),
            raised_by="lila",
        ),
    ],
    findings=[
        FixtureFinding(
            slug="bleach-2024-extent",
            title="2024 bleaching event extent across transects",
            author="kyle",
            body=(
                "Stress affected T1 and T3 most heavily; T2 showed partial recovery by September."
            ),
        ),
    ],
)


_LIT_MONITOR = Fixture(
    name="lit-monitor",
    project_files=[
        FixtureFile(
            relpath="README.md",
            content="""\
            # lit-monitor

            Literature-tracking project that watches arXiv and journal RSS for
            coral / bleaching / climate-stress papers.

            What we're tracking:
            - Coral bleaching cycles
            - Transect methodology
            - Climate-stress synthesis reviews
            """,
        ),
        FixtureFile(
            relpath="watchlist.yaml",
            content="""\
            papers:
              - arxiv: "2402.00001"
                title: "Bleaching cycles in the Coral Triangle"
              - arxiv: "2403.00002"
                title: "Transect methodology revisited"
              - arxiv: "2404.00003"
                title: "Climate stress and bleaching frequency"
              - arxiv: "2405.00004"
                title: "Coral cover synthesis review"
            """,
        ),
        FixtureFile(
            relpath="scripts/fetch.py",
            content='''\
            """Stub: would fetch new entries from arXiv + journal RSS."""

            def fetch_new() -> list[dict]:
                return []
            ''',
        ),
    ],
    commits=[
        FixtureCommit(
            author_name="Kyle",
            author_email="kyle@example.com",
            message="initial watchlist",
            files=["README.md", "watchlist.yaml"],
        ),
        FixtureCommit(
            author_name="Priya",
            author_email="priya@example.com",
            message="add fetch stub",
            files=["scripts/fetch.py"],
        ),
    ],
    collaborators=[
        FixtureCollaborator(id="kyle", name="Kyle", role="lead", email="kyle@example.com"),
        FixtureCollaborator(
            id="priya",
            name="Priya",
            role="collaborator (lit search)",
            email="priya@example.com",
        ),
    ],
    decisions=[
        FixtureDecision(
            text="Use arXiv API + journal RSS, not Google Scholar.",
            author="priya",
            context=(
                "Scholar's terms forbid systematic scraping; arXiv + RSS covers our scope cleanly."
            ),
        ),
    ],
    questions=[
        FixtureQuestion(
            id="Q-001",
            question=("Should we track preprints separately from published versions?"),
            raised_by="kyle",
        ),
    ],
    findings=[],
)


_SHARED_PHYSICS = Fixture(
    name="shared-physics-paper",
    project_files=[
        FixtureFile(
            relpath="README.md",
            content="""\
            # shared-physics-paper

            Three-author paper on a measurement of an ungapped Higgs-sector
            observable.

            Authors: Alex (methods), Morgan (analysis), Sam (writeup).
            """,
        ),
        FixtureFile(
            relpath="paper/draft.tex",
            content=r"""\
            \documentclass{article}
            \title{Measurement of the ungapped observable}
            \author{Alex \and Morgan \and Sam}
            \begin{document}
            \maketitle
            \section{Introduction}
            \section{Methods}
            \section{Analysis}
            \section{Results}
            \section{Discussion}
            \end{document}
            """,
        ),
        FixtureFile(
            relpath="analysis/run_fit.py",
            content='''\
            """Stub fit driver — would call the actual minimiser."""

            def run_fit(toys: int = 1000) -> dict:
                return {"converged": True, "n_toys": toys}
            ''',
        ),
    ],
    commits=[
        FixtureCommit(
            author_name="Alex",
            author_email="alex@example.com",
            message="paper skeleton + run_fit stub",
            files=["README.md", "paper/draft.tex", "analysis/run_fit.py"],
        ),
    ],
    collaborators=[
        FixtureCollaborator(
            id="alex",
            name="Alex",
            role="methods lead",
            email="alex@example.com",
        ),
        FixtureCollaborator(
            id="morgan",
            name="Morgan",
            role="analysis lead",
            email="morgan@example.com",
        ),
        FixtureCollaborator(id="sam", name="Sam", role="writeup lead", email="sam@example.com"),
        FixtureCollaborator(
            id="repo-history",
            name="repo history",
            role="ambiguous authorship placeholder",
            type="unknown",
        ),
    ],
    decisions=[
        FixtureDecision(
            text=("Use the V+jets control region for background estimation."),
            author="alex",
            context=(
                "V+jets gives the cleanest extrapolation; alternatives have larger MC dependence."
            ),
        ),
    ],
    questions=[
        FixtureQuestion(
            id="Q-001",
            question=("Are the JER systematics double-counted in the smoothing prescription?"),
            raised_by="morgan",
        ),
    ],
    findings=[
        FixtureFinding(
            slug="fit-converges-on-toys",
            title="Fit converges on toys",
            author="alex",
            body=("No pulls > 2 sigma on the nominal nuisance set; convergence rate 99.4%."),
        ),
    ],
)


FIXTURES: dict[str, Fixture] = {
    "coral-bleach": _CORAL_BLEACH,
    "lit-monitor": _LIT_MONITOR,
    "shared-physics-paper": _SHARED_PHYSICS,
}
