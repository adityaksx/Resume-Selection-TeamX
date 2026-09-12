"""Entry point for the Smart Shortlisting Engine.

Run with: streamlit run app/main.py
"""

import sys
from pathlib import Path

# Ensure the project root (parent of app/) is on sys.path so that
# absolute imports like `from app.xxx import ...` resolve correctly
# when Streamlit runs this file directly.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.ui import run_ui


if __name__ == "__main__":
    run_ui()
else:
    # When Streamlit imports this module directly
    run_ui()
