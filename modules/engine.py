from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .config import DEFAULT_WEIGHTS, GRADE_LEVELS, PROFICIENCY, CAPACITY_POLICY
from .validation import parse_skill_string, split_pipe


@dataclass
class MatchResult:
    table: pd.DataFrame
    diagnostics: dict


def grade_ok(candidate: str, minimum: str, maximum: str) -> bool:
    try:
        c, lo, hi = GRADE_LEVELS.index(candidate), GRADE_LEVELS.index(minimum), GRADE_LEVELS.index(maximum)
        return lo <= c <= hi
    except (ValueError, TypeError):
        return False


def date_range_weeks(start, end) -> pd.DatetimeIndex:
    s = pd.Timestamp(start).normalize()
    e = pd.Timestamp(end).normalize()
    first = s - pd.Timedelta(days=s.weekday())
    last = e - pd.Timedelta(days=e.weekday())
    return pd.date_range(first, last, freq="7D")


def _prepare_capacity(capacity: pd.DataFrame) -> pd.DataFrame:
    if capacity is None or capacity.empty:
        return pd.DataFrame(columns=["resource_id", "week_start", "working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"])
    c = capacity.copy()
    c["resource_id"] = c["resource_id"].astype(str)
    c["week_start"] = pd.to_datetime(c["week_start"], errors="coerce").dt.normalize()
    for col in ["working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"]:
        c[col] = pd.to_numeric(c[col], errors="coerce")
    return c


def _window_from_resource_frame(resource_capacity: pd.DataFrame, weeks: pd.DatetimeIndex, allocation: float) -> pd.DataFrame:
    if resource_capacity is None or resource_capacity.empty:
        out = pd.DataFrame(index=weeks)
    else:
        out = resource_capacity.drop_duplicates("week_start").set_index("week_start").reindex(weeks)
    for col in ["working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"]:
        if col not in out.columns:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["data_missing"] = out[["working_capacity_pct", "confirmed_allocation_pct", "leave_pct"]].isna().any(axis=1)
    out["working_capacity_pct"] = out["working_capacity_pct"].fillna(0)
    out["confirmed_allocation_pct"] = out["confirmed_allocation_pct"].fillna(0)
    out["tentative_allocation_pct"] = out["tentative_allocation_pct"].fillna(0)
    out["leave_pct"] = out["leave_pct"].fillna(0)
    out["available_pct"] = (out.working_capacity_pct - out.confirmed_allocation_pct - out.leave_pct).clip(0, 100)
    out["net_available_after_tentative_pct"] = (out.available_pct - out.tentative_allocation_pct).clip(0, 100)
    out["required_pct"] = float(allocation)
    out["gap_pct"] = (out.required_pct - out.available_pct).clip(0, 100)
    out["tentative_gap_pct"] = (out.required_pct - out.net_available_after_tentative_pct).clip(0, 100)
    out["status"] = np.where(out.data_missing, "Missing capacity data", np.where(out.available_pct >= allocation, "Covered", "Below demand"))
    return out.reset_index(names="week_start")


def candidate_capacity(capacity: pd.DataFrame, resource_id: str, start, end, allocation: float) -> pd.DataFrame:
    weeks = date_range_weeks(start, end)
    c = _prepare_capacity(capacity)
    return _window_from_resource_frame(c[c.resource_id.eq(str(resource_id))], weeks, allocation)


def capacity_stats(window: pd.DataFrame, allocation: float, tentative_reserved: bool = False) -> dict:
    if window is None or window.empty:
        return {"min_available_pct": 0.0, "median_available_pct": 0.0, "p10_available_pct": 0.0,
                "weeks_below_demand": 999, "max_gap_pct": float(allocation), "tentative_risk_weeks": 0,
                "coverage_ratio": 0.0, "missing_weeks": 999}
    available = window.available_pct.to_numpy(dtype=float)
    comparable = window.net_available_after_tentative_pct.to_numpy(dtype=float) if tentative_reserved else available
    return {
        "min_available_pct": float(np.min(available)),
        "median_available_pct": float(np.median(available)),
        "p10_available_pct": float(np.percentile(available, 10)),
        "weeks_below_demand": int(np.sum(comparable + CAPACITY_POLICY.allow_small_capacity_shortfall_pct < allocation)),
        "max_gap_pct": float(np.max(np.maximum(allocation - comparable, 0))),
        "tentative_risk_weeks": int(np.sum(window.net_available_after_tentative_pct < allocation)),
        "coverage_ratio": float(np.mean(comparable >= allocation)),
        "missing_weeks": int(window.data_missing.sum()),
    }


