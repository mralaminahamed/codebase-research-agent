import os

os.environ.setdefault("SECRET_KEY", "test-only-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.sqlite3")
os.environ.setdefault("DEBUG", "True")

from config.settings import *  # noqa: F401, F403, E402
