import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


_load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./specimen_routing.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # \ub3d9\uc2dc\uc811\uc18d \ucd5c\uc801\ud654: WAL \ubaa8\ub4dc + \uc5f0\uacb0 \ud480 \uc124\uc815
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
        pool_size=10,        # \ub3d9\uc2dc \uc5f0\uacb0 \ucd5c\ub300 10\uac1c
        max_overflow=20,     # \ud480 \ucd08\uacfc \ud5c8\uc6a9 \uc5f0\uacb0
        pool_timeout=30,     # \uc5f0\uacb0 \ub300\uae30 \ucd5c\ub300 30\ucd08
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        """WAL \ubaa8\ub4dc: \uc77d\uae30-\uc4f0\uae30 \ub3d9\uc2dc \ud5c8\uc6a9, \uc7a0\uae08 \ub300\uae30 5\ucd08"""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")      # \ub3d9\uc2dc \uc77d\uae30+\uc4f0\uae30
        cur.execute("PRAGMA synchronous=NORMAL")    # \uc131\ub2a5/\uc548\uc804 \uade0\ud615
        cur.execute("PRAGMA busy_timeout=5000")     # DB \uc7a0\uae08 \uc2dc 5\ucd08 \ub300\uae30
        cur.execute("PRAGMA cache_size=-32000")     # 32 MB \uce90\uc2dc
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
else:
    connect_args = {}
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
