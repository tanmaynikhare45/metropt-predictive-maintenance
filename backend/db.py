"""Database connection pool (one pool for the whole API process)."""
import os

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv()


def make_pool(url=None):
    url = url or os.environ["DATABASE_URL"]
    return ConnectionPool(
        url,
        min_size=1,
        max_size=5,
        timeout=5,          # fail fast if the database is down
        open=False,         # opened in the app's startup (see main.py)
        kwargs={"row_factory": dict_row, "options": "-c timezone=UTC"},
    )
