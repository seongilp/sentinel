from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnInfo:
    schema_name: str
    table_name: str
    column_name: str
    data_type: str
    nullable: bool = True


@dataclass(frozen=True)
class SampleData:
    column: ColumnInfo
    values: tuple[str | None, ...]  # tuple for hashability (frozen dataclass)

    @classmethod
    def from_list(cls, column: ColumnInfo, values: list[str | None]) -> "SampleData":
        return cls(column=column, values=tuple(values))


class DatabaseConnector(ABC):
    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def list_schemas(self) -> list[str]: ...

    @abstractmethod
    async def list_tables(self, schema: str) -> list[str]: ...

    @abstractmethod
    async def get_columns(self, schema: str, table: str) -> list[ColumnInfo]: ...

    @abstractmethod
    async def sample_column(
        self, schema: str, table: str, column: str, limit: int = 100
    ) -> SampleData: ...

    @abstractmethod
    async def close(self) -> None: ...

    async def count_rows(self, schema: str, table: str) -> int:
        raise NotImplementedError

    async def fetch_rows(
        self, schema: str, table: str, columns: list[str], limit: int, offset: int
    ) -> list[list]:
        """Returns rows as list of lists (one per row)."""
        raise NotImplementedError
