import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # makes `evals` importable from backend tests

os.environ.setdefault("MUJEAZ_ENV", "test")
os.environ.setdefault("MUJEAZ_DEV_AUTH", "true")
