"""Check read-only behavior and error handling without touching the database."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "database.py"
spec = importlib.util.spec_from_file_location("skill_database", SCRIPT)
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)

CONFIG = {
    "DB_HOST": "test.invalid", "DB_NAME": "example", "DB_USER": "reader",
    "DB_PASSWORD": "test-secret-never-display",
}


class DatabaseTests(unittest.TestCase):
    def test_mutation_commands_rejected_before_connecting(self):
        with patch.object(database, "_settings") as settings:
            for sql in ("UPDATE players SET rank=1", "DELETE FROM matches",
                        "DROP TABLE players", "CALL PLAYER_ODDS('x', 'y', 'Hard')",
                        "SET SESSION TRANSACTION READ WRITE", "", "-- comment\nSELECT 1"):
                with self.subTest(sql=sql), self.assertRaises(database.DatabaseError):
                    database.execute(sql)
            settings.assert_not_called()

    def connection(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.description = (("name",),)
        cursor.fetchall.return_value = [{"name": "Example"}]
        cursor.rowcount = 1
        cursor.nextset.return_value = None
        return connection, cursor

    def test_bound_parameters_read_only_transaction_and_cleanup(self):
        connection, cursor = self.connection()
        params = ("O'Example",)
        with patch.object(database, "_settings", return_value=(CONFIG, 3306)), \
                patch.object(database.pymysql, "connect", return_value=connection):
            result = database.execute("SELECT name FROM players WHERE name = %s", params)
        self.assertEqual(result, [{"rows": [{"name": "Example"}], "rowcount": 1}])
        self.assertEqual(cursor.execute.call_args_list[0].args,
                         ("SET SESSION TRANSACTION READ ONLY",))
        self.assertEqual(cursor.execute.call_args_list[1].args,
                         ("START TRANSACTION READ ONLY",))
        self.assertEqual(cursor.execute.call_args_list[2].args,
                         ("SELECT name FROM players WHERE name = %s", params))
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()
        connection.commit.assert_not_called()

    def test_failed_query_suppresses_server_details_and_closes(self):
        connection, cursor = self.connection()
        cursor.execute.side_effect = [None, None, RuntimeError(CONFIG["DB_PASSWORD"])]
        with patch.object(database, "_settings", return_value=(CONFIG, 3306)), \
                patch.object(database.pymysql, "connect", return_value=connection):
            with self.assertRaises(database.DatabaseError) as caught:
                database.execute("SELECT missing_column FROM players")
        self.assertNotIn(CONFIG["DB_PASSWORD"], str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        connection.rollback.assert_called_once()
        connection.close.assert_called_once()

    def test_connection_failure_does_not_expose_credentials(self):
        with patch.object(database, "_settings", return_value=(CONFIG, 3306)), \
                patch.object(database.pymysql, "connect",
                             side_effect=RuntimeError(CONFIG["DB_PASSWORD"])):
            with self.assertRaises(database.DatabaseError) as caught:
                database.execute("SELECT 1")
        self.assertNotIn(CONFIG["DB_PASSWORD"], str(caught.exception))

    def test_settings_do_not_expand_password(self):
        config = dict(CONFIG, DB_PASSWORD="${UNRELATED_VARIABLE}", DB_PORT="3307")
        with patch.object(database.Path, "is_file", return_value=True), \
                patch.object(database, "dotenv_values", return_value=config) as dotenv:
            loaded, port = database._settings("/example/.env")
        self.assertEqual(loaded["DB_PASSWORD"], "${UNRELATED_VARIABLE}")
        self.assertEqual(port, 3307)
        dotenv.assert_called_once_with(Path("/example/.env"), interpolate=False)

    def test_explicit_env_file_has_precedence_and_no_fallback(self):
        with patch.dict(database.os.environ, {"ATP_TENNIS_ENV_FILE": "/other/.env"}), \
                patch.object(database.Path, "is_file", return_value=False), \
                patch.object(database, "dotenv_values") as dotenv:
            with self.assertRaises(database.DatabaseError):
                database._settings("/chosen/.env")
            dotenv.assert_not_called()


if __name__ == "__main__":
    unittest.main()
