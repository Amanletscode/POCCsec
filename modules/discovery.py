from __future__ import annotations

from dataclasses import dataclass, field
import re
import pandas as pd

from .config import DOMAINS, LANGUAGES, LOCATIONS, SEARCH_ALIASES, SKILL_CATALOG, SKILL_ALIASES, TIME_ZONES
from .validation import normalize_skill_name, parse_skill_string, split_pipe


@dataclass
class DiscoveryIntent:
    raw: str
    intent: str = "expert_finder"
    skills: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    locations: set[str] = field(default_factory=set)
    time_zones: set[str] = field(default_factory=set)
    languages: set[str] = field(default_factory=set)
    terms: set[str] = field(default_factory=set)
    requested_contact: bool = False


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"\b" + re.escape(phrase.lower()) + r"\b", text.lower()) is not None


def interpret_query(text: str) -> DiscoveryIntent:
    raw = str(text or "").strip()
    lower = raw.lower()
    intent = "capability_discovery"
    if any(x in lower for x in ["who should i contact", "who do i contact", "contact for", "expert", "sme", "subject matter", "who knows", "who has"]):
        intent = "expert_finder"
    if any(x in lower for x in ["available", "capacity", "staff", "resource", "allocate", "allocation", "%"]):
        intent = "resource_matching"
    if any(x in lower for x in ["team", "capability", "expertise", "competence"]):
        intent = "capability_discovery" if intent == "expert_finder" else intent

    out = DiscoveryIntent(raw=raw, intent=intent, requested_contact=("contact" in lower or "email" in lower or "reach" in lower))
    # Exact governed vocab first, longest terms first.
    for skill in sorted(SKILL_CATALOG + list(SKILL_ALIASES.keys()), key=len, reverse=True):
        if _contains_phrase(raw, skill):
            canonical = normalize_skill_name(skill)
            if canonical:
                out.skills.add(canonical)
    for domain in sorted(DOMAINS, key=len, reverse=True):
        if _contains_phrase(raw, domain):
            out.domains.add(domain)
    for location in sorted(LOCATIONS, key=len, reverse=True):
        if _contains_phrase(raw, location):
            out.locations.add(location)
    for timezone in TIME_ZONES:
        if timezone.lower() in lower:
            out.time_zones.add(timezone)
    for language in LANGUAGES:
        if _contains_phrase(raw, language):
            out.languages.add(language)
    for phrase, payload in SEARCH_ALIASES.items():
        if _contains_phrase(raw, phrase):
            out.terms.add(phrase.upper())
            out.locations |= payload.get("locations", set())
            out.skills |= payload.get("skills", set())
            out.terms |= payload.get("tags", set())
    # Stable free-text tokens are retained as weak search terms, not hard filters.
    tokens = {t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9&'-]{2,}", lower) if t not in {"who", "should", "have", "for", "the", "and", "with", "from", "project", "expertise", "contact"}}
    out.terms |= tokens
    return out


def discovery_search(resources: pd.DataFrame, evidence: pd.DataFrame, query: str, limit: int = 10) -> tuple[DiscoveryIntent, pd.DataFrame]:
    intent = interpret_query(query)
    if resources is None or resources.empty:
        return intent, pd.DataFrame()
    rows = []
    evidence = evidence if evidence is not None else pd.DataFrame()
    for _, r in resources.iterrows():
        skill_map = parse_skill_string(r.get("skills"))
        skill_names = set(skill_map)
        domains = split_pipe(r.get("domains"))
        locations = {str(r.get("location", ""))}
        locations |= split_pipe(r.get("country_expertise"))
        geography = split_pipe(r.get("geography_expertise"))
        tags = split_pipe(r.get("project_expertise")) | split_pipe(r.get("capability_tags"))
        searchable = " ".join([
            str(r.get("resource_name", "")), str(r.get("team", "")), str(r.get("grade", "")),
            str(r.get("domains", "")), str(r.get("development_interests", "")), str(r.get("project_expertise", "")),
            str(r.get("capability_tags", "")), str(r.get("geography_expertise", "")), str(r.get("country_expertise", "")),
            str(r.get("expertise_summary", "")),
        ]).lower()
        person_evidence = evidence[evidence.resource_id.astype(str).eq(str(r.get("resource_id")))] if not evidence.empty and "resource_id" in evidence else evidence.iloc[0:0]
        evidence_text = " ".join(person_evidence.astype(str).fillna("").agg(" ".join, axis=1).tolist()).lower() if not person_evidence.empty else ""
        score = 0.0
        matched = []
        matched_skill = intent.skills.intersection(skill_names)
        if matched_skill:
            score += 35 + min(15, 5 * len(matched_skill))
            matched.extend(sorted(matched_skill))
        domain_hits = intent.domains.intersection(domains)
        if domain_hits:
            score += 20
            matched.extend(sorted(domain_hits))
        loc_hits = intent.locations.intersection(locations | geography)
        if loc_hits:
            score += 20
            matched.extend(sorted(loc_hits))
        if intent.time_zones and r.get("time_zone") in intent.time_zones:
            score += 15
            matched.append(str(r.get("time_zone")))
        if intent.languages and intent.languages.issubset(split_pipe(r.get("languages"))):
            score += 10
            matched.extend(sorted(intent.languages))
        term_hits = [term for term in intent.terms if len(term) >= 3 and term.lower() in (searchable + " " + evidence_text)]
        score += min(15, len(term_hits) * 3)
        matched.extend(term_hits[:6])
        if not (intent.skills or intent.domains or intent.locations or intent.time_zones or intent.languages):
            # Pure capability discovery gets a small, transparent relevance score rather than returning arbitrary names.
            score = min(65, 15 + 10 * ("expert" in searchable or "sme" in searchable) + 10 * ("pricing" in searchable or "analytics" in searchable))
        if score <= 0:
            continue
        rows.append({
            "resource_id": str(r.get("resource_id")), "resource_name": str(r.get("resource_name")),
            "team": str(r.get("team")), "grade": str(r.get("grade")), "location": str(r.get("location")),
            "time_zone": str(r.get("time_zone")), "languages": str(r.get("languages")),
            "contact_email": str(r.get("contact_email", "")), "manager_name": str(r.get("manager_name", "Not provided")),
            "manager_email": str(r.get("manager_email", "")), "score": round(score, 1),
            "matched_context": sorted(dict.fromkeys([x for x in matched if x])),
            "key_skills": ", ".join(sorted(skill_names.intersection(intent.skills))) if intent.skills else ", ".join(sorted(skill_names, key=lambda x: -skill_map.get(x, 0))[:6]),
            "domain_expertise": str(r.get("domains", "")), "geography_expertise": str(r.get("geography_expertise", "")),
            "project_expertise": str(r.get("project_expertise", "")),
            "expertise_summary": str(r.get("expertise_summary", "")), "profile_confidence": float(r.get("profile_confidence", 0.5) or 0.5),
        })
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["score", "profile_confidence"], ascending=[False, False]).head(limit).reset_index(drop=True)
        result["rank"] = range(1, len(result) + 1)
    return intent, result


def mock_llm_adapter_spec() -> dict:
    return {
        "interface": "interpret_request(text: str) -> DiscoveryIntent",
        "replace_with": "Approved LLM/API client in the future",
        "contract": ["intent", "skills", "domains", "locations", "time_zones", "languages", "terms", "requested_contact"],
        "guardrail": "LLM may interpret language, but deterministic validation and matching rules remain the system of record.",
    }
