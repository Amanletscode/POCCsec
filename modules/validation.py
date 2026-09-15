from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd

from .config import (
    DOMAINS,
    GRADE_LEVELS,
    LANGUAGES,
    LOCATION_TO_TIMEZONE,
    LOCATIONS,
    PROFICIENCY,
    SKILL_ALIASES,
    SKILL_CATALOG,
    TIME_ZONES,
)

@dataclass
class ValidationReport:
    ok: bool
    errors: list[str]
    warnings: list[str]

REQUIRED_RESOURCE_COLUMNS = {
    "resource_id", "resource_name", "team", "grade", "location", "time_zone",
    "languages", "skills", "domains", "development_interests", "years_experience",
    "delivery_rating", "profile_confidence", "profile_updated",
}
REQUIRED_CAPACITY_COLUMNS = {
    "resource_id", "week_start", "working_capacity_pct", "confirmed_allocation_pct",
    "tentative_allocation_pct", "leave_pct",
}
REQUIRED_EVIDENCE_COLUMNS = {
    "resource_id", "project_name", "project_type", "domain", "role", "skills_used",
    "duration_months", "project_end", "outcome_score",
}

ALIAS_LOWER = {k.lower(): v for k, v in SKILL_ALIASES.items()}


def normalize_skill_name(name: Any) -> str | None:
    if name is None:
        return None
    raw = str(name).strip()
    if not raw:
        return None
    if raw in SKILL_CATALOG:
        return raw
    return ALIAS_LOWER.get(raw.lower())


def parse_skill_string(value: Any) -> dict[str, int]:
    """Safely parse pipe-delimited `Skill:Level` data. Malformed tokens are ignored."""
    if value is None:
        return {}
    if isinstance(value, dict):
        out: dict[str, int] = {}
        for name, level in value.items():
            canonical = normalize_skill_name(name)
            try:
                lvl = int(float(level))
            except (TypeError, ValueError):
                continue
            if canonical and lvl in PROFICIENCY.values():
                out[canonical] = max(out.get(canonical, 0), lvl)
        return out
    try:
        if pd.isna(value):
            return {}
    except (TypeError, ValueError):
        pass

    out: dict[str, int] = {}
    for token in str(value).replace(";", "|").split("|"):
        token = token.strip()
        if not token or ":" not in token:
            continue
        name, raw_level = token.rsplit(":", 1)
        canonical = normalize_skill_name(name)
        try:
            level = int(float(raw_level.strip()))
        except (TypeError, ValueError):
            continue
        if canonical and level in PROFICIENCY.values():
            out[canonical] = max(out.get(canonical, 0), level)
    return out


def split_pipe(value: Any) -> set[str]:
    if value is None:
        return set()
    try:
        if pd.isna(value):
            return set()
    except (TypeError, ValueError):
        pass
    return {x.strip() for x in str(value).replace(";", "|").split("|") if x.strip()}


def validate_resources(df: pd.DataFrame) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    missing = REQUIRED_RESOURCE_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Resources file is missing required columns: {', '.join(sorted(missing))}")
        return ValidationReport(False, errors, warnings)
    if df.empty:
        errors.append("Resources dataset is empty.")
        return ValidationReport(False, errors, warnings)
    if df.resource_id.astype(str).duplicated().any():
        dup = df.loc[df.resource_id.astype(str).duplicated(keep=False), "resource_id"].astype(str).unique()[:8]
        errors.append(f"Duplicate resource IDs found: {', '.join(dup)}")
    unknown_grades = sorted(set(df.grade.dropna().astype(str)) - set(GRADE_LEVELS))
    if unknown_grades:
        errors.append(f"Unknown resource grade(s): {', '.join(unknown_grades[:8])}")
    unknown_locations = sorted(set(df.location.dropna().astype(str)) - set(LOCATIONS))
    if unknown_locations:
        warnings.append(f"Unknown location(s) found: {', '.join(unknown_locations[:8])}")
    for idx, raw in df.skills.items():
        parsed = parse_skill_string(raw)
        if raw is not None and str(raw).strip() and not parsed:
            warnings.append(f"Resource row {idx + 2}: no valid governed skill entries were found.")
            if len(warnings) >= 12:
                break
    for col, lo, hi in [("delivery_rating", 0, 5), ("profile_confidence", 0, 1), ("years_experience", 0, 60)]:
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.isna().any():
                warnings.append(f"Column '{col}' contains missing/non-numeric values.")
            if ((vals.dropna() < lo) | (vals.dropna() > hi)).any():
                errors.append(f"Column '{col}' contains values outside {lo} to {hi}.")
    return ValidationReport(not errors, errors, warnings)


