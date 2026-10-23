# apps/workers (placeholder)

Not implemented: `apps/api` currently fetches from each provider on
request, with a simple in-memory TTL cache (see
`packages/sp_providers/base.py`) to stay under free-tier rate limits.
This folder is reserved for moving that into real scheduled background
jobs if/when request-time fetching stops being enough. Not needed for the
current working version — see [../../README.md](../../README.md).
