import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text

from app.services.bootstrap import ensure_runtime_columns


class CheckinSwitchMigrationTest(unittest.TestCase):
    def test_existing_spots_default_to_disabled_and_migration_is_repeatable(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE scenic_spots (id INTEGER PRIMARY KEY)"))
                connection.execute(text("INSERT INTO scenic_spots (id) VALUES (1)"))
            with patch("app.services.bootstrap.engine", engine):
                ensure_runtime_columns()
                ensure_runtime_columns()
            with engine.connect() as connection:
                self.assertEqual(connection.scalar(text("SELECT checkin_enabled FROM scenic_spots WHERE id = 1")), 0)
        finally:
            engine.dispose()
