"""DLP content classifiers.

The public entry point is `scan(text)`, returning a `ClassificationResult`.

Hard rule (see CLAUDE.md / docs/PRIVACY_AND_CONSENT.md): matched values are
never returned or logged in raw form. `Finding.masked_snippet` always masks
the middle of the match, keeping only enough of the edges to let an admin
recognize *what* was flagged without exposing the secret/PII itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_security_agent.dlp.rules import ALL_PATTERN_RULES, CONFIDENTIAL_KEYWORDS

_KEEP_EDGE_CHARS = 4


def _mask(value: str) -> str:
    """Redact the middle of a matched value, keeping a few edge chars."""
    if len(value) <= _KEEP_EDGE_CHARS * 2:
        return "*" * len(value)
    return (
        value[:_KEEP_EDGE_CHARS]
        + "*" * (len(value) - _KEEP_EDGE_CHARS * 2)
        + value[-_KEEP_EDGE_CHARS:]
    )


def _luhn_valid(digits: str) -> bool:
    """Standard Luhn checksum, used to filter credit-card-shaped false
    positives (phone numbers, order IDs, etc. also match 13-19 digit runs).
    """
    total = 0
    parity = len(digits) % 2
    for i, ch in enumerate(digits):
        n = int(ch)
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


@dataclass(frozen=True)
class Finding:
    category: str
    rule_name: str
    masked_snippet: str
    start: int
    end: int
    weight: int
    description: str


@dataclass
class ClassificationResult:
    findings: list[Finding] = field(default_factory=list)
    risk_score: int = 1
    rationale: str = "No confidential content detected."

    @property
    def categories(self) -> set[str]:
        return {f.category for f in self.findings}

    @property
    def flagged(self) -> bool:
        return bool(self.findings)


def scan(text: str, extra_keywords: tuple[str, ...] = ()) -> ClassificationResult:
    """Scan prompt text for credentials, PII, and confidential markers.

    `extra_keywords` allows per-deployment keyword lists (client/project
    code names) to be layered on without touching source.
    """
    findings: list[Finding] = []

    for rule in ALL_PATTERN_RULES:
        for match in rule.pattern.finditer(text):
            value = match.group(0)
            if rule.name == "credit_card_candidate":
                digits = "".join(ch for ch in value if ch.isdigit())
                if not (13 <= len(digits) <= 19) or not _luhn_valid(digits):
                    continue
            findings.append(
                Finding(
                    category=rule.category,
                    rule_name=rule.name,
                    masked_snippet=_mask(value),
                    start=match.start(),
                    end=match.end(),
                    weight=rule.weight,
                    description=rule.description,
                )
            )

    keywords = tuple({*CONFIDENTIAL_KEYWORDS, *extra_keywords})
    lowered = text.lower()
    for keyword in keywords:
        idx = lowered.find(keyword)
        if idx != -1:
            findings.append(
                Finding(
                    category="confidential_marker",
                    rule_name="keyword_match",
                    masked_snippet=_mask(keyword),
                    start=idx,
                    end=idx + len(keyword),
                    weight=4,
                    description=f"Confidential marker keyword: '{keyword}'",
                )
            )

    return _build_result(findings)


def _build_result(findings: list[Finding]) -> ClassificationResult:
    if not findings:
        return ClassificationResult()

    top_weight = max(f.weight for f in findings)
    distinct_categories = len({f.category for f in findings})
    # Base score on the single worst finding, then bump slightly for
    # multiple independent categories triggering (broader exposure).
    score = min(10, top_weight + max(0, distinct_categories - 1))
    score = max(1, score)

    by_category: dict[str, int] = {}
    for f in findings:
        by_category[f.category] = by_category.get(f.category, 0) + 1
    category_summary = ", ".join(
        f"{count}x {category}" for category, count in sorted(by_category.items())
    )
    rationale = (
        f"Risk {score}/10: detected {len(findings)} finding(s) "
        f"({category_summary}). Highest-weight signal: "
        f"{max(findings, key=lambda f: f.weight).description}."
    )

    return ClassificationResult(findings=findings, risk_score=score, rationale=rationale)
