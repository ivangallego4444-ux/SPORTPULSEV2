import os
import sys
from pathlib import Path

_PACKAGES_DIR = Path(__file__).resolve().parents[2] / "packages"
if str(_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_DIR))

# Must be set before `app.main` is ever imported by a test module: the real
# app warms an in-memory snapshot by fetching every competition at startup
# and keeps it fresh with background tasks (see main.py's _Snapshot). A
# test only ever mocks the one or two routes its own scenario needs, so
# letting that eager warm-up run during tests would throw respx's
# "unmocked request" error for every *other* competition, or hit the real
# network when no mock is active at all. Tests instead rely on the
# existing per-request lazy-fetch fallback, unchanged from before this
# snapshot existed.
os.environ.setdefault("SPORTPULSE_DISABLE_BACKGROUND_REFRESH", "1")
