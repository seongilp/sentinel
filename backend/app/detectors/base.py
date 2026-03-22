from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.connectors.base import ColumnInfo


@dataclass(frozen=True)
class Detection:
    pii_type: str
    confidence: float
    detector: str  # "column_name" or "regex_pattern"
    evidence: str


class BaseDetector(ABC):
    @abstractmethod
    def detect(
        self, column: ColumnInfo, samples: list[str] | None = None
    ) -> list[Detection]: ...
