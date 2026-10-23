"""Real-data completeness audit for one competition's fetched matches —
a diagnostic, never a gate. It reports how close the real data we have is
to a full season, so a gap is visible and logged, but it never blocks a
response: a genuinely postponed or rescheduled match can make the real
expected count differ slightly from the textbook round-robin arithmetic
even when nothing is actually broken, and refusing to answer in that case
would trade a honest "almost complete" view for the exact "show nothing"
problem this project has spent this whole session fixing.
"""

from __future__ import annotations

from dataclasses import dataclass

from sp_core.models import Match, StandingRow

from .history import _is_finished_with_score

EXPECTED_TEAMS: dict[str, int] = {
    "laliga": 20,
    "premier-league": 20,
    "serie-a": 20,
    "ligue-1": 18,
    "bundesliga": 18,
    "champions-league": 36,
    "europa-league": 36,
    "conference-league": 36,
    "segunda": 22,
    "championship": 24,
    "primeira-liga": 18,
    "eredivisie": 18,
}

EXPECTED_MATCHES: dict[str, int] = {
    "laliga": 380,  # 20 teams, double round-robin: 20 × 19
    "premier-league": 380,
    "serie-a": 380,
    "ligue-1": 306,  # 18 teams: 18 × 17
    "bundesliga": 306,
    "champions-league": 144,  # 36 teams × 8 league-phase matchdays ÷ 2
    "europa-league": 144,  # same league-phase format as champions-league
    "conference-league": 108,  # 36 teams × 6 league-phase matchdays ÷ 2
    "segunda": 462,  # 22 teams, double round-robin: 22 × 21
    "championship": 552,  # 24 teams, double round-robin: 24 × 23
    "primeira-liga": 306,  # 18 teams: 18 × 17
    "eredivisie": 306,
}


@dataclass
class CompletenessAudit:
    competition_slug: str
    matches_found: int
    matches_expected: int | None
    teams_found: int
    teams_expected: int | None
    matches_complete: bool
    teams_complete: bool

    @property
    def is_complete(self) -> bool:
        return self.matches_complete and self.teams_complete


def audit_completeness(
    competition_slug: str, matches: list[Match], standings: list[StandingRow] | None
) -> CompletenessAudit:
    expected_matches = EXPECTED_MATCHES.get(competition_slug)
    expected_teams = EXPECTED_TEAMS.get(competition_slug)
    teams_found = len(standings) if standings else 0

    return CompletenessAudit(
        competition_slug=competition_slug,
        matches_found=len(matches),
        matches_expected=expected_matches,
        teams_found=teams_found,
        teams_expected=expected_teams,
        matches_complete=expected_matches is None or len(matches) >= expected_matches,
        # Exact, not >=: unlike match count (legitimately reduced by a
        # real postponement), the number of teams in a competition is
        # fixed all season — more than expected is never healthy. Real
        # bug found live: merging two sources that spell the same club
        # differently (e.g. "FC Internazionale Milano" vs "Inter Milan")
        # silently inflated a 20-team table to 37 rows, and a `>=` check
        # here would have reported that as "complete".
        teams_complete=expected_teams is None or teams_found == expected_teams,
    )


def count_played_matches(matches: list[Match]) -> int:
    """How many of the fetched matches have a real final score — a second,
    independent completeness signal alongside the raw match count (a
    season can have the right total count while still missing recent
    results, e.g. if every "played" match in the window is actually still
    scheduled)."""
    return sum(1 for m in matches if _is_finished_with_score(m))
