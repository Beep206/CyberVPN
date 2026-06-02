#!/usr/bin/env python
from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fluent.runtime import FluentBundle, FluentResource
from fluent.syntax import FluentParser, ast as fluent_ast

from src.config import BotSettings
from src.middlewares.i18n import SUPPORTED_LOCALES

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
LOCALES_DIR = SRC_DIR / "locales"
PRIMARY_LOCALES = ("en", "ru")
CONTRACT_LOCALE = "en"
AUDITED_SOURCE_DIRS = (SRC_DIR / "handlers", SRC_DIR / "keyboards")
MESSAGE_ID_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*=")
TAG_RE = re.compile(r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9:-]*)(?:\s+[^<>]*)?(/?)\s*>")
ALLOWED_TELEGRAM_TAGS = {
    "a",
    "b",
    "blockquote",
    "code",
    "del",
    "em",
    "i",
    "ins",
    "pre",
    "s",
    "span",
    "strike",
    "strong",
    "tg-emoji",
    "tg-spoiler",
    "u",
}
NUMERIC_VARIABLE_HINTS = (
    "amount",
    "bonus",
    "count",
    "day",
    "duration",
    "gb",
    "limit",
    "memory",
    "month",
    "percent",
    "price",
    "rate",
    "reward",
    "traffic",
    "user",
)
KNOWN_NAME_KEY_OPTIONS = {
    "first_line_key": (
        "support-first-line-account",
        "support-first-line-connectivity",
        "support-first-line-general",
        "support-first-line-legal_abuse",
        "support-first-line-payment",
        "support-first-line-provisioning",
    ),
    "status_key": (
        "support-escalation-created",
        "support-escalation-fallback",
    ),
    "text_key": (
        "btn-finance-open",
        "btn-growth-gifts",
        "btn-growth-notifications",
        "btn-miniapp",
        "btn-miniapp-open",
    ),
}
KNOWN_CALL_KEY_OPTIONS = {
    "_invite_status_key": (
        "my-invites-status-active",
        "my-invites-status-expired",
        "my-invites-status-used",
    ),
    "_trial_reason_key": (
        "trial-not-eligible-active",
        "trial-not-eligible-unavailable",
        "trial-not-eligible-unknown",
        "trial-not-eligible-used",
    ),
}
KNOWN_FSTRING_KEY_OPTIONS = {
    ("admin-broadcast-audience-", "audience_type"): ("active", "all", "inactive", "trial"),
    ("admin-referral-first-purchase-", "action"): ("disabled", "enabled"),
    ("admin-referral-lifetime-", "action"): ("disabled", "enabled"),
    ("admin-referral-system-", "action"): ("disabled", "enabled"),
    ("admin-referral-type-", "new_type"): ("fixed", "percentage"),
}


@dataclass(frozen=True)
class MessageInfo:
    key: str
    variables: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class UsedKey:
    key: str
    path: Path
    line: int

    def location(self) -> str:
        return f"{self.path.relative_to(ROOT)}:{self.line}"


def walk_fluent(node: object) -> Iterator[object]:
    if node is None or isinstance(node, str | bytes | int | float | bool):
        return
    if isinstance(node, list | tuple):
        for item in node:
            yield from walk_fluent(item)
        return

    yield node
    fields = getattr(node, "__dict__", {})
    for name, value in fields.items():
        if name in {"span", "comment"}:
            continue
        yield from walk_fluent(value)


def parse_message_sources(path: Path) -> dict[str, str]:
    messages: dict[str, list[str]] = {}
    current_key: str | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        match = MESSAGE_ID_RE.match(line)
        if match:
            current_key = match.group(1)
            messages[current_key] = [line]
            continue
        if current_key is not None:
            messages[current_key].append(line)

    return {key: "\n".join(lines) for key, lines in messages.items()}


