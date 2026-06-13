"""Rules engine: resolve the legal posture of each countermeasure.

For a given authority profile and location, the engine selects every applicable
rule (federal ∩ state ∩ profile, with optional location predicates), applies any
profile-specific exception, and combines results with **most-restrictive-wins**.

Design intent: the engine never invents legality. If no rule matches, mitigation
defaults to ``conditional`` with a "verify" note (advisory, not authorizing) and
detection defaults to ``permitted``. This keeps the tool honest about gaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Citation, LocationAttributes, Rule
from ..taxonomy import Countermeasure, Profile, is_detection
from .loader import load_rules

# Ordering for most-restrictive-wins.
_RANK: dict[str, int] = {"permitted": 0, "conditional": 1, "prohibited": 2}


@dataclass
class ResolvedCountermeasure:
    countermeasure: Countermeasure
    effect: str
    rationale: str
    citations: list[Citation] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)


def _rule_applies(rule: Rule, profile: Profile, loc: LocationAttributes) -> bool:
    """A rule applies to a profile if the profile is listed OR an exception
    names it, and any required location flag is present."""
    named = profile in rule.applies_to_profiles or any(
        exc.profile == profile for exc in rule.exceptions
    )
    if not named:
        return False
    if rule.requires_location_flag:
        return bool(loc.location_flags.get(rule.requires_location_flag, False))
    return True


def _effective_effect(rule: Rule, profile: Profile) -> tuple[str, list[str]]:
    """Resolve this single rule's effect for the profile, applying exceptions."""
    for exc in rule.exceptions:
        if exc.profile == profile:
            return exc.effect, list(exc.conditions)
    return rule.effect, []


def resolve(
    profile: Profile,
    loc: LocationAttributes,
    credible_threat: bool = False,
) -> dict[Countermeasure, ResolvedCountermeasure]:
    """Return a resolved posture for every countermeasure class."""
    rules = load_rules()
    results: dict[Countermeasure, ResolvedCountermeasure] = {}

    for cm in Countermeasure:
        applicable = [
            r for r in rules if r.countermeasure == cm and _rule_applies(r, profile, loc)
        ]

        if not applicable:
            results[cm] = _default_for(cm)
            continue

        best_effect = "permitted"
        rationales: list[str] = []
        citations: list[Citation] = []
        conditions: list[str] = []

        for rule in applicable:
            effect, exc_conditions = _effective_effect(rule, profile)
            if _RANK[effect] > _RANK[best_effect]:
                best_effect = effect
            citations.append(rule.citation)
            conditions.extend(exc_conditions)
            # Keep the rationale from rules at the winning (or higher) severity.
            rationales.append(f"{rule.rationale} [{rule.jurisdiction}]")

        # A credible-threat declaration can satisfy a common condition.
        conditions = _dedupe(conditions)
        if credible_threat and "credible_threat" in conditions:
            conditions = [c for c in conditions if c != "credible_threat"]
            conditions.append("credible_threat (declared)")

        results[cm] = ResolvedCountermeasure(
            countermeasure=cm,
            effect=best_effect,
            rationale=" ".join(_dedupe(rationales)),
            citations=_dedupe_citations(citations),
            conditions=conditions,
        )

    return results


def _default_for(cm: Countermeasure) -> ResolvedCountermeasure:
    if is_detection(cm):
        return ResolvedCountermeasure(
            countermeasure=cm,
            effect="permitted",
            rationale="No explicit restriction matched; passive detection is generally "
            "permissible. Confirm no signal interception/decoding occurs (Wiretap/Pen-Trap).",
        )
    return ResolvedCountermeasure(
        countermeasure=cm,
        effect="conditional",
        rationale="No explicit rule matched for this profile/location. Treat as requiring "
        "legal verification before use — do not assume authorization.",
        conditions=["verify_with_counsel"],
    )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _dedupe_citations(items: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    out: list[Citation] = []
    for c in items:
        key = c.statute
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out
