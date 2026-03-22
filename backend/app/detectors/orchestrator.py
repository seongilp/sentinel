from app.connectors.base import ColumnInfo
from app.detectors.base import Detection
from app.detectors.column_name import ColumnNameDetector
from app.detectors.regex_pattern import RegexPatternDetector


class DetectionOrchestrator:
    def __init__(self, confidence_threshold: float = 0.5, rules: list | None = None) -> None:
        self._threshold = confidence_threshold
        self._col_detector = ColumnNameDetector()
        self._regex_detector = RegexPatternDetector()

    def detect(
        self, column: ColumnInfo, samples: list[str] | None = None
    ) -> list[Detection]:
        col_detections = self._col_detector.detect(column, samples)
        regex_detections = self._regex_detector.detect(column, samples)

        # Index column detections by pii_type
        col_by_type: dict[str, Detection] = {d.pii_type: d for d in col_detections}
        regex_by_type: dict[str, Detection] = {d.pii_type: d for d in regex_detections}

        merged: dict[str, Detection] = {}

        # Merge: types detected by column name
        for pii_type, col_det in col_by_type.items():
            if pii_type in regex_by_type:
                regex_det = regex_by_type[pii_type]
                combined_conf = min(1.0, col_det.confidence + regex_det.confidence * 0.5)
                merged[pii_type] = Detection(
                    pii_type=pii_type,
                    confidence=combined_conf,
                    detector="column_name+regex_pattern",
                    evidence=f"{col_det.evidence}; {regex_det.evidence}",
                )
            else:
                merged[pii_type] = col_det

        # Add regex-only detections not covered by column name
        for pii_type, regex_det in regex_by_type.items():
            if pii_type not in merged:
                merged[pii_type] = regex_det

        # Filter by threshold and return sorted by confidence descending
        results = [d for d in merged.values() if d.confidence >= self._threshold]
        return sorted(results, key=lambda d: d.confidence, reverse=True)

    def detect_by_column_name(self, column: ColumnInfo) -> list[Detection]:
        """Phase 1: 컬럼명만으로 탐지 (샘플링 없이)"""
        return self._col_detector.detect(column, samples=None)

    def detect_with_samples(
        self,
        column: ColumnInfo,
        samples: list[str],
        existing: list[Detection] | None = None,
    ) -> list[Detection]:
        """Phase 2: 데이터 샘플로 정규식 탐지 후 기존 결과와 병합"""
        col_by_type: dict[str, Detection] = {d.pii_type: d for d in (existing or [])}
        regex_detections = self._regex_detector.detect(column, samples)
        regex_by_type: dict[str, Detection] = {d.pii_type: d for d in regex_detections}

        merged: dict[str, Detection] = {}

        for pii_type, col_det in col_by_type.items():
            if pii_type in regex_by_type:
                regex_det = regex_by_type[pii_type]
                combined_conf = min(1.0, col_det.confidence + regex_det.confidence * 0.5)
                merged[pii_type] = Detection(
                    pii_type=pii_type,
                    confidence=combined_conf,
                    detector="column_name+regex_pattern",
                    evidence=f"{col_det.evidence}; {regex_det.evidence}",
                )
            else:
                merged[pii_type] = col_det

        for pii_type, regex_det in regex_by_type.items():
            if pii_type not in merged:
                merged[pii_type] = regex_det

        return sorted(merged.values(), key=lambda d: d.confidence, reverse=True)
