"""Small grammar helpers shared by Mihomo policy sentinels."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from fnmatch import fnmatchcase
from typing import Any

MIHOMO_TRAILING_RULE_OPTIONS = frozenset({"no-resolve"})
MIHOMO_RULE_SET_PATTERN = re.compile(r"(?:^|[,(])rule-set,([^,)]+)", re.IGNORECASE)
MIHOMO_DOMAIN_MATCHER_PATTERN = re.compile(
    r"(?:^|[^a-z0-9_-])domain-(keyword|regex|regexp|wildcard),([^,)\r\n]+)",
    re.IGNORECASE,
)


def split_mihomo_rule(rule: str) -> list[str]:
    """Split a Mihomo rule on top-level commas, preserving logical expressions."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for character in rule:
        if character == "(":
            depth += 1
        elif character == ")" and depth:
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    parts.append("".join(current).strip())
    return parts


def mihomo_rule_subject_and_target(rule: str) -> tuple[str, str]:
    """Return normalized matcher text and the top-level policy target."""
    parts = split_mihomo_rule(rule)
    while parts and parts[-1].casefold() in MIHOMO_TRAILING_RULE_OPTIONS:
        parts.pop()
    if len(parts) < 2:
        return "", ""
    return ",".join(parts[:-1]).casefold(), parts[-1].casefold()


def mihomo_rule_provider_ids(subject: str) -> set[str]:
    """Extract normalized RULE-SET provider IDs from simple or logical matchers."""
    return {
        match.group(1).strip().casefold()
        for match in MIHOMO_RULE_SET_PATTERN.finditer(subject)
        if match.group(1).strip()
    }


def mihomo_text_matches_domains(text: str, domains: Iterable[str]) -> bool:
    """Return whether Mihomo matcher/provider text can select a known domain."""
    normalized = text.casefold()
    known_domains = {domain.strip().casefold() for domain in domains if domain.strip()}
    unescaped = normalized.replace("\\", "")
    if any(domain in normalized or domain in unescaped for domain in known_domains):
        return True

    for match in MIHOMO_DOMAIN_MATCHER_PATTERN.finditer(normalized):
        matcher_type = match.group(1).casefold()
        matcher = match.group(2).strip().strip("'\"")
        if not matcher or len(matcher) > 512:
            return True
        if matcher_type == "keyword":
            if any(matcher in domain for domain in known_domains):
                return True
            continue
        if matcher_type == "wildcard":
            if any(fnmatchcase(domain, matcher) for domain in known_domains):
                return True
            continue
        try:
            if any(re.search(matcher, domain, flags=re.IGNORECASE) for domain in known_domains):
                return True
        except re.error:
            return True
    return False


def mihomo_block_targets(
    groups: Sequence[Mapping[str, Any]],
    base_targets: Iterable[str],
) -> set[str]:
    """Resolve proxy groups whose every path terminates in a block target."""
    targets = {str(target).strip().casefold() for target in base_targets}
    group_proxies: dict[str, set[str]] = {}
    for group in groups:
        name = str(group.get("name") or "").strip().casefold()
        proxies = group.get("proxies")
        if not name or not isinstance(proxies, list):
            continue
        normalized = {str(proxy).strip().casefold() for proxy in proxies if str(proxy).strip()}
        if normalized:
            group_proxies[name] = normalized

    changed = True
    while changed:
        changed = False
        for name, proxies in group_proxies.items():
            if name not in targets and proxies.issubset(targets):
                targets.add(name)
                changed = True
    return targets
