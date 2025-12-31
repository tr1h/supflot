# conftest.py (положите рядом с run_bot.py, config.py и папками core/, handlers/ и т.д.)
import sys
from pathlib import Path

# корень — папка, где лежит этот conftest.py
ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
