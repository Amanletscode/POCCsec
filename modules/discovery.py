from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import re

import pandas as pd

from .config import (
    DESIGNATIONS,
    DOMAINS,
    LANGUAGES,
    LOCATIONS,
    SEARCH_ALIASES,
    SKILL_ALIASES,
    SKILL_CATALOG,
    STANDARD_WEEK_HOURS,
    TIME_ZONES,
)
from .engine import candidate_capacity
from .validation import normalize_skill_name, parse_skill_string, split_pipe


@dataclass
class DiscoveryIntent:
    raw: str
    intent: str = "expert_finder"
    skills: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    locations: set[str] = field(default_factory=set)
    geographies: set[str] = field(default_factory=set)
    time_zones: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)
    designations: set[str] = field(default_factory=set)
    terms: set[str] = field(default_factory=set)
    availability_min: float | None = None
    availability_max: float | None = None
    start_date: date | None = None
    requested_contact: bool = False
    interpreted_by: str = "deterministic"


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"\b" + re.escape(phrase.lower()) + r"\b", text.lower()) is not None


def _parse_availability(text: str) -> tuple[float | None, float | None]:
    hours_range = re.search(
        r"\b(\d{1,2}(?:\.\d+)?)\s*(?:-|–|to)\s*"
        r"(\d{1,2}(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b",
        text,
        flags=re.IGNORECASE,
    )
    if hours_range:
        low, high = sorted(map(float, hours_range.groups()))
        if 0 <= low <= high <= STANDARD_WEEK_HOURS:
            return low / STANDARD_WEEK_HOURS * 100, high / STANDARD_WEEK_HOURS * 100
        return None, None
    hours_value = re.search(
        r"\b(\d{1,2}(?:\.\d+)?)\s*(?:hours?|hrs?)\s*"
        r"(?:available|availability|capacity|free)?",
        text,
        flags=re.IGNORECASE,
    )
    if hours_value:
        value = float(hours_value.group(1))
        return (
            (value / STANDARD_WEEK_HOURS * 100, None)
            if 0 <= value <= STANDARD_WEEK_HOURS
            else (None, None)
        )
    range_match = re.search(
        r"\b(\d{1,3})\s*(?:-|–|to)\s*(\d{1,3})\s*%",
        text,
        flags=re.IGNORECASE,
    )
    if range_match:
        low, high = sorted(map(float, range_match.groups()))
        return (low, high) if 0 <= low <= high <= 100 else (None, None)
    value_match = re.search(
        r"\b(\d{1,3})\s*%\s*(?:available|availability|capacity|allocation)?",
        text,
        flags=re.IGNORECASE,
    )
    if value_match:
        value = float(value_match.group(1))
        return (value, None) if 0 <= value <= 100 else (None, None)
    return None, None


def _parse_date(text: str) -> date | None:
    iso = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if not iso:
        return None
    try:
        return date(*map(int, iso.groups()))
    except ValueError:
        return None


def interpret_query(text: str) -> DiscoveryIntent:
    raw = str(text or "").strip()
    lower = raw.lower()
    intent_name = "capability_discovery"
    if any(
        phrase in lower
        for phrase in [
            "who should i contact",
            "who do i contact",
            "contact for",
            "expert",
            "sme",
            "who knows",
            "who has",
        ]
    ):
        intent_name = "expert_finder"
    if any(
        phrase in lower
        for phrase in ["available", "capacity", "staff", "resource", "allocate", "allocation", "%"]
    ):
        intent_name = "resource_matching"

    output = DiscoveryIntent(
        raw=raw,
        intent=intent_name,
        requested_contact=any(term in lower for term in ["contact", "email", "reach"]),
    )
    for skill in sorted(SKILL_CATALOG + list(SKILL_ALIASES), key=len, reverse=True):
        if _contains_phrase(raw, skill):
            canonical = normalize_skill_name(skill)
            if canonical:
                output.skills.add(canonical)
    for domain in sorted(DOMAINS, key=len, reverse=True):
        if _contains_phrase(raw, domain):
            output.domains.add(domain)
    for location in sorted(LOCATIONS, key=len, reverse=True):
        if _contains_phrase(raw, location):
            output.locations.add(location)
    for designation in sorted(DESIGNATIONS, key=len, reverse=True):
        if _contains_phrase(raw, designation):
            output.designations.add(designation)
    for timezone in TIME_ZONES:
        if timezone.lower() in lower:
            output.time_zones.add(timezone)
    for language in LANGUAGES:
        if _contains_phrase(raw, language):
            output.languages.add(language)
    for phrase, payload in SEARCH_ALIASES.items():
        if _contains_phrase(raw, phrase):
            output.locations |= payload.get("locations", set())
            output.geographies |= payload.get("geographies", set())
            output.skills |= payload.get("skills", set())
            output.terms |= payload.get("tags", set())
    output.availability_min, output.availability_max = _parse_availability(raw)
    output.start_date = _parse_date(raw)

    ignored = {
        "who",
        "should",
        "have",
        "for",
        "the",
        "and",
        "with",
        "from",
        "project",
        "expertise",
        "contact",
        "available",
        "availability",
        "capacity",
    }
    output.terms |= {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9&'-]{2,}", lower)
        if token not in ignored
    }
    return output


