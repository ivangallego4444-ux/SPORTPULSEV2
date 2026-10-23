# packages/sp_core

Shared, sport-agnostic domain models that every provider adapter in
`packages/sp_providers` normalizes into, and that `apps/api` serves
as-is: `Match`, `StandingRow`, `Competition`, `FormResult`,
`MatchPrediction`, `MatchAnalysis`. See [`models.py`](./models.py).
