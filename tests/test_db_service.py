import pandas as pd
from services.db_service import DatabaseService
from sqlalchemy import create_engine


def test_database_service_test_connection_success():
    # SQLite memory database is always reachable and valid
    url = "sqlite:///:memory:"
    success, msg = DatabaseService.test_connection(url)
    assert success
    assert "successful" in msg


def test_database_service_test_connection_failure():
    # Invalid dialect should fail
    url = "invalid_dialect://hostname/db"
    success, msg = DatabaseService.test_connection(url)
    assert not success
    assert "Connection failed" in msg


def test_database_service_list_tables_and_load_table():
    import os
    import tempfile

    # Create an in-memory-like but persistent temporary SQLite file database
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        db_path = tmp.name

    url = f"sqlite:///{db_path}"
    try:
        engine = create_engine(url)

        df_users = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
        df_logs = pd.DataFrame({"id": [1], "action": ["login"]})

        df_users.to_sql("users", engine, index=False)
        df_logs.to_sql("logs", engine, index=False)

        # Test listing tables
        tables = DatabaseService.list_tables(url)
        assert tables == ["logs", "users"]

        # Test loading table
        df_loaded = DatabaseService.load_table(url, "users")
        assert len(df_loaded) == 2
        assert list(df_loaded.columns) == ["id", "name"]

        # Test load table row limiting
        df_limited = DatabaseService.load_table(url, "users", max_rows=1)
        assert len(df_limited) == 1
    finally:
        # Clean up temporary database file
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
