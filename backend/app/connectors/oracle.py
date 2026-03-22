from app.connectors.base import DatabaseConnector, ColumnInfo, SampleData


class OracleConnector(DatabaseConnector):
    def __init__(self, config: dict) -> None:
        self._config = config

    async def test_connection(self) -> bool:
        raise NotImplementedError("Phase 2")

    async def list_schemas(self) -> list[str]:
        raise NotImplementedError("Phase 2")

    async def list_tables(self, schema: str) -> list[str]:
        raise NotImplementedError("Phase 2")

    async def get_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        raise NotImplementedError("Phase 2")

    async def sample_column(
        self, schema: str, table: str, column: str, limit: int = 100
    ) -> SampleData:
        raise NotImplementedError("Phase 2")

    async def close(self) -> None:
        raise NotImplementedError("Phase 2")
