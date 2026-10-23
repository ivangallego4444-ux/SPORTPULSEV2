from __future__ import annotations

from datetime import datetime, timezone

from sp_core.models import Match, MatchStatus, StandingRow
from sp_predict.integrity import audit_completeness, count_played_matches


def _match(match_id: str, status: MatchStatus = MatchStatus.FINISHED) -> Match:
    return Match(
        id=match_id,
        sport="futbol",
        competition_slug="laliga",
        competition_name="LaLiga",
        status=status,
        kickoff=datetime(2026, 10, 1, tzinfo=timezone.utc),
        home="Alpha",
        away="Beta",
        home_score=1 if status == MatchStatus.FINISHED else None,
        away_score=0 if status == MatchStatus.FINISHED else None,
        summary=None,
        venue=None,
        source="test",
    )


def _standings(n: int) -> list[StandingRow]:
    return [
        StandingRow(rank=i + 1, team=f"Team{i}", played=1, wins=1, draws=0, losses=0, points=3, crest_url=None)
        for i in range(n)
    ]


class TestAuditCompleteness:
    def test_reports_incomplete_when_below_the_real_expected_count(self):
        audit = audit_completeness("laliga", [_match("1")] * 50, _standings(15))
        assert audit.matches_expected == 380
        assert audit.teams_expected == 20
        assert audit.matches_complete is False
        assert audit.teams_complete is False
        assert audit.is_complete is False

    def test_reports_complete_once_the_real_expected_count_is_met(self):
        audit = audit_completeness("ligue-1", [_match(str(i)) for i in range(306)], _standings(18))
        assert audit.matches_complete is True
        assert audit.teams_complete is True
        assert audit.is_complete is True

    def test_champions_league_expects_144_matches_and_36_teams(self):
        audit = audit_completeness("champions-league", [_match(str(i)) for i in range(144)], _standings(36))
        assert audit.matches_expected == 144
        assert audit.teams_expected == 36
        assert audit.is_complete is True

    def test_an_unknown_competition_has_no_expectation_and_is_never_flagged_incomplete(self):
        # A competition this audit doesn't know about (e.g. NBA) should
        # never be reported as "incomplete" — there's no real expectation
        # to compare against, so silence is honest, a false alarm is not.
        audit = audit_completeness("nba", [_match("1")], None)
        assert audit.matches_expected is None
        assert audit.teams_expected is None
        assert audit.is_complete is True

    def test_never_blocks_on_a_real_count_that_is_merely_close(self):
        # 379 of 380 (one real postponed match) must not read as badly
        # broken — this is a diagnostic signal, not a hard gate, and the
        # caller is expected to keep serving the response either way.
        audit = audit_completeness("laliga", [_match(str(i)) for i in range(379)], _standings(20))
        assert audit.matches_found == 379
        assert audit.matches_complete is False  # visible in the audit...
        # ...but nothing here raises or refuses — it's just a number.


class TestCountPlayedMatches:
    def test_counts_only_matches_with_a_real_final_score(self):
        matches = [_match("1"), _match("2", status=MatchStatus.SCHEDULED)]
        assert count_played_matches(matches) == 1
