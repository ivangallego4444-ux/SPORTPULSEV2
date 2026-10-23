# packages/sp_predict

Real statistics on real data, never a bookmaker odds feed.

- [`poisson.py`](./poisson.py) — match outcome / BTTS / over-under
  probabilities from each team's actual goals-for/against in the
  competition's own fetched matches. Refuses to return a prediction
  (`None`) below `MIN_MATCHES` real home/away games for either team,
  rather than reporting a number from a thin sample.
- [`history.py`](./history.py) — recent form (W/D/L) and head-to-head,
  both derived purely from already-fetched `Match` objects. Never calls
  the network itself.

Takes `sp_core.Match` objects in, never a provider or an HTTP client —
keeps this package testable with plain data and reusable for any sport
that gives structured home/away teams and scores.