def _intent_from_payload(raw: str, payload: dict) -> DiscoveryIntent:
    """Validate an approved LLM's structured payload against governed values."""
    deterministic = interpret_query(raw)
    for field_name, allowed in [
        ("skills", set(SKILL_CATALOG)),
        ("domains", set(DOMAINS)),
        ("locations", set(LOCATIONS)),
        ("time_zones", set(TIME_ZONES)),
        ("languages", set(LANGUAGES)),
        ("designations", set(DESIGNATIONS)),
    ]:
        values = set(payload.get(field_name) or [])
        setattr(deterministic, field_name, values.intersection(allowed))
    deterministic.geographies = {
        str(value).strip() for value in payload.get("geographies") or [] if str(value).strip()
    }
    deterministic.terms = {
        str(value).strip() for value in payload.get("terms") or [] if str(value).strip()
    }
    minimum = pd.to_numeric(payload.get("availability_min"), errors="coerce")
    maximum = pd.to_numeric(payload.get("availability_max"), errors="coerce")
    deterministic.availability_min = (
        float(minimum) if pd.notna(minimum) and 0 <= float(minimum) <= 100 else None
    )
    deterministic.availability_max = (
        float(maximum) if pd.notna(maximum) and 0 <= float(maximum) <= 100 else None
    )
    parsed_date = pd.to_datetime(payload.get("start_date"), errors="coerce")
    deterministic.start_date = parsed_date.date() if pd.notna(parsed_date) else None
    deterministic.intent = str(payload.get("intent") or deterministic.intent)
    deterministic.interpreted_by = "llm"
    return deterministic


def interpret_with_runtime(text: str, llm_adapter=None) -> DiscoveryIntent:
    """Use an optional runtime LLM adapter, with a safe deterministic fallback."""
    if llm_adapter is None:
        return interpret_query(text)
    try:
        payload = llm_adapter.interpret(text, mock_llm_adapter_spec())
        if not isinstance(payload, dict):
            raise TypeError("LLM adapter must return a dictionary")
        return _intent_from_payload(text, payload)
    except Exception:
        return interpret_query(text)


