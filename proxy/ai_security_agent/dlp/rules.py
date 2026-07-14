"""Pattern and keyword definitions used by the DLP classifiers.

Each `PatternRule` is a regex plus a weight (1-10) contributing to the
overall risk score. Keyword lists are separate since they're meant to be
extended per-deployment (client/project code names) without touching regex
logic — see `CONFIDENTIAL_KEYWORDS` and `load_custom_keywords`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PatternRule:
    name: str
    category: str
    pattern: re.Pattern[str]
    weight: int  # 1-10, contribution to overall risk score
    description: str


CREDENTIAL_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        name="aws_access_key",
        category="credential",
        pattern=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        weight=9,
        description="AWS access key ID",
    ),
    PatternRule(
        name="github_token",
        category="credential",
        pattern=re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
        weight=9,
        description="GitHub personal access / OAuth / app token",
    ),
    PatternRule(
        name="slack_token",
        category="credential",
        pattern=re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        weight=8,
        description="Slack API token",
    ),
    PatternRule(
        name="private_key_block",
        category="credential",
        pattern=re.compile(
            r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
        weight=10,
        description="PEM private key block",
    ),
    PatternRule(
        name="jwt",
        category="credential",
        pattern=re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
        weight=6,
        description="JWT-shaped token",
    ),
    PatternRule(
        name="generic_api_key_assignment",
        category="credential",
        pattern=re.compile(
            r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*"
            r"['\"]?[A-Za-z0-9_\-/+]{16,}['\"]?"
        ),
        weight=6,
        description="Generic 'key = value' style secret assignment",
    ),
)

PII_RULES: tuple[PatternRule, ...] = (
    PatternRule(
        name="ssn",
        category="pii",
        pattern=re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
        weight=8,
        description="US Social Security Number",
    ),
    PatternRule(
        name="email_address",
        category="pii",
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        weight=2,
        description="Email address",
    ),
    PatternRule(
        name="credit_card_candidate",
        category="pii",
        # Candidate digit runs; validated with a Luhn check in classifiers.py
        pattern=re.compile(r"\b(?:\d[ -]?){13,19}\b"),
        weight=7,
        description="Candidate credit card number (Luhn-validated)",
    ),
)

CONFIDENTIAL_KEYWORDS: tuple[str, ...] = (
    "confidential",
    "internal use only",
    "do not distribute",
    "nda",
    "non-disclosure",
    "proprietary and confidential",
    "attorney-client privileged",
)


def load_custom_keywords(extra: list[str]) -> tuple[str, ...]:
    """Merge deployment-specific keywords (client/project code names) in.

    Kept as a separate entry point rather than editing CONFIDENTIAL_KEYWORDS
    directly, since per-client lists should come from config, not source.
    """
    return tuple({*CONFIDENTIAL_KEYWORDS, *(k.lower() for k in extra)})


ALL_PATTERN_RULES: tuple[PatternRule, ...] = CREDENTIAL_RULES + PII_RULES