def normalize_weights(weights: dict | None) -> dict[str, float]:
    base = dict(DEFAULT_WEIGHTS)
    if weights:
        for key in base:
            try:
                base[key] = max(0.0, float(weights.get(key, base[key])))
            except (TypeError, ValueError):
                pass
    total = sum(base.values())
    return {k: v / total for k, v in base.items()} if total else dict(DEFAULT_WEIGHTS)


def skill_score(candidate: dict[str, int], required: dict[str, int]) -> float:
    if not required:
        return 100.0
    vals = [min(candidate.get(skill, 0) / max(level, 1), 1.0) * 100 for skill, level in required.items()]
    return float(np.mean(vals)) if vals else 100.0


def preferred_score(candidate: dict[str, int], required: dict[str, int]) -> float:
    if not required:
        return 50.0
    vals = [min(candidate.get(skill, 0) / max(level, 1), 1.0) * 100 for skill, level in required.items()]
    return float(np.mean(vals)) if vals else 50.0


def proficiency_score(candidate: dict[str, int], mandatory: dict[str, int], preferred: dict[str, int]) -> float:
    req = {**preferred, **mandatory}
    if not req:
        return 50.0
    vals = [min(candidate.get(skill, 0) / max(level, 1), 1.0) * 100 for skill, level in req.items()]
    return float(np.mean(vals)) if vals else 50.0


def evidence_score(resource_id: str, resource_row: pd.Series, evidence_by_resource: dict[str, pd.DataFrame], request: dict) -> tuple[float, list[str]]:
    e = evidence_by_resource.get(str(resource_id))
    if e is None or e.empty:
        return 0.0, []
    requested_domains = set(request.get("domains") or [])
    required_skills = set((request.get("mandatory_skills") or {})) | set((request.get("preferred_skills") or {}))
    domain_hits = 0
    skill_hits = 0
    for _, x in e.iterrows():
        used = split_pipe(x.get("skills_used"))
        if required_skills.intersection(used):
            skill_hits += 1
        if x.get("domain") in requested_domains:
            domain_hits += 1
    years_raw = pd.to_numeric(resource_row.get("years_experience"), errors="coerce")
    rating_raw = pd.to_numeric(resource_row.get("delivery_rating"), errors="coerce")
    exp = min(float(years_raw) if pd.notna(years_raw) else 0, 10) / 10 * 100
    rating = min(max(float(rating_raw) if pd.notna(rating_raw) else 0, 0), 5) / 5 * 100
    domain_score = 100 if domain_hits else (45 if not requested_domains else 25)
    skill_evidence = min(skill_hits / 3, 1) * 100
    score = 0.30 * exp + 0.25 * rating + 0.25 * domain_score + 0.20 * skill_evidence
    summaries = []
    ordered = e.copy()
    ordered["project_end"] = pd.to_datetime(ordered["project_end"], errors="coerce")
    ordered["outcome_score"] = pd.to_numeric(ordered["outcome_score"], errors="coerce").fillna(0)
    for _, x in ordered.sort_values(["project_end", "outcome_score"], ascending=[False, False]).head(4).iterrows():
        summaries.append(f"{x.project_name} | {x.domain} | {x.duration_months}m | outcome {x.outcome_score:.1f}")
    return float(score), summaries


