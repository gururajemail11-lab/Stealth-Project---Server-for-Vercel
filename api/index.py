import os
import sys

# Ensure project root is importable when running under Vercel runtime.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from receiver import app
