# apps/api

FastAPI backend. Exposes normalized sports data over:

- `/api/sports`
- `/api/sports/{sport}/competitions`
- `/api/competitions/{slug}/matches`
- `/api/competitions/{slug}/standings`
- `/api/competitions/{slug}/matches/{match_id}/analysis` — real Poisson
  prediction (or an honest reason why not), recent form, head-to-head.

See [../../README.md](../../README.md) for how to run it and
[../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) for the design.
