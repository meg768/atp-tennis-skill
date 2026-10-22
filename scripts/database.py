"""Read-only ATP MariaDB queries using skill-local credentials."""

import argparse
import json
import os
from pathlib import Path
import re
import sys

from dotenv import dotenv_values
import pymysql


SKILL_ROOT = Path(__file__).resolve().parent.parent
READ_QUERY = re.compile(r"^\s*(SELECT|WITH|SHOW|DESCRIBE|DESC|EXPLAIN)\b", re.I)


class DatabaseError(Exception):
    """An error safe to display without connection details or SQL values."""


def _settings(env_file=None):
    selected = env_file or os.environ.get("ATP_TENNIS_ENV_FILE")
    path = Path(selected).expanduser() if selected else SKILL_ROOT / ".env"
    try:
        if not path.is_file():
            raise ValueError
        config = dotenv_values(path, interpolate=False)
        if any(not config.get(key) for key in
               ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")):
            raise ValueError
        port = int(config.get("DB_PORT") or "3306")
        if not 1 <= port <= 65535:
            raise ValueError
    except Exception:
        raise DatabaseError("Missing or invalid database settings in selected .env.") from None
    return config, port


def execute(sql, params=None, env_file=None):
    """Run one read query with optional PyMySQL %s parameters.

    MariaDB enforces a read-only transaction in addition to the initial keyword
    check. This helper is for trusted analysis SQL, not an untrusted SQL service.
    Database grants remain the security boundary. Errors omit server messages
    because those may contain credentials or query values.
    """
    if not isinstance(sql, str) or not READ_QUERY.match(sql):
        raise DatabaseError("Expected one read query starting with SELECT, WITH, SHOW, DESCRIBE, DESC, or EXPLAIN.")
    config, port = _settings(env_file)
    try:
        connection = pymysql.connect(
            host=config["DB_HOST"], port=port, database=config["DB_NAME"],
            user=config["DB_USER"], password=config["DB_PASSWORD"],
            charset="utf8mb4", autocommit=False, connect_timeout=10,
            read_timeout=30, write_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception:
        raise DatabaseError("Database connection failed; check settings and access.") from None

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("START TRANSACTION READ ONLY")
            cursor.execute(sql, params)
            results = []
            while True:
                results.append({
                    "rows": cursor.fetchall() if cursor.description else [],
                    "rowcount": cursor.rowcount,
                })
                if not cursor.nextset():
                    break
            return results
    except Exception:
        raise DatabaseError("Database read failed; server details suppressed.") from None
    finally:
        try:
            connection.rollback()
        except Exception:
            pass
        try:
            connection.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Read the ATP MariaDB database; output JSON.")
    parser.add_argument("file", nargs="?", type=Path,
                        help="UTF-8 SQL file; omit to read standard input")
    parser.add_argument("--env-file", type=Path, help="Credential file (default: skill-local .env)")
    parser.add_argument("--params", help="JSON array of values for SQL %%s placeholders")
    args = parser.parse_args()
    try:
        sql = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
        params = json.loads(args.params) if args.params is not None else None
        if args.params is not None and not isinstance(params, list):
            raise DatabaseError("--params must be a JSON array.")
        result = execute(sql, tuple(params) if params is not None else None, args.env_file)
        print(json.dumps(result, default=str, ensure_ascii=False))
    except DatabaseError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print("Unable to process query; details suppressed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
