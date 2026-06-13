"""Load and validate the YAML rules database.

Rules live as data under backend/rules/{federal,texas}/*.yaml so that legal
updates never require a code change and citations stay bound to each rule.
Every file is validated against the Rule schema at load time; a malformed rule
fails loudly rather than silently producing a wrong recommendation.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

from ..config import settings
from ..models import Rule


def _load_dir(directory: Path) -> list[Rule]:
    rules: list[Rule] = []
    if not directory.exists():
        return rules
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw is None:
            continue
        # A file may hold a single rule (dict) or a list of rules.
        entries = raw if isinstance(raw, list) else [raw]
        for entry in entries:
            try:
                rules.append(Rule.model_validate(entry))
            except Exception as exc:  # noqa: BLE001 — surface which file/rule broke
                raise ValueError(f"Invalid rule in {path.name}: {exc}") from exc
    return rules


@functools.lru_cache(maxsize=1)
def load_rules() -> list[Rule]:
    """Load all federal + state rules once and cache them."""
    rules = _load_dir(settings.rules_dir / "federal") + _load_dir(settings.rules_dir / "texas")
    if not rules:
        raise RuntimeError(f"No rules found under {settings.rules_dir}. Cannot assess.")
    _check_duplicate_ids(rules)
    return rules


def _check_duplicate_ids(rules: list[Rule]) -> None:
    seen: set[str] = set()
    for rule in rules:
        if rule.id in seen:
            raise ValueError(f"Duplicate rule id: {rule.id}")
        seen.add(rule.id)


def reload_rules() -> list[Rule]:
    """Clear the cache and reload (useful after editing YAML in dev)."""
    load_rules.cache_clear()
    return load_rules()
