import sys
from pathlib import Path

_PACKAGES_DIR = Path(__file__).resolve().parents[3] / "packages"
if str(_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_DIR))
