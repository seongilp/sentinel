import aiomysql
from app.connectors.base import DatabaseConnector, ColumnInfo, SampleData


class MySQLConnector(DatabaseConnector):
    def __init__(self, config: dict) -> None:
        self._config = config
        self._conn: aiomysql.Connection | None = None

    async def _get_conn(self) -> aiomysql.Connection:
        if self._conn is None or self._conn.closed:
            db = self._config.get("database") or None
            self._conn = await aiomysql.connect(
                host=self._config["host"],
                port=int(self._config.get("port", 3306)),
                user=self._config["username"],
                password=self._config.get("password", ""),
                db=db,
                autocommit=True,
            )
        return self._conn

    async def test_connection(self) -> bool:
        try:
            conn = await self._get_conn()
            await conn.ping()
            return True
        except Exception:
            return False

    _SYSTEM_DATABASES = {"information_schema", "performance_schema", "mysql", "sys"}

    async def list_schemas(self) -> list[str]:
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute("SHOW DATABASES")
            rows = await cur.fetchall()
        db = self._config.get("database") or None
        if db:
            return [db] if db in {row[0] for row in rows} else []
        return [row[0] for row in rows if row[0] not in self._SYSTEM_DATABASES]

    async def list_tables(self, schema: str) -> list[str]:
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute(f"SHOW TABLES IN `{schema}`")
            rows = await cur.fetchall()
        return [row[0] for row in rows]

    async def get_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (schema, table),
            )
            rows = await cur.fetchall()
        return [
            ColumnInfo(
                schema_name=schema,
                table_name=table,
                column_name=row[0],
                data_type=row[1],
                nullable=(row[2].upper() == "YES"),
            )
            for row in rows
        ]

    async def sample_column(
        self, schema: str, table: str, column: str, limit: int = 100
    ) -> SampleData:
        column_info = ColumnInfo(
            schema_name=schema,
            table_name=table,
            column_name=column,
            data_type="unknown",
        )
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT `{column}` FROM `{schema}`.`{table}` WHERE `{column}` IS NOT NULL LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
        values: list[str | None] = [str(row[0]) if row[0] is not None else None for row in rows]
        return SampleData.from_list(column_info, values)

    async def count_rows(self, schema: str, table: str) -> int:
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) FROM `{schema}`.`{table}`")
            row = await cur.fetchone()
        return int(row[0])

    async def fetch_rows(self, schema: str, table: str, columns: list[str], limit: int, offset: int) -> list[list]:
        cols = ", ".join(f"`{c}`" for c in columns)
        conn = await self._get_conn()
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT {cols} FROM `{schema}`.`{table}` LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = await cur.fetchall()
        return [list(row) for row in rows]

    async def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