def validate_capacity(df: pd.DataFrame, resources: pd.DataFrame) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    missing = REQUIRED_CAPACITY_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Capacity file is missing required columns: {', '.join(sorted(missing))}")
        return ValidationReport(False, errors, warnings)
    if df.empty:
        errors.append("Capacity dataset is empty.")
        return ValidationReport(False, errors, warnings)
    cap = df.copy()
    cap["week_start"] = pd.to_datetime(cap["week_start"], errors="coerce").dt.normalize()
    if cap.week_start.isna().any():
        errors.append("Capacity contains invalid week_start values.")
    for col in ["working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"]:
        vals = pd.to_numeric(cap[col], errors="coerce")
        if vals.isna().any():
            errors.append(f"Capacity column '{col}' contains non-numeric values.")
        if ((vals < 0) | (vals > 100)).any():
            errors.append(f"Capacity column '{col}' must stay between 0 and 100.")
    unknown_ids = set(cap.resource_id.astype(str)) - set(resources.resource_id.astype(str))
    if unknown_ids:
        errors.append(f"Capacity references unknown resource IDs: {', '.join(sorted(unknown_ids)[:8])}")
    if cap.duplicated(["resource_id", "week_start"], keep=False).any():
        errors.append("Duplicate resource/week capacity rows found.")
    return ValidationReport(not errors, errors, warnings)


def validate_evidence(df: pd.DataFrame, resources: pd.DataFrame) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    missing = REQUIRED_EVIDENCE_COLUMNS - set(df.columns)
    if missing:
        errors.append(f"Delivery evidence is missing required columns: {', '.join(sorted(missing))}")
        return ValidationReport(False, errors, warnings)
    if df.empty:
        warnings.append("Delivery evidence dataset is empty. Relevant evidence scores will be conservative.")
        return ValidationReport(True, errors, warnings)
    unknown_ids = set(df.resource_id.astype(str)) - set(resources.resource_id.astype(str))
    if unknown_ids:
        errors.append(f"Delivery evidence references unknown resource IDs: {', '.join(sorted(unknown_ids)[:8])}")
    vals = pd.to_numeric(df.outcome_score, errors="coerce")
    if ((vals.dropna() < 0) | (vals.dropna() > 5)).any():
        errors.append("Evidence outcome_score must stay between 0 and 5.")
    return ValidationReport(not errors, errors, warnings)


def validate_request(request: dict) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    required = ["start_date", "end_date", "allocation_pct", "grade_min", "grade_max"]
    if any(k not in request for k in required):
        return ValidationReport(False, ["The staffing request is incomplete."], warnings)
    try:
        start = pd.Timestamp(request["start_date"]).date()
        end = pd.Timestamp(request["end_date"]).date()
        if end < start:
            errors.append("End date cannot be before start date.")
    except Exception:
        errors.append("Start and end dates must be valid dates.")
    try:
        allocation = float(request["allocation_pct"])
        if not 1 <= allocation <= 100:
            errors.append("Allocation must be between 1% and 100%.")
    except Exception:
        errors.append("Allocation must be numeric.")
    if request.get("grade_min") not in GRADE_LEVELS or request.get("grade_max") not in GRADE_LEVELS:
        errors.append("Grade range contains an unsupported grade.")
    elif GRADE_LEVELS.index(request["grade_min"]) > GRADE_LEVELS.index(request["grade_max"]):
        errors.append("Minimum grade cannot be above maximum grade.")
    for field, allowed, label in [
        ("allowed_locations", LOCATIONS, "location"),
        ("languages", LANGUAGES, "language"),
        ("time_zones", TIME_ZONES, "time zone"),
        ("domains", DOMAINS, "domain"),
    ]:
        for val in request.get(field, []) or []:
            if val not in allowed:
                errors.append(f"Unsupported {label}: {val}")
    for group in ["mandatory_skills", "preferred_skills"]:
        values = request.get(group, {}) or {}
        if not isinstance(values, dict):
            errors.append(f"{group} must be a skill-to-level mapping.")
            continue
        for skill, lvl in values.items():
            if skill not in SKILL_CATALOG:
                errors.append(f"Unsupported skill: {skill}")
            if lvl not in PROFICIENCY.values():
                errors.append(f"Invalid proficiency for {skill}.")
    overlap = set(request.get("mandatory_skills", {})) & set(request.get("preferred_skills", {}))
    if overlap:
        warnings.append(f"Skills cannot be both mandatory and preferred. Mandatory takes precedence: {', '.join(sorted(overlap))}")
    # If a timezone is explicitly selected, validate the location-to-timezone relationship only as information.
    # The actual gate remains exact on the candidate's timezone so mixed-location global searches remain possible.
    selected_locations = request.get("allowed_locations") or []
    selected_zones = request.get("time_zones") or []
    implied_zones = {LOCATION_TO_TIMEZONE.get(x) for x in selected_locations if x in LOCATION_TO_TIMEZONE}
    if selected_zones and implied_zones and not implied_zones.intersection(selected_zones):
        warnings.append("Selected locations and selected time zones do not overlap. This may intentionally produce zero matches.")
    return ValidationReport(not errors, errors, warnings)