def discovery_search(
    resources: pd.DataFrame,
    capacity: pd.DataFrame,
    query: str,
    limit: int = 10,
    llm_adapter=None,
) -> tuple[DiscoveryIntent, pd.DataFrame]:
    intent = interpret_with_runtime(query, llm_adapter)
    if resources is None or resources.empty:
        return intent, pd.DataFrame()

    rows = []
    for _, resource in resources.iterrows():
        skill_map = parse_skill_string(resource.get("skills"))
        skills = set(skill_map)
        domains = split_pipe(resource.get("domains"))
        geography = split_pipe(resource.get("geography_expertise"))

        # Countries are strict work-location filters. Geography expertise is a
        # separate contextual filter and never broadens a country request.
        if intent.locations and str(resource.get("location")) not in intent.locations:
            continue
        if intent.geographies and not intent.geographies.intersection(geography):
            continue
        if intent.skills and not intent.skills.issubset(skills):
            continue
        if intent.domains and not intent.domains.intersection(domains):
            continue
        if intent.designations and str(resource.get("role_title")) not in intent.designations:
            continue
        if intent.time_zones and str(resource.get("time_zone")) not in intent.time_zones:
            continue
        if intent.languages and not intent.languages.issubset(split_pipe(resource.get("languages"))):
            continue

        minimum_available = None
        if intent.availability_min is not None:
            start = intent.start_date or pd.Timestamp.today().date()
            window = candidate_capacity(capacity, str(resource.get("resource_id")), start, start, 0)
            values = pd.to_numeric(window["available_capacity_pct"], errors="coerce").dropna()
            if values.empty:
                continue
            minimum_available = float(values.min())
            if minimum_available < intent.availability_min:
                continue
            if intent.availability_max is not None and minimum_available > intent.availability_max:
                continue

        searchable = " ".join(
            [
                str(resource.get("resource_name", "")),
                str(resource.get("team", "")),
                str(resource.get("role_title", "")),
                str(resource.get("domains", "")),
                str(resource.get("development_interests", "")),
                str(resource.get("project_expertise", "")),
                str(resource.get("geography_expertise", "")),
                str(resource.get("expertise_summary", "")),
            ]
        ).lower()
        term_hits = [term for term in intent.terms if term.lower() in searchable]
        matched_skills = intent.skills.intersection(skills)
        score = 25.0
        score += 40.0 if intent.skills else 0.0
        score += 15.0 if intent.domains else 0.0
        score += 10.0 if intent.locations or intent.geographies else 0.0
        score += min(10.0, len(term_hits) * 2.0)
        if intent.skills:
            score += min(
                10.0,
                sum(skill_map[skill] for skill in matched_skills)
                / max(1, 4 * len(intent.skills))
                * 10.0,
            )
        rows.append(
            {
                "resource_id": str(resource.get("resource_id")),
                "resource_name": str(resource.get("resource_name")),
                "team": str(resource.get("team")),
                "role_title": str(resource.get("role_title")),
                "grade": int(resource.get("grade")),
                "location": str(resource.get("location")),
                "time_zone": str(resource.get("time_zone")),
                "languages": str(resource.get("languages")),
                "minimum_available_pct": minimum_available,
                "score": round(min(score, 100.0), 1),
                "key_skills": ", ".join(
                    sorted(matched_skills)
                    if intent.skills
                    else sorted(skills, key=lambda name: -skill_map[name])[:6]
                ),
                "domains": str(resource.get("domains", "")),
                "geography_expertise": str(resource.get("geography_expertise", "")),
                "project_expertise": str(resource.get("project_expertise", "")),
                "contact_email": str(resource.get("contact_email", "")),
                "manager_name": str(resource.get("manager_name", "Not provided")),
                "manager_email": str(resource.get("manager_email", "")),
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = (
            result.sort_values(["score", "resource_name"], ascending=[False, True])
            .head(limit)
            .reset_index(drop=True)
        )
        result["rank"] = range(1, len(result) + 1)
    return intent, result


def intent_summary(intent: DiscoveryIntent) -> dict:
    payload = asdict(intent)
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, False, "", set()) and key not in {"raw", "terms"}
    }


def mock_llm_adapter_spec() -> dict:
    return {
        "interface": "adapter.interpret(text, schema) -> dict",
        "purpose": "Interpret natural language into governed filters only",
        "fields": {
            "intent": ["expert_finder", "capability_discovery", "resource_matching"],
            "skills": SKILL_CATALOG,
            "domains": DOMAINS,
            "locations": LOCATIONS,
            "geographies": "list[str]",
            "time_zones": TIME_ZONES,
            "languages": LANGUAGES,
            "designations": DESIGNATIONS,
            "availability_min": "number 0..100 or null",
            "availability_max": "number 0..100 or null",
            "start_date": "YYYY-MM-DD or null",
            "terms": "list[str]",
        },
        "runtime_guardrails": [
            "Validate every returned value against governed catalogues",
            "Fall back to deterministic parsing on timeout or invalid output",
            "Never allow model output to change hard gates or scoring policy",
            "Do not send unnecessary employee fields to the model",
        ],
    }
