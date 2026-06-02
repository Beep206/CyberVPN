from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fluent.syntax import FluentParser, ast

from src.middlewares.i18n import SUPPORTED_LOCALES, I18nManager

if TYPE_CHECKING:
    from collections.abc import Iterator


LOCALES_DIR = Path(__file__).parents[2] / "src" / "locales"
CONTRACT_LOCALE = "en"
PRIMARY_LOCALES = ("en", "ru")


def _walk(node: object) -> Iterator[object]:
    if node is None or isinstance(node, (str, bytes, int, float, bool)):
        return

    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk(item)
        return

    yield node

    fields = getattr(node, "__dict__", {})
    for name, value in fields.items():
        if name in {"span", "comment"}:
            continue
        yield from _walk(value)


def _parse_messages(path: Path) -> dict[str, tuple[str, ...]]:
    resource = FluentParser().parse(path.read_text(encoding="utf-8"))
    messages: dict[str, tuple[str, ...]] = {}
    junk_entries: list[str] = []

    for entry in resource.body:
        if isinstance(entry, ast.Junk):
            junk_entries.append(entry.content.strip().replace("\n", " ")[:120])
            continue

        if isinstance(entry, ast.Message):
            variables = sorted(
                {
                    item.id.name
                    for item in _walk(entry)
                    if isinstance(item, ast.VariableReference)
                }
            )
            messages[entry.id.name] = tuple(variables)

    assert not junk_entries, f"{path} contains invalid Fluent entries: {junk_entries}"
    return messages


def _locale_contract(locale: str) -> dict[str, dict[str, tuple[str, ...]]]:
    locale_dir = LOCALES_DIR / locale
    assert locale_dir.is_dir(), f"Locale directory is missing: {locale}"
    return {
        path.name: _parse_messages(path)
        for path in sorted(locale_dir.glob("*.ftl"))
    }


def test_primary_locale_files_and_keys_match_english_contract() -> None:
    contract = _locale_contract(CONTRACT_LOCALE)
    failures: list[str] = []

    for locale in PRIMARY_LOCALES:
        actual = _locale_contract(locale)
        missing_files = sorted(set(contract) - set(actual))
        extra_files = sorted(set(actual) - set(contract))

        if missing_files or extra_files:
            failures.append(
                f"{locale}: missing_files={missing_files} extra_files={extra_files}"
            )

        for filename in sorted(set(contract) & set(actual)):
            missing_keys = sorted(set(contract[filename]) - set(actual[filename]))
            extra_keys = sorted(set(actual[filename]) - set(contract[filename]))
            if missing_keys or extra_keys:
                failures.append(
                    f"{locale}/{filename}: missing_keys={missing_keys} extra_keys={extra_keys}"
                )

    assert not failures, "FTL key parity failed:\n" + "\n".join(failures[:80])


def test_locale_directories_are_visible_and_parseable() -> None:
    failures: list[str] = []
    for locale in SUPPORTED_LOCALES:
        locale_dir = LOCALES_DIR / locale
        if not locale_dir.is_dir():
            failures.append(f"{locale}: locale directory is missing")
            continue
        if not list(locale_dir.glob("*.ftl")):
            failures.append(f"{locale}: locale directory has no FTL files")
            continue
        _locale_contract(locale)

    assert not failures, "Locale visibility failed:\n" + "\n".join(failures[:80])


def test_locale_variables_match_english_contract_where_keys_exist() -> None:
    contract = _locale_contract(CONTRACT_LOCALE)
    failures: list[str] = []

    for locale in SUPPORTED_LOCALES:
        actual = _locale_contract(locale)
        for filename, messages in contract.items():
            for key, expected_variables in messages.items():
                actual_variables = actual.get(filename, {}).get(key)
                if actual_variables is None and locale not in PRIMARY_LOCALES:
                    continue
                if actual_variables != expected_variables:
                    failures.append(
                        f"{locale}/{filename}/{key}: "
                        f"expected={list(expected_variables)} actual={list(actual_variables or ())}"
                    )

    assert not failures, "FTL variable parity failed:\n" + "\n".join(failures[:80])


def test_trial_offer_formats_without_raw_placeholders_for_all_locales() -> None:
    manager = I18nManager(LOCALES_DIR, locales=SUPPORTED_LOCALES)
    missing_bundles = [
        locale for locale in SUPPORTED_LOCALES if manager.get_bundle(locale) is None
    ]

    assert not missing_bundles, f"Locale bundles failed to load: {missing_bundles}"

    failures: list[str] = []
    for locale in SUPPORTED_LOCALES:
        text = manager.get_translator(locale)("trial-offer", days=7)
        if "traffic_gb" in text or "{ $" in text:
            failures.append(f"{locale}: {text!r}")

    assert not failures, "trial-offer leaked raw placeholders:\n" + "\n".join(failures)
