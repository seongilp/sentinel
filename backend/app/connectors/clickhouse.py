import logging

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient

from app.connectors.base import DatabaseConnector, ColumnInfo, SampleData

logger = logging.getLogger(__name__)

# ClickHouse system databases to exclude from scans
_SYSTEM_SCHEMAS = {"system", "information_schema", "INFORMATION_SCHEMA"}


class ClickHouseConnector(DatabaseConnector):
    def __init__(self, config: dict) -> None:
        self._config = config
        self._client: AsyncClient | None = None

    async def _get_client(self) -> AsyncClient:
        if self._client is None:
            self._client = await clickhouse_connect.get_async_client(
                host=self._config.get("host", "localhost"),
                port=int(self._config.get("port", 8123)),
                username=self._config.get("username", "default"),
                password=self._config.get("password", ""),
                database=self._config.get("database") or "default",
            )
        return self._client

    async def test_connection(self) -> bool:
        try:
            client = await self._get_client()
            result = await client.query("SELECT 1")
            return result.first_item is not None
        except Exception as e:
            logger.error("ClickHouse test_connection failed: %s", e, exc_info=True)
            return False

    async def list_schemas(self) -> list[str]:
        client = await self._get_client()
        result = await client.query("SHOW DATABASES")
        return [row[0] for row in result.result_rows if row[0] not in _SYSTEM_SCHEMAS]

    async def list_tables(self, schema: str) -> list[str]:
        client = await self._get_client()
        result = await client.query(
            "SELECT name FROM system.tables WHERE database = {db:String}",
            parameters={"db": schema},
        )
        return [row[0] for row in result.result_rows]

    async def get_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        client = await self._get_client()
        result = await client.query(
            """
            SELECT name, type
            FROM system.columns
            WHERE database = {db:String} AND table = {tbl:String}
            ORDER BY position
            """,
            parameters={"db": schema, "tbl": table},
        )
        return [
            ColumnInfo(
                schema_name=schema,
                table_name=table,
                column_name=row[0],
                data_type=row[1],
                nullable="Nullable" in row[1],
            )
            for row in result.result_rows
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
        client = await self._get_client()
        result = await client.query(
            f"SELECT `{column}` FROM `{schema}`.`{table}` "
            f"WHERE `{column}` IS NOT NULL LIMIT {{lim:UInt32}}",
            parameters={"lim": limit},
        )
        values: list[str | None] = [
            str(row[0]) if row[0] is not None else None
            for row in result.result_rows
        ]
        return SampleData.from_list(column_info, values)

    async def count_rows(self, schema: str, table: str) -> int:
        client = await self._get_client()
        result = await client.query(
            f"SELECT count() FROM `{schema}`.`{table}`"
        )
        return int(result.first_row[0])

    async def fetch_rows(self, schema: str, table: str, columns: list[str], limit: int, offset: int) -> list[list]:
        cols = ", ".join(f"`{c}`" for c in columns)
        client = await self._get_client()
        result = await client.query(
            f"SELECT {cols} FROM `{schema}`.`{table}` LIMIT {{lim:UInt64}} OFFSET {{off:UInt64}}",
            parameters={"lim": limit, "off": offset},
        )
        return [list(row) for row in result.result_rows]

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
