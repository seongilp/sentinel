"""Pure unit tests for PII detectors — no DB required."""
import pytest
from app.connectors.base import ColumnInfo
from app.detectors.column_name import ColumnNameDetector
from app.detectors.regex_pattern import RegexPatternDetector
from app.detectors.orchestrator import DetectionOrchestrator


def _col(name: str, data_type: str = "varchar") -> ColumnInfo:
    return ColumnInfo(schema_name="s", table_name="t",
                      column_name=name, data_type=data_type)


# ===========================================================================
# ColumnNameDetector
# ===========================================================================

class TestColumnNameDetector:
    def setup_method(self):
        self.detector = ColumnNameDetector()

    # --- exact match ---

    def test_exact_match_email(self):
        results = self.detector.detect(_col("email"))
        assert len(results) == 1
        assert results[0].pii_type == "email"
        assert results[0].confidence == 0.8
        assert results[0].detector == "column_name"

    def test_exact_match_phone(self):
        results = self.detector.detect(_col("phone"))
        types = [r.pii_type for r in results]
        assert "phone" in types

    def test_exact_match_case_insensitive(self):
        results = self.detector.detect(_col("EMAIL"))
        types = [r.pii_type for r in results]
        assert "email" in types

    # --- partial match ---

    def test_partial_match_email_in_compound_name(self):
        results = self.detector.detect(_col("user_email_address"))
        types = [r.pii_type for r in results]
        assert "email" in types
        email_det = next(r for r in results if r.pii_type == "email")
        assert email_det.confidence == 0.6

    def test_partial_match_phone(self):
        results = self.detector.detect(_col("mobile_phone_number"))
        types = [r.pii_type for r in results]
        assert "phone" in types

    # --- Korean column names ---

    def test_korean_email_column(self):
        results = self.detector.detect(_col("이메일"))
        types = [r.pii_type for r in results]
        assert "email" in types

    def test_korean_phone_column(self):
        results = self.detector.detect(_col("전화번호"))
        types = [r.pii_type for r in results]
        assert "phone" in types

    def test_korean_resident_id_column(self):
        results = self.detector.detect(_col("주민번호"))
        types = [r.pii_type for r in results]
        assert "resident_id" in types

    # --- no match ---

    def test_no_match_generic_column(self):
        results = self.detector.detect(_col("created_at"))
        assert results == []

    def test_no_match_product_column(self):
        results = self.detector.detect(_col("product_id"))
        assert results == []

    # --- evidence format ---

    def test_evidence_contains_column_name(self):
        results = self.detector.detect(_col("email"))
        assert "email" in results[0].evidence

    def test_partial_evidence_contains_partial(self):
        results = self.detector.detect(_col("user_email"))
        email_det = next(r for r in results if r.pii_type == "email")
        assert "email" in email_det.evidence

    # --- samples argument ignored ---

    def test_samples_argument_ignored(self):
        results_no_samples = self.detector.detect(_col("email"))
        results_with_samples = self.detector.detect(_col("email"), samples=["a@b.com"])
        assert len(results_no_samples) == len(results_with_samples)


# ===========================================================================
# RegexPatternDetector
# ===========================================================================

