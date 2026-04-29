from datetime import datetime

from sqltune_agent.discovery import WorkloadDiscovery


class Cursor:
    def __init__(self):
        self.sql = None
        self.params = None

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params

    def fetchall(self):
        return [
            (
                1,
                "abc123",
                42,
                10,
                100.0,
                200.0,
                "APP",
                "module",
                "action",
                1000,
                5,
                20,
                datetime.utcnow(),
                "select * from dual",
            )
        ]


class Connection:
    def __init__(self):
        self.cursor_obj = Cursor()

    def cursor(self):
        return self.cursor_obj


def test_discover_uses_gv_sql_and_max_sql_bind():
    connection = Connection()
    rows = WorkloadDiscovery(connection, "gv$sql").discover(10, "combined")

    assert "gv$sql" in connection.cursor_obj.sql.lower()
    assert connection.cursor_obj.params == {"max_sql": 10}
    assert rows[0].sql_id == "abc123"
    assert rows[0].avg_elapsed_time == 200.0