def run_matching(resources: pd.DataFrame, capacity: pd.DataFrame, evidence: pd.DataFrame, request: dict, weights: dict | None = None) -> MatchResult:
    weights = normalize_weights(weights)
    if resources is None or resources.empty:
        return MatchResult(pd.DataFrame(), {"resources_assessed": 0, "eligible": 0, "excluded": 0, "zero_match": True, "message": "No resources are available."})

    weeks = date_range_weeks(request["start_date"], request["end_date"])
    c = _prepare_capacity(capacity)
    capacity_by_resource = {rid: group for rid, group in c.groupby("resource_id", sort=False)}
    ev = evidence.copy() if evidence is not None else pd.DataFrame()
    evidence_by_resource = {rid: group for rid, group in ev.groupby("resource_id", sort=False)} if not ev.empty and "resource_id" in ev.columns else {}

    rows = []
    counts = {k: 0 for k in ["location", "time_zone", "language", "domain", "grade", "mandatory_skill", "mandatory_proficiency", "capacity_data", "capacity"]}
    for _, r in resources.iterrows():
        rid = str(r.get("resource_id", ""))
        skills = parse_skill_string(r.get("skills"))
        langs = split_pipe(r.get("languages"))
        domains = split_pipe(r.get("domains"))
        window = _window_from_resource_frame(capacity_by_resource.get(rid), weeks, request["allocation_pct"])
        stats = capacity_stats(window, request["allocation_pct"], tentative_reserved=False)
        missing_mandatory = [s for s in request.get("mandatory_skills", {}) if s not in skills]
        below_mandatory = [s for s, lvl in request.get("mandatory_skills", {}).items() if skills.get(s, 0) < lvl]
        missing_preferred = [s for s in request.get("preferred_skills", {}) if s not in skills]

        gates = {
            "Location": not request.get("allowed_locations") or str(r.get("location")) in request["allowed_locations"],
            "Time zone": not request.get("time_zones") or str(r.get("time_zone")) in request["time_zones"],
            "Language": set(request.get("languages") or []).issubset(langs),
            "Domain": not request.get("domain_strict") or not request.get("domains") or bool(domains.intersection(request.get("domains"))),
            "Grade": grade_ok(str(r.get("grade")), request.get("grade_min"), request.get("grade_max")),
            "Mandatory skill presence": not missing_mandatory,
            "Mandatory proficiency": not below_mandatory,
            "Capacity data": stats["missing_weeks"] == 0,
            "Weekly capacity": (stats["weeks_below_demand"] == 0) if request.get("capacity_strict", True) else True,
        }
        reason_map = {
            "Location": "Location mismatch", "Time zone": "Time-zone mismatch", "Language": "Required language missing",
            "Domain": "Domain mismatch", "Grade": "Grade outside requested range", "Mandatory skill presence": "Mandatory skill missing",
            "Mandatory proficiency": "Mandatory proficiency below required level", "Capacity data": "Missing weekly capacity data",
            "Weekly capacity": "Insufficient weekly capacity",
        }
        reasons = [reason_map[k] for k, ok in gates.items() if not ok]
        for key, ok in {"location": gates["Location"], "time_zone": gates["Time zone"], "language": gates["Language"], "domain": gates["Domain"],
                         "grade": gates["Grade"], "mandatory_skill": gates["Mandatory skill presence"], "mandatory_proficiency": gates["Mandatory proficiency"],
                         "capacity_data": gates["Capacity data"], "capacity": gates["Weekly capacity"]}.items():
            if not ok:
                counts[key] += 1
        eligible = not reasons

        score_mand = skill_score(skills, request.get("mandatory_skills", {}))
        score_pref = preferred_score(skills, request.get("preferred_skills", {}))
        score_prof = proficiency_score(skills, request.get("mandatory_skills", {}), request.get("preferred_skills", {}))
        score_evidence, evidence_summary = evidence_score(rid, r, evidence_by_resource, request)
        score_capacity = max(0.0, min(100.0, stats["coverage_ratio"] * 100.0))
        score_delivery_fit = 100.0 if gates["Location"] and gates["Time zone"] and gates["Language"] else 0.0
        dev = split_pipe(r.get("development_interests"))
        preferred_set = set(request.get("preferred_skills", {}))
        score_development = 100.0 * len(dev.intersection(preferred_set)) / max(1, len(preferred_set)) if preferred_set else 50.0
        conf_raw = pd.to_numeric(r.get("profile_confidence"), errors="coerce")
        score_confidence = float(max(0, min(100, (float(conf_raw) if pd.notna(conf_raw) else 0.5) * 100)))
        normalized_components = {
            "mandatory_skills": score_mand, "preferred_skills": score_pref, "proficiency": score_prof, "relevant_evidence": score_evidence,
            "capacity": score_capacity, "delivery_fit": score_delivery_fit, "development_alignment": score_development, "data_confidence": score_confidence,
        }
        contributions = {key: normalized_components[key] * weights[key] for key in weights}
        total_score = float(sum(contributions.values())) if eligible else 0.0
        risks = []
        if stats["tentative_risk_weeks"] > 0:
            risks.append(f"Tentative commitments could consume headroom in {stats['tentative_risk_weeks']} week(s).")
        if not request.get("capacity_strict", True) and stats["weeks_below_demand"] > 0:
            risks.append(f"Confirmed availability falls below demand in {stats['weeks_below_demand']} week(s).")
        if (float(conf_raw) if pd.notna(conf_raw) else 0.5) < 0.8:
            risks.append("Profile confidence is below 80%; verify current information.")
        if score_evidence < 50:
            risks.append("Relevant delivery evidence is limited for this request.")

        rows.append({
            "resource_id": rid, "resource_name": str(r.get("resource_name", "")), "team": str(r.get("team", "")), "grade": str(r.get("grade", "")),
            "role_title": str(r.get("role_title", "")), "location": str(r.get("location", "")), "time_zone": str(r.get("time_zone", "")),
            "languages": str(r.get("languages", "")), "status": "Eligible" if eligible else "Excluded", "exclusion_reasons": reasons, "gates": gates,
            "total_score": round(total_score, 2), "score_components": {k: round(v, 2) for k, v in contributions.items()},
            "minimum_available_pct": round(stats["min_available_pct"], 1), "median_available_pct": round(stats["median_available_pct"], 1),
            "weeks_below_demand": stats["weeks_below_demand"], "max_gap_pct": round(stats["max_gap_pct"], 1), "tentative_risk_weeks": stats["tentative_risk_weeks"],
            "missing_capacity_weeks": stats["missing_weeks"], "coverage_ratio": stats["coverage_ratio"],
            "missing_mandatory_skills": missing_mandatory, "below_mandatory_skills": below_mandatory, "missing_preferred_skills": missing_preferred,
            "evidence_summary": evidence_summary, "years_experience": float(pd.to_numeric(r.get("years_experience"), errors="coerce") if pd.notna(pd.to_numeric(r.get("years_experience"), errors="coerce")) else 0),
            "delivery_rating": float(pd.to_numeric(r.get("delivery_rating"), errors="coerce") if pd.notna(pd.to_numeric(r.get("delivery_rating"), errors="coerce")) else 0),
            "profile_confidence": float(conf_raw) if pd.notna(conf_raw) else 0.5, "manager_name": str(r.get("manager_name", "Not provided")),
            "manager_email": str(r.get("manager_email", "")), "contact_email": str(r.get("contact_email", "")),
            "geography_expertise": str(r.get("geography_expertise", "")), "country_expertise": str(r.get("country_expertise", "")),
            "project_expertise": str(r.get("project_expertise", "")), "capability_tags": str(r.get("capability_tags", "")), "risks": risks,
        })

    table = pd.DataFrame(rows)
    if table.empty:
        return MatchResult(table, {"resources_assessed": 0, "eligible": 0, "excluded": 0, "zero_match": True})
    feasible = table[table.status.eq("Eligible")].sort_values(["total_score", "minimum_available_pct", "profile_confidence"], ascending=[False, False, False])
    if not feasible.empty:
        n = len(feasible)
        table.loc[feasible.index, "rank"] = range(1, n + 1)
        table.loc[feasible.index, "fit_percentile"] = 100.0 if n == 1 else (feasible.total_score.rank(method="min", pct=True) * 100).round(1)
    if "rank" not in table.columns:
        table["rank"] = 0
    if "fit_percentile" not in table.columns:
        table["fit_percentile"] = 0.0
    table["rank"] = pd.to_numeric(table["rank"], errors="coerce").fillna(0).astype(int)
    table["fit_percentile"] = pd.to_numeric(table["fit_percentile"], errors="coerce").fillna(0).round(1)
    table["confidence_label"] = table.profile_confidence.map(lambda x: "High" if x >= 0.90 else "Medium" if x >= 0.80 else "Verify")
    table["status_order"] = table.status.map({"Eligible": 0, "Excluded": 1}).fillna(2)
    table = table.sort_values(["status_order", "rank", "resource_name"], ascending=[True, True, True]).drop(columns=["status_order"]).reset_index(drop=True)
    diagnostics = {
        "resources_assessed": len(table), "eligible": int((table.status == "Eligible").sum()), "excluded": int((table.status == "Excluded").sum()),
        "zero_match": feasible.empty, "request_window_weeks": len(weeks), "gate_exclusion_counts": counts,
    }
    return MatchResult(table, diagnostics)


def build_alternatives(result_table: pd.DataFrame, selected_id: str, limit: int = 3) -> list[dict]:
    if result_table is None or result_table.empty:
        return []
    pool = result_table[(result_table.status == "Eligible") & (result_table.resource_id.astype(str) != str(selected_id))].sort_values(["total_score", "minimum_available_pct"], ascending=[False, False]).head(limit)
    return pool[["resource_id", "resource_name", "team", "grade", "location", "total_score", "fit_percentile", "minimum_available_pct", "tentative_risk_weeks"]].to_dict("records")
