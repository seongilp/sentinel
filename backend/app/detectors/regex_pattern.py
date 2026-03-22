import re
from app.connectors.base import ColumnInfo
from app.detectors.base import BaseDetector, Detection

PII_REGEX_PATTERNS: dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"(01[016789])-?\d{3,4}-?\d{4}",
    "resident_id": r"\d{6}-[1-4]\d{6}",
    "credit_card": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
    "account_number": r"\d{2,6}-\d{2,6}-\d{2,6}",
    "passport": r"[A-Z]{1,2}\d{7,8}",
    "driver_license": r"\d{2}-\d{2}-\d{6}-\d{2}",
    "ip_address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    "ssn": r"\d{3}-\d{2}-\d{4}",
}

_COMPILED: dict[str, re.Pattern] = {
    pii_type: re.compile(pattern)
    for pii_type, pattern in PII_REGEX_PATTERNS.items()
}

_MIN_CONFIDENCE = 0.3


class RegexPatternDetector(BaseDetector):
    def detect(
        self, column: ColumnInfo, samples: list[str] | None = None
    ) -> list[Detection]:
        if not samples:
            return []

        sample_size = len(samples)
        if sample_size == 0:
            return []

        detections: list[Detection] = []

        for pii_type, pattern in _COMPILED.items():
            match_count = sum(1 for s in samples if s and pattern.search(s))
            confidence = match_count / sample_size

            if confidence >= _MIN_CONFIDENCE:
                detections.append(
                    Detection(
                        pii_type=pii_type,
                        confidence=confidence,
                        detector="regex_pattern",
                        evidence=f"{match_count}/{sample_size} samples matched pattern for '{pii_type}'",
                    )
                )

        return detections
