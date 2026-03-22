from app.connectors.base import DatabaseConnector
from app.connectors.mysql import MySQLConnector
from app.connectors.oracle import OracleConnector
from app.connectors.mongodb import MongoDBConnector
from app.connectors.clickhouse import ClickHouseConnector


def create_connector(db_type: str, config: dict) -> DatabaseConnector:
    match db_type:
        case "mysql":
            return MySQLConnector(config)
        case "oracle":
            return OracleConnector(config)
        case "mongodb":
            return MongoDBConnector(config)
        case "clickhouse":
            return ClickHouseConnector(config)
        case _:
            raise ValueError(f"Unsupported DB type: {db_type}")