class TestRegexPatternDetector:
    def setup_method(self):
        self.detector = RegexPatternDetector()
        self.col = _col("data_col")

    # --- no samples → no detections ---

    def test_empty_samples_returns_empty(self):
        assert self.detector.detect(self.col, samples=[]) == []

    def test_none_samples_returns_empty(self):
        assert self.detector.detect(self.col, samples=None) == []

    # --- email ---

    def test_email_all_match(self):
        samples = ["alice@example.com", "bob@test.org", "carol@mail.net"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "email" in types
        email = next(r for r in results if r.pii_type == "email")
        assert email.confidence == pytest.approx(1.0)

    def test_email_partial_match_above_threshold(self):
        samples = ["alice@example.com", "not_an_email", "another@test.com"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "email" in types
        email = next(r for r in results if r.pii_type == "email")
        assert email.confidence == pytest.approx(2 / 3)

    def test_email_below_threshold_not_returned(self):
        # 1/10 = 0.1 < _MIN_CONFIDENCE (0.3)
        samples = ["alice@example.com"] + ["plain_text"] * 9
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "email" not in types

    # --- Korean phone ---

    def test_korean_phone_detected(self):
        samples = ["010-1234-5678", "011-987-6543", "016-555-0001"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "phone" in types

    # --- Resident ID (주민등록번호) ---

    def test_resident_id_detected(self):
        samples = ["900101-1234567", "850320-2987654"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "resident_id" in types

    # --- Credit card ---

    def test_credit_card_detected(self):
        samples = ["1234-5678-9012-3456", "4111111111111111"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "credit_card" in types

    # --- IP address ---

    def test_ip_address_detected(self):
        samples = ["192.168.1.1", "10.0.0.254", "172.16.0.1"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "ip_address" in types

    # --- No match ---

    def test_no_match_returns_empty(self):
        samples = ["hello", "world", "foobar", "test123"]
        results = self.detector.detect(self.col, samples=samples)
        assert results == []

    # --- None values in samples ignored ---

    def test_none_values_in_samples_handled(self):
        samples = ["alice@example.com", None, "bob@test.com"]
        results = self.detector.detect(self.col, samples=samples)
        types = [r.pii_type for r in results]
        assert "email" in types

    # --- evidence format ---

    def test_evidence_contains_match_ratio(self):
        samples = ["alice@example.com", "bob@test.com"]
        results = self.detector.detect(self.col, samples=samples)
        email = next(r for r in results if r.pii_type == "email")
        assert "2/2" in email.evidence


# ===========================================================================
# DetectionOrchestrator
# ===========================================================================

class TestDetectionOrchestrator:
    def setup_method(self):
        self.orchestrator = DetectionOrchestrator(confidence_threshold=0.5)

    # --- detect_by_column_name ---

    def test_detect_by_column_name_email(self):
        results = self.orchestrator.detect_by_column_name(_col("email"))
        types = [r.pii_type for r in results]
        assert "email" in types

    def test_detect_by_column_name_no_match(self):
        results = self.orchestrator.detect_by_column_name(_col("created_at"))
        assert results == []

    # --- detect_with_samples ---

    def test_detect_with_samples_merges_existing(self):
        col = _col("email")
        # Phase 1: column name detection
        existing = self.orchestrator.detect_by_column_name(col)
        # Phase 2: merge with regex detections
        samples = ["alice@example.com", "bob@test.org"]
        results = self.orchestrator.detect_with_samples(col, samples, existing=existing)
        types = [r.pii_type for r in results]
        assert "email" in types
        email = next(r for r in results if r.pii_type == "email")
        # Combined confidence > base confidence (0.8 + regex * 0.5)
        assert email.confidence > 0.8
        assert email.detector == "column_name+regex_pattern"

    def test_detect_with_samples_regex_only_pii(self):
        """Column name 'data_col' has no PII, but samples contain emails."""
        col = _col("data_col")
        existing = self.orchestrator.detect_by_column_name(col)
        assert existing == []
        samples = ["alice@example.com", "bob@test.com", "carol@mail.net"]
        results = self.orchestrator.detect_with_samples(col, samples, existing=existing)
        types = [r.pii_type for r in results]
        assert "email" in types

    def test_detect_with_samples_empty_list(self):
        col = _col("email")
        existing = self.orchestrator.detect_by_column_name(col)
        results = self.orchestrator.detect_with_samples(col, samples=[], existing=existing)
        # No regex detections, so only column name results remain
        types = [r.pii_type for r in results]
        assert "email" in types

    # --- full detect ---

    def test_detect_combined(self):
        col = _col("email")
        samples = ["alice@example.com", "bob@test.org"]
        results = self.orchestrator.detect(col, samples=samples)
        types = [r.pii_type for r in results]
        assert "email" in types
        email = next(r for r in results if r.pii_type == "email")
        assert email.detector == "column_name+regex_pattern"

    def test_detect_sorted_by_confidence_desc(self):
        col = _col("email")
        samples = ["alice@example.com", "bob@test.org"]
        results = self.orchestrator.detect(col, samples=samples)
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True)

    # --- threshold filtering ---

    def test_threshold_filters_low_confidence(self):
        # Orchestrator with very high threshold
        strict = DetectionOrchestrator(confidence_threshold=0.99)
        col = _col("user_email_addr")  # partial match → 0.6
        results = strict.detect_by_column_name(col)
        # Orchestrator.detect_by_column_name doesn't filter (returns raw col detections)
        # But detect() method does filter
        full_results = strict.detect(col, samples=[])
        # 0.6 confidence < 0.99 threshold, so filtered out
        types = [r.pii_type for r in full_results]
        assert "email" not in types

    def test_threshold_passes_high_confidence(self):
        low_threshold = DetectionOrchestrator(confidence_threshold=0.1)
        col = _col("email")  # exact match → 0.8
        samples = ["alice@example.com", "bob@test.org"]
        results = low_threshold.detect(col, samples=samples)
        types = [r.pii_type for r in results]
        assert "email" in types

    # --- confidence merging formula ---

    def test_combined_confidence_capped_at_1(self):
        """Both col-name (0.8) and regex (1.0) → min(1.0, 0.8 + 1.0*0.5) = 1.0"""
        col = _col("email")
        samples = ["a@b.com"] * 10  # 100% match → regex confidence=1.0
        results = self.orchestrator.detect(col, samples=samples)
        email = next(r for r in results if r.pii_type == "email")
        assert email.confidence <= 1.0