def parse_ftl_file(path: Path) -> tuple[dict[str, MessageInfo], list[str]]:
    source_by_key = parse_message_sources(path)
    resource = FluentParser().parse(path.read_text(encoding="utf-8"))
    messages: dict[str, MessageInfo] = {}
    failures: list[str] = []

    for entry in resource.body:
        if isinstance(entry, fluent_ast.Junk):
            content = entry.content.strip().replace("\n", " ")[:120]
            failures.append(f"{path.relative_to(ROOT)}: invalid Fluent entry: {content}")
            continue
        if not isinstance(entry, fluent_ast.Message):
            continue

        variables = sorted(
            {
                item.id.name
                for item in walk_fluent(entry)
                if isinstance(item, fluent_ast.VariableReference)
            }
        )
        key = entry.id.name
        messages[key] = MessageInfo(
            key=key,
            variables=tuple(variables),
            source=source_by_key.get(key, ""),
        )

    return messages, failures


def locale_contract(locale: str) -> tuple[dict[str, dict[str, MessageInfo]], list[str]]:
    locale_dir = LOCALES_DIR / locale
    if not locale_dir.is_dir():
        return {}, [f"missing locale directory: {locale}"]

    contract: dict[str, dict[str, MessageInfo]] = {}
    failures: list[str] = []
    for path in sorted(locale_dir.glob("*.ftl")):
        contract[path.name], file_failures = parse_ftl_file(path)
        failures.extend(file_failures)
    return contract, failures


def flatten_contract(contract: Mapping[str, Mapping[str, MessageInfo]]) -> dict[str, MessageInfo]:
    flat: dict[str, MessageInfo] = {}
    for filename, messages in contract.items():
        for key, info in messages.items():
            if key in flat:
                raise ValueError(f"duplicate message id across FTL files: {key}")
            flat[key] = info
    return flat


def configured_languages() -> tuple[str, ...]:
    field = BotSettings.model_fields["available_languages"]
    factory = field.default_factory
    if factory is None:
        return tuple(field.default or ())
    return tuple(factory())


def extract_used_i18n_keys() -> tuple[dict[str, list[UsedKey]], list[str]]:
    used: dict[str, list[UsedKey]] = defaultdict(list)
    dynamic: list[str] = []

    for source_dir in AUDITED_SOURCE_DIRS:
        for path in sorted(source_dir.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not is_i18n_call(node):
                    continue
                first_arg = node.args[0] if node.args else None
                options = i18n_key_options(first_arg)
                if options:
                    for key in sorted(options):
                        used[key].append(UsedKey(key, path, node.lineno))
                else:
                    dynamic.append(f"{path.relative_to(ROOT)}:{node.lineno}")

    return dict(used), dynamic


def is_i18n_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name) and node.func.id == "i18n":
        return True
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "i18n"
    )


def i18n_key_options(node: ast.AST | None) -> tuple[str, ...]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return (node.value,)

    if isinstance(node, ast.IfExp):
        body = i18n_key_options(node.body)
        orelse = i18n_key_options(node.orelse)
        if body and orelse:
            return tuple(sorted({*body, *orelse}))
        return ()

    if isinstance(node, ast.Name):
        return KNOWN_NAME_KEY_OPTIONS.get(node.id, ())

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return KNOWN_CALL_KEY_OPTIONS.get(node.func.id, ())

    if isinstance(node, ast.JoinedStr):
        return fstring_key_options(node)

    return ()


def fstring_key_options(node: ast.JoinedStr) -> tuple[str, ...]:
    if len(node.values) != 2:
        return ()
    prefix_node, variable_node = node.values
    if not (
        isinstance(prefix_node, ast.Constant)
        and isinstance(prefix_node.value, str)
        and isinstance(variable_node, ast.FormattedValue)
        and isinstance(variable_node.value, ast.Name)
    ):
        return ()

    prefix = prefix_node.value
    variable_name = variable_node.value.id
    suffixes = KNOWN_FSTRING_KEY_OPTIONS.get((prefix, variable_name))
    if suffixes is None:
        return ()
    return tuple(f"{prefix}{suffix}" for suffix in suffixes)


def fake_args(variables: Iterable[str]) -> dict[str, Any]:
    args: dict[str, Any] = {}
    for variable in variables:
        lowered = variable.lower()
        if any(hint in lowered for hint in NUMERIC_VARIABLE_HINTS):
            args[variable] = 7
        else:
            args[variable] = "TEST"
    return args


