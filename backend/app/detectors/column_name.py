from app.connectors.base import ColumnInfo
from app.detectors.base import BaseDetector, Detection

PII_COLUMN_PATTERNS: dict[str, list[str]] = {
    "email": ["email", "e_mail", "email_addr", "이메일", "메일"],
    "phone": ["phone", "tel", "mobile", "cell", "전화", "핸드폰", "연락처", "휴대폰"],
    "resident_id": ["주민", "주민번호", "주민등록", "resident_id", "rrn"],
    "name": ["name", "full_name", "first_name", "last_name", "이름", "성명"],
    "address": ["address", "addr", "주소", "도로명", "상세주소"],
    "birth_date": ["birth", "birthday", "birth_date", "생년월일", "dob"],
    "passport": ["passport", "여권", "passport_no"],
    "driver_license": ["driver", "license", "운전면허", "면허번호"],
    "account_number": ["account", "계좌", "bank_account", "acct"],
    "credit_card": ["card", "credit_card", "card_no", "카드번호"],
    "ssn": ["ssn", "social_security"],
    "ip_address": ["ip", "ip_addr", "ip_address"],
    "password": ["password", "passwd", "pwd", "pass", "비밀번호"],
}


class ColumnNameDetector(BaseDetector):
    def detect(
        self, column: ColumnInfo, samples: list[str] | None = None
    ) -> list[Detection]:
        col_lower = column.column_name.lower()
        detections: list[Detection] = []

        for pii_type, patterns in PII_COLUMN_PATTERNS.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                if col_lower == pattern_lower:
                    detections.append(
                        Detection(
                            pii_type=pii_type,
                            confidence=0.8,
                            detector="column_name",
                            evidence=f"Exact match: column '{column.column_name}' == '{pattern}'",
                        )
                    )
                    break
                elif pattern_lower in col_lower:
                    detections.append(
                        Detection(
                            pii_type=pii_type,
                            confidence=0.6,
                            detector="column_name",
                            evidence=f"Partial match: column '{column.column_name}' contains '{pattern}'",
                        )
                    )
                    break

        return detections
