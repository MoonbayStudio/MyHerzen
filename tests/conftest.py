from pathlib import Path
import os
import sys


os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OWNER_EMAILS", "owner@example.com")

ROOT_DIR = Path(__file__).resolve().parents[1]
API_DIR = ROOT_DIR / "API"
ROOT_DIR_STR = str(ROOT_DIR)
API_DIR_STR = str(API_DIR)

if API_DIR_STR not in sys.path:
    sys.path.insert(0, API_DIR_STR)
if ROOT_DIR_STR not in sys.path:
    sys.path.insert(0, ROOT_DIR_STR)