def build_bundle(locale: str) -> tuple[FluentBundle | None, list[str]]:
    locale_dir = LOCALES_DIR / locale
    if not locale_dir.is_dir():
        return None, [f"{locale}: missing locale directory"]

    bundle = FluentBundle([locale])
    failures: list[str] = []
    for path in sorted(locale_dir.glob("*.ftl")):
        resource = FluentResource(path.read_text(encoding="utf-8"))
        errors = bundle.add_resource(resource) or []
        for error in errors:
            failures.append(f"{path.relative_to(ROOT)}: {error}")
    return bundle, failures


def format_message(bundle: FluentBundle, key: str, variables: Iterable[str]) -> tuple[str | None, list[str]]:
    message = bundle.get_message(key)
    if message is None or message.value is None:
        return None, [f"missing runtime message: {key}"]

    value, errors = bundle.format_pattern(message.value, fake_args(variables))
    return str(value), [str(error) for error in errors]


def validate_telegram_html(text: str, *, location: str) -> list[str]:
    failures: list[str] = []
    stack: list[str] = []

    for match in TAG_RE.finditer(text):
        closing, raw_name, self_closing = match.groups()
        tag = raw_name.lower()
        if tag not in ALLOWED_TELEGRAM_TAGS:
            failures.append(f"{location}: unsupported Telegram HTML tag <{raw_name}>")
            continue

        if self_closing:
            continue
        if closing:
            if not stack:
                failures.append(f"{location}: closing tag </{raw_name}> without opening tag")
            elif stack[-1] != tag:
                failures.append(
                    f"{location}: closing tag </{raw_name}> does not match <{stack[-1]}>"
                )
            else:
                stack.pop()
        else:
            stack.append(tag)

    for tag in reversed(stack):
        failures.append(f"{location}: unclosed Telegram HTML tag <{tag}>")

    return failures


def check_primary_parity(
    contracts: Mapping[str, Mapping[str, Mapping[str, MessageInfo]]],
) -> list[str]:
    failures: list[str] = []
    en_contract = contracts["en"]
    ru_contract = contracts["ru"]

    missing_files = sorted(set(en_contract) - set(ru_contract))
    extra_files = sorted(set(ru_contract) - set(en_contract))
    if missing_files or extra_files:
        failures.append(f"ru/en file parity failed: missing={missing_files} extra={extra_files}")

    for filename in sorted(set(en_contract) & set(ru_contract)):
        en_messages = en_contract[filename]
        ru_messages = ru_contract[filename]
        missing_keys = sorted(set(en_messages) - set(ru_messages))
        extra_keys = sorted(set(ru_messages) - set(en_messages))
        if missing_keys or extra_keys:
            failures.append(
                f"ru/en key parity failed in {filename}: missing={missing_keys} extra={extra_keys}"
            )

        for key in sorted(set(en_messages) & set(ru_messages)):
            expected = en_messages[key].variables
            actual = ru_messages[key].variables
            if actual != expected:
                failures.append(
                    f"ru/en variable parity failed in {filename}/{key}: "
                    f"en={list(expected)} ru={list(actual)}"
                )

    return failures


def check_additional_locale_placeholders(
    contracts: Mapping[str, Mapping[str, Mapping[str, MessageInfo]]],
) -> list[str]:
    failures: list[str] = []
    en_contract = contracts[CONTRACT_LOCALE]

    for locale, contract in sorted(contracts.items()):
        if locale in PRIMARY_LOCALES:
            continue
        for filename in sorted(set(en_contract) & set(contract)):
            for key in sorted(set(en_contract[filename]) & set(contract[filename])):
                expected = en_contract[filename][key].variables
                actual = contract[filename][key].variables
                if actual != expected:
                    failures.append(
                        f"{locale}/{filename}/{key}: variable mismatch with en: "
                        f"expected={list(expected)} actual={list(actual)}"
                    )

    return failures


def check_used_key_coverage(
    used_keys: Mapping[str, Sequence[UsedKey]],
    primary_flat: Mapping[str, Mapping[str, MessageInfo]],
) -> list[str]:
    failures: list[str] = []
    for locale in PRIMARY_LOCALES:
        available = primary_flat[locale]
        missing = sorted(set(used_keys) - set(available))
        if missing:
            for key in missing:
                locations = ", ".join(item.location() for item in used_keys[key][:5])
                failures.append(f"{locale}: used key is missing: {key} at {locations}")
    return failures


