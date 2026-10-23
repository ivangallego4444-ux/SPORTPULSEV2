# packages/sp_providers

One adapter module per external data source, each converting that
source's real response shape into the shared models in `packages/sp_core`
— never fabricating a field a source doesn't provide (see `Match.title`
vs `Match.home`/`away` for the football-vs-tennis case).

- [`openligadb.py`](./openligadb.py) — football (Germany: 1.Bundesliga,
  2.Bundesliga, DFB-Pokal), no API key.
- [`thesportsdb.py`](./thesportsdb.py) — basketball (NBA), tennis
  (ATP/WTA), and football (LaLiga, Premier League, Serie A, Ligue 1,
  Champions League), free public key, generic per-league config. Football
  leagues fetch per-round (`get_rounds`) rather than per-season, because
  `eventsseason.php` caps out at ~15 events for the whole competition —
  see docs/DATA_SOURCES.md.
- [`base.py`](./base.py) — shared TTL cache and safe JSON fetch helper.
  Failed/empty fetches get a short TTL (not the long success one) so a
  rate-limited request self-heals on the next try instead of showing "no
  data" long after the limit has actually cleared.
- [`registry.py`](./registry.py) — which sports/competitions are wired up.
  Don't add one here without live-verifying its endpoints first.
