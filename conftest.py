import os


def pytest_configure(config: object) -> None:
    """Set required env vars before Django settings load."""
    os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
    os.environ.setdefault("DATABASE_URL", "sqlite:///test.sqlite3")
    os.environ.setdefault("DEBUG", "True")