def check_locale_visibility(locale_dirs: Sequence[str]) -> list[str]:
    failures: list[str] = []
    supported = tuple(SUPPORTED_LOCALES)
    configured = configured_languages()

    if configured != supported:
        failures.append(
            "config.py available_languages does not match i18n.py SUPPORTED_LOCALES: "
            f"config_only={sorted(set(configured) - set(supported))} "
            f"i18n_only={sorted(set(supported) - set(configured))}"
        )

    missing_dirs = sorted(set(supported) - set(locale_dirs))
    extra_dirs = sorted(set(locale_dirs) - set(supported))
    if missing_dirs or extra_dirs:
        failures.append(f"locale directories mismatch supported locales: missing={missing_dirs} extra={extra_dirs}")

    return failures


def check_runtime_and_tags(
    contracts: Mapping[str, Mapping[str, Mapping[str, MessageInfo]]],
) -> list[str]:
    failures: list[str] = []
    for locale, contract in sorted(contracts.items()):
        bundle, bundle_failures = build_bundle(locale)
        failures.extend(bundle_failures)
        if bundle is None:
            continue

        for filename, messages in sorted(contract.items()):
            for key, info in sorted(messages.items()):
                text, format_errors = format_message(bundle, key, info.variables)
                for error in format_errors:
                    failures.append(f"{locale}/{filename}/{key}: runtime format error: {error}")
                if text is None:
                    continue
                failures.extend(
                    validate_telegram_html(
                        text,
                        location=f"{locale}/{filename}/{key}",
                    )
                )

    return failures


def main() -> int:
    locale_dirs = sorted(path.name for path in LOCALES_DIR.iterdir() if path.is_dir())
    contracts: dict[str, dict[str, dict[str, MessageInfo]]] = {}
    failures: list[str] = []

    for locale in locale_dirs:
        contracts[locale], locale_failures = locale_contract(locale)
        failures.extend(locale_failures)

    for locale in PRIMARY_LOCALES:
        if locale not in contracts:
            failures.append(f"primary locale is missing: {locale}")

    if all(locale in contracts for locale in PRIMARY_LOCALES):
        failures.extend(check_primary_parity(contracts))

    if CONTRACT_LOCALE in contracts:
        failures.extend(check_additional_locale_placeholders(contracts))

    used_keys, dynamic_usages = extract_used_i18n_keys()
    if dynamic_usages:
        failures.extend(f"dynamic i18n key cannot be audited statically: {item}" for item in dynamic_usages)

    primary_flat: dict[str, dict[str, MessageInfo]] = {}
    for locale in PRIMARY_LOCALES:
        if locale in contracts:
            try:
                primary_flat[locale] = flatten_contract(contracts[locale])
            except ValueError as exc:
                failures.append(f"{locale}: {exc}")

    if set(primary_flat) == set(PRIMARY_LOCALES):
        failures.extend(check_used_key_coverage(used_keys, primary_flat))

    failures.extend(check_locale_visibility(locale_dirs))
    failures.extend(check_runtime_and_tags(contracts))

    total_messages = sum(len(messages) for messages in contracts.get(CONTRACT_LOCALE, {}).values())
    additional_locales = [locale for locale in locale_dirs if locale not in PRIMARY_LOCALES]

    print("CyberVPN Telegram Bot i18n audit")
    print(f"- locales visible: {len(locale_dirs)} ({', '.join(locale_dirs)})")
    print(f"- primary locales: {', '.join(PRIMARY_LOCALES)}")
    print(f"- en contract messages: {total_messages}")
    print(f"- audited source keys: {len(used_keys)}")
    print(f"- additional locales checked for syntax/runtime/placeholders: {len(additional_locales)}")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nPASS")
    print("- ru/en FTL message IDs and Fluent variables match")
    print("- used handler/keyboards i18n keys exist in ru/en")
    print("- Fluent runtime formatting and Telegram HTML tags are valid")
    print("- non-primary locale directories remain visible without v4 translation gating")
    return 0


if __name__ == "__main__":
    sys.exit(main())
