from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from app.connectors.base import DatabaseConnector, ColumnInfo, SampleData

# MongoDB는 schema-less이므로 컬럼 타입 추론을 위해 샘플 문서 분석
_BSON_TYPE_MAP: dict[type, str] = {
    str: "String",
    int: "Int64",
    float: "Double",
    bool: "Boolean",
    bytes: "Binary",
    list: "Array",
    dict: "Object",
}

_SYSTEM_COLLECTIONS = {"system.indexes", "system.users", "system.sessions"}
_SYSTEM_KEYS = {"_id", "__v"}


def _bson_type(value: object) -> str:
    return _BSON_TYPE_MAP.get(type(value), type(value).__name__)


def _infer_schema(docs: list[dict]) -> dict[str, str]:
    """여러 문서에서 필드명 → 타입을 추론한다."""
    fields: dict[str, str] = {}
    for doc in docs:
        for k, v in doc.items():
            if k not in fields:
                fields[k] = _bson_type(v)
    return fields


class MongoDBConnector(DatabaseConnector):
    def __init__(self, config: dict) -> None:
        host = config.get("host", "localhost")
        port = int(config.get("port", 27017))
        username = config.get("username", "")
        password = config.get("password", "")

        if username and password:
            uri = f"mongodb://{username}:{password}@{host}:{port}/?authSource=admin"
        else:
            uri = f"mongodb://{host}:{port}/"

        self._client: AsyncIOMotorClient = AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        self._database = config.get("database", "")

    # ── Connection test ────────────────────────────────────────────────────────

    async def test_connection(self) -> bool:
        await self._client.admin.command("ping")
        return True

    # ── Schema (= database) listing ────────────────────────────────────────────

    async def list_schemas(self) -> list[str]:
        if self._database:
            return [self._database]
        names: list[str] = await self._client.list_database_names()
        return [n for n in names if n not in {"admin", "local", "config"}]

    # ── Table (= collection) listing ───────────────────────────────────────────

    async def list_tables(self, schema: str) -> list[str]:
        db = self._client[schema]
        names: list[str] = await db.list_collection_names()
        return [n for n in names if n not in _SYSTEM_COLLECTIONS]

    # ── Column (= field) listing via schema inference ──────────────────────────

    async def get_columns(self, schema: str, table: str) -> list[ColumnInfo]:
        db = self._client[schema]
        cursor = db[table].find({}, limit=100)
        docs: list[dict] = await cursor.to_list(length=100)
        if not docs:
            return []
        fields = _infer_schema(docs)
        return [
            ColumnInfo(
                schema_name=schema,
                table_name=table,
                column_name=field,
                data_type=dtype,
                nullable=True,
            )
            for field, dtype in fields.items()
            if field not in _SYSTEM_KEYS
        ]

    # ── Sample data for regex detection ───────────────────────────────────────

    async def sample_column(
        self, schema: str, table: str, column: str, limit: int = 100
    ) -> SampleData:
        db = self._client[schema]
        cursor = db[table].find(
            {column: {"$exists": True, "$ne": None}},
            {column: 1, "_id": 0},
            limit=limit,
        )
        docs: list[dict] = await cursor.to_list(length=limit)
        col_info = ColumnInfo(
            schema_name=schema,
            table_name=table,
            column_name=column,
            data_type="String",
            nullable=True,
        )
        values = [str(doc[column]) for doc in docs if column in doc]
        return SampleData.from_list(col_info, values)

    # ── Deep inspect helpers ───────────────────────────────────────────────────

    async def count_rows(self, schema: str, table: str) -> int:
        db = self._client[schema]
        return await db[table].count_documents({})

    async def fetch_rows(self, schema: str, table: str, columns: list[str], limit: int, offset: int) -> list[list]:
        db = self._client[schema]
        projection = {col: 1 for col in columns}
        projection["_id"] = 0
        cursor = db[table].find({}, projection).skip(offset).limit(limit)
        docs: list[dict] = await cursor.to_list(length=limit)
        return [[str(doc.get(col, "")) for col in columns] for doc in docs]

    # ── Cleanup ────────────────────────────────────────────────────────────────

    async def close(self) -> None:
        self._client.close()
