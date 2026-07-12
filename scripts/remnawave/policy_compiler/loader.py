from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import PremiumSmartRuPolicy


class PolicyLoadError(ValueError):
    """Raised when a policy source is malformed or violates its schema."""


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise PolicyLoadError(
                f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_policy(path: str | Path) -> PremiumSmartRuPolicy:
    policy_path = Path(path)
    try:
        raw = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyLoadError(f"cannot read policy {policy_path}: {exc}") from exc

    try:
        data = yaml.load(raw, Loader=UniqueKeyLoader)
    except PolicyLoadError:
        raise
    except yaml.YAMLError as exc:
        raise PolicyLoadError(f"invalid YAML in {policy_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise PolicyLoadError(f"policy {policy_path} must contain a YAML mapping")

    try:
        return PremiumSmartRuPolicy.model_validate(data)
    except ValidationError as exc:
        raise PolicyLoadError(
            f"policy validation failed for {policy_path}:\n{exc}"
        ) from exc
