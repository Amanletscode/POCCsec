from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.config import (
    DATA_VERSION, DEFAULT_WEIGHTS, DOMAINS, GRADE_LEVELS, LANGUAGES, LOCATIONS,
    PROFICIENCY, PROFICIENCY_LABELS, RULE_VERSION, SKILL_CATALOG, TAXONOMY_VERSION,
    TIME_ZONES,
)
from modules.data import canonicalize_capacity, canonicalize_evidence, canonicalize_resources, dataset_health, load_demo_data, load_workbook
from modules.discovery import discovery_search, interpret_query, mock_llm_adapter_spec
from modules.engine import build_alternatives, candidate_capacity, run_matching
from modules.sample_data import write_demo_data
from modules.validation import parse_skill_string, split_pipe, validate_request

st.set_page_config(page_title="CSEC RM Copilot", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
if not (DATA_DIR / "resources.csv").exists():
    write_demo_data(DATA_DIR)

# Always canonicalize, because uploaded/demo files can have missing optional fields.
resources, capacity, evidence = load_demo_data(DATA_DIR)


def styled_header():
    st.markdown(
        """
        <style>
        .block-container {max-width: 1550px; padding-top: 1.0rem; padding-bottom: 2.0rem;}
        .hero {padding: 1.35rem 1.55rem; border-radius: 18px; background: linear-gradient(135deg,#17365D,#315A8A); color:#fff; margin-bottom:1rem;}
        .hero h1 {margin:0;color:#fff;font-size:2.1rem;}
        .hero p {margin:.35rem 0 0;color:#eaf2fb;font-size:1rem;}
        .soft {padding:.75rem 1rem;border-radius:12px;background:#f7f9fc;border:1px solid #e6ebf1;}
        .pass {color:#157347;font-weight:700;}
        .fail {color:#b42318;font-weight:700;}
        .warn {padding:.55rem .7rem;border-radius:9px;background:#fff7e6;border:1px solid #f4c27a;margin:.25rem 0;}
        .chatq {padding:.75rem 1rem;border-radius:14px;background:#f2f6fb;border:1px solid #dbe5f0;margin:.35rem 0;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero"><h1>🧭 CSEC RM Copilot</h1><p>Capability discovery first. Explainable resource matching underneath. Human decision always stays in control.</p></div>',
        unsafe_allow_html=True,
    )


def serialize_df(df: pd.DataFrame) -> bytes:
    out = df.copy()
    for col in out.columns:
        out[col] = out[col].apply(lambda x: json.dumps(x, default=str) if isinstance(x, (dict, list, set)) else x)
    return out.to_csv(index=False).encode("utf-8")


def request_defaults() -> dict:
    return {
        "request_id": "REQ-2026-001",
        "role_title": "Healthcare Data Analyst",
        "start_date": date(2026, 9, 14),
        "end_date": date(2026, 11, 30),
        "allocation_pct": 50,
        "allowed_locations": ["India"],
        "time_zones": ["Asia/Kolkata"],
        "languages": ["English"],
        "domains": ["Healthcare"],
        "mandatory_skills": {"SQL": 3, "Python": 2, "Healthcare Data": 2},
        "preferred_skills": {"Power BI": 2, "Claims Data": 2},
        "grade_min": "Analyst",
        "grade_max": "Consultant",
        "capacity_strict": True,
        "domain_strict": False,
    }


def display_name(df: pd.DataFrame, rid: str) -> str:
    row = df[df.resource_id.astype(str).eq(str(rid))]
    if row.empty:
        return str(rid)
    name = row.iloc[0].get("resource_name", "Unknown")
    return f"{name}  ·  {rid}"


styled_header()

if "request" not in st.session_state:
    st.session_state.request = request_defaults()
if "results" not in st.session_state:
    st.session_state.results = None
if "decisions" not in st.session_state:
    st.session_state.decisions = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar: data + policy only. Business intake is kept out of the sidebar to make the main experience feel less like a traditional form.
with st.sidebar:
    st.header("Data & policy")
    uploaded = st.file_uploader("Upload workbook", type=["xlsx", "xls"], help="Workbook should contain Resources, Capacity and DeliveryEvidence sheets. The same deterministic engine is used after upload.")
    if uploaded is not None:
        try:
            up_res, up_cap, up_evi = load_workbook(uploaded)
            if up_res is None:
                st.error("No Resources sheet was found. The demo dataset remains active.")
            else:
                resources = canonicalize_resources(up_res)
                capacity = canonicalize_capacity(up_cap)
                evidence = canonicalize_evidence(up_evi)
                st.success("Workbook loaded safely. Optional columns were filled where missing.")
        except Exception:
            st.error("The workbook could not be read. Please use the demo workbook structure or upload a clean XLSX.")
    health = dataset_health(resources, capacity, evidence)
    st.caption(f"{len(resources):,} resources · {len(capacity):,} capacity rows · {len(evidence):,} delivery records")
    if health["resources_errors"]:
        st.error("Resource data: " + " | ".join(health["resources_errors"][:3]))
    if health["capacity_errors"]:
        st.error("Capacity data: " + " | ".join(health["capacity_errors"][:3]))
    if health["evidence_errors"]:
        st.error("Evidence data: " + " | ".join(health["evidence_errors"][:3]))
    with st.expander("Matching policy", expanded=False):
        st.write("Location is a hard gate when selected. Time zone is also a hard gate when selected. A high score never offsets a failed hard gate.")
        capacity_strict = st.checkbox("Require requested allocation every week", value=True)
        domain_strict_default = st.checkbox("Make selected domain a hard gate", value=False)
    with st.expander("Weights", expanded=False):
        weight_labels = {
            "mandatory_skills": "Mandatory skills", "preferred_skills": "Preferred skills", "proficiency": "Proficiency",
            "relevant_evidence": "Relevant evidence", "capacity": "Capacity", "delivery_fit": "Delivery fit",
            "development_alignment": "Development alignment", "data_confidence": "Data confidence",
        }
        entered = {}
        for key, default in DEFAULT_WEIGHTS.items():
            entered[key] = st.number_input(weight_labels[key], 0.0, 100.0, default * 100, 1.0, key="weight_" + key)
        raw_total = sum(entered.values())
        weights = {k: v / raw_total for k, v in entered.items()} if raw_total else DEFAULT_WEIGHTS.copy()
        st.caption(f"Weights normalized to {sum(weights.values()) * 100:.0f}%.")

TABS = st.tabs(["💬 Copilot", "🧩 Structured match", "🎯 Recommendations", "📅 Selected capacity", "🌐 Capability map", "🔎 Audit & data"])

# ---------------- Copilot ----------------
with TABS[0]:
    st.subheader("Ask the capability network")
    st.caption("This POC does not call an LLM yet. It uses the same governed catalogue and deterministic search engine that a future LLM adapter will call.")
    examples = [
        "I have an MMX project, who should I contact?",
        "Who has expertise in price elasticity for Europe?",
        "Find India consultants with SQL and Python",
        "Who are the GenAI and Agentic AI SMEs?",
    ]
    ec = st.columns(len(examples))
    for i, example in enumerate(examples):
        with ec[i]:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.chat_query = example
    query = st.text_input("Ask Copilot", value=st.session_state.get("chat_query", ""), placeholder="Try: Who has expertise in price elasticity for Europe?")
    combine = st.checkbox("Use current structured staffing request as context", value=st.session_state.get("results") is not None)
    if st.button("Search capability network", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Enter a question or choose one of the examples above.")
        else:
            intent, found = discovery_search(resources, evidence, query, limit=12)
            st.session_state.chat_history.append({"query": query, "intent": intent, "rows": found})
            if combine and st.session_state.request and st.session_state.results is not None and intent.intent == "resource_matching":
                # No LLM magic: use the already computed deterministic shortlist and optionally narrow it by discovered terms.
                st.session_state.chat_resource_mode = True
            else:
                st.session_state.chat_resource_mode = False
    for item in reversed(st.session_state.chat_history[-3:]):
        st.markdown(f'<div class="chatq"><b>You:</b> {item["query"]}</div>', unsafe_allow_html=True)
        intent, found = item["intent"], item["rows"]
        if found.empty:
            st.info("I could not find a strong governed match. Try a skill, domain, geography, project name or team that exists in the catalogue.")
            if intent.skills:
                st.warning("Detected skills: " + ", ".join(sorted(intent.skills)))
        else:
            detected = []
            if intent.skills: detected.append("Skills: " + ", ".join(sorted(intent.skills)))
            if intent.locations: detected.append("Geography: " + ", ".join(sorted(intent.locations)))
            if intent.domains: detected.append("Domain: " + ", ".join(sorted(intent.domains)))
            if intent.terms: detected.append("Context: " + ", ".join(sorted(intent.terms)[:8]))
            if detected:
                st.caption(" | ".join(detected))
            st.markdown("### People and teams to contact")
            cols = ["rank", "resource_name", "grade", "team", "location", "time_zone", "score", "key_skills", "geography_expertise", "project_expertise", "contact_email", "manager_name", "manager_email"]
            show = found[[c for c in cols if c in found.columns]].copy()
            show.rename(columns={"resource_name": "Expert / contact", "score": "Relevance", "key_skills": "Relevant skills", "contact_email": "Contact", "manager_name": "Manager", "manager_email": "Manager contact"}, inplace=True)
            st.dataframe(show, use_container_width=True, hide_index=True)

    if st.session_state.get("results") is not None:
        st.markdown("### Bridge to the structured engine")
        st.info("The Copilot and the structured form are intentionally two front doors to the same rule engine. A future LLM can replace only the query interpretation layer, not the eligibility or scoring rules.")
        if st.button("Open current request in Recommendations", use_container_width=True):
            st.session_state.active_tab_hint = "recommendations"

# ---------------- Structured match ----------------
with TABS[1]:
    st.subheader("Structured request", divider="blue")
    st.caption("Use this when you know the delivery constraints. Every controlled attribute comes from the governed catalogue, so malformed skill strings cannot crash the application.")
    current = st.session_state.request or request_defaults()
    with st.form("structured_request"):
        left, middle, right = st.columns(3)
        with left:
            request_id = st.text_input("Request ID", value=current.get("request_id", "REQ-2026-001"))
            role_title = st.text_input("Opportunity / role", value=current.get("role_title", "Healthcare Data Analyst"))
            allocation = st.slider("Required allocation (%)", 5, 100, int(current.get("allocation_pct", 50)), 5)
            start = st.date_input("Start date", value=current.get("start_date", date(2026, 9, 14)))
            end = st.date_input("End date", value=current.get("end_date", date(2026, 11, 30)))
        with middle:
            min_grade = st.selectbox("Minimum grade", GRADE_LEVELS, index=GRADE_LEVELS.index(current.get("grade_min", "Analyst")))
            valid_max = GRADE_LEVELS[GRADE_LEVELS.index(min_grade):]
            default_max = current.get("grade_max", "Consultant") if current.get("grade_max", "Consultant") in valid_max else valid_max[-1]
            max_grade = st.selectbox("Maximum grade", valid_max, index=valid_max.index(default_max))
            locations = st.multiselect("Allowed work locations · STRICT", LOCATIONS, default=[x for x in current.get("allowed_locations", ["India"]) if x in LOCATIONS])
            zones = st.multiselect("Allowed time zones · STRICT", TIME_ZONES, default=[x for x in current.get("time_zones", ["Asia/Kolkata"]) if x in TIME_ZONES])
        with right:
            languages = st.multiselect("Mandatory languages", LANGUAGES, default=[x for x in current.get("languages", ["English"]) if x in LANGUAGES])
            domains = st.multiselect("Relevant domains", DOMAINS, default=[x for x in current.get("domains", ["Healthcare"]) if x in DOMAINS])
            cap_mode = st.checkbox("Hard capacity gate", value=bool(capacity_strict))
            domain_mode = st.checkbox("Hard domain gate", value=bool(domain_strict_default or current.get("domain_strict", False)))

        st.markdown("#### Mandatory capabilities")
        selected_mand = st.multiselect("Mandatory skills", SKILL_CATALOG, default=[x for x in current.get("mandatory_skills", {}) if x in SKILL_CATALOG], help="A candidate must have every selected skill at or above the requested level.")
        mand_levels = {}
        if selected_mand:
            mcols = st.columns(min(4, len(selected_mand)))
            for i, skill in enumerate(selected_mand):
                with mcols[i % len(mcols)]:
                    existing = int(current.get("mandatory_skills", {}).get(skill, 2))
                    level_idx = max(0, min(3, existing - 1))
                    mand_levels[skill] = PROFICIENCY[st.selectbox(skill, PROFICIENCY_LABELS, index=level_idx, key="req_mand_" + skill)]
        st.markdown("#### Nice-to-have capabilities")
        preferred_catalog = [x for x in SKILL_CATALOG if x not in selected_mand]
        selected_pref = st.multiselect("Preferred skills", preferred_catalog, default=[x for x in current.get("preferred_skills", {}) if x in preferred_catalog])
        pref_levels = {}
        if selected_pref:
            pcols = st.columns(min(4, len(selected_pref)))
            for i, skill in enumerate(selected_pref):
                with pcols[i % len(pcols)]:
                    existing = int(current.get("preferred_skills", {}).get(skill, 2))
                    level_idx = max(0, min(3, existing - 1))
                    pref_levels[skill] = PROFICIENCY[st.selectbox(skill + " ", PROFICIENCY_LABELS, index=level_idx, key="req_pref_" + skill)]
        submitted = st.form_submit_button("Run explainable match", type="primary", use_container_width=True)

    if submitted:
        request = {
            "request_id": request_id.strip() or "UNNAMED-REQUEST",
            "role_title": role_title.strip() or "Unspecified opportunity",
            "start_date": start, "end_date": end, "allocation_pct": allocation,
            "allowed_locations": locations, "time_zones": zones, "languages": languages, "domains": domains,
            "mandatory_skills": mand_levels, "preferred_skills": pref_levels,
            "grade_min": min_grade, "grade_max": max_grade,
            "capacity_strict": cap_mode, "domain_strict": domain_mode,
        }
        report = validate_request(request)
        if not report.ok:
            st.error("The request was not accepted. No matching run was attempted.")
            for error in report.errors:
                st.error(error)
        else:
            st.session_state.request = request
            try:
                match = run_matching(resources, capacity, evidence, request, weights)
                st.session_state.results = match
                st.success(f"Match complete: {match.diagnostics['eligible']:,} eligible of {match.diagnostics['resources_assessed']:,} assessed.")
                for warning in report.warnings:
                    st.warning(warning)
            except Exception:
                # Never expose a scary stack trace in the app. Technical detail belongs in local logs in production.
                st.session_state.results = None
                st.error("The dataset could not be evaluated safely. Check Audit & data for validation issues, then retry.")

# ---------------- Recommendations ----------------
with TABS[2]:
    st.subheader("Recommendations")
    match = st.session_state.results
    if match is None:
        st.info("Run the structured match first, or start with a Copilot discovery question.")
    elif match.table.empty:
        st.error("There are no resources in the current dataset.")
    else:
        table = match.table
        diagnostics = match.diagnostics
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Resources assessed", diagnostics.get("resources_assessed", 0))
        k2.metric("Feasible", diagnostics.get("eligible", 0))
        k3.metric("Excluded", diagnostics.get("excluded", 0))
        k4.metric("Request weeks", diagnostics.get("request_window_weeks", 0))

        if diagnostics.get("zero_match"):
            st.error("No candidate satisfies every selected mandatory condition. Hard location, time-zone, language, grade, skill and capacity rules are not relaxed automatically.")
            counts = diagnostics.get("gate_exclusion_counts", {})
            labels = ["Location", "Time zone", "Language", "Domain", "Grade", "Mandatory skill", "Mandatory proficiency", "Capacity data", "Capacity"]
            keys = ["location", "time_zone", "language", "domain", "grade", "mandatory_skill", "mandatory_proficiency", "capacity_data", "capacity"]
            diag = pd.DataFrame({"Constraint": labels, "Candidates failing": [counts.get(k, 0) for k in keys]})
            st.plotly_chart(px.bar(diag, x="Constraint", y="Candidates failing", text_auto=True), use_container_width=True)
            st.caption("These counts are diagnostic only. The manager must explicitly change a constraint if business context permits it.")
        else:
            eligible = table[table.status.eq("Eligible")].copy()
            st.markdown("### Feasible shortlist")
            shortlist_cols = ["rank", "resource_name", "grade", "team", "location", "time_zone", "total_score", "fit_percentile", "minimum_available_pct", "weeks_below_demand", "tentative_risk_weeks", "confidence_label"]
            if "confidence_label" not in eligible.columns:
                eligible["confidence_label"] = eligible.profile_confidence.map(lambda x: "High" if x >= .9 else "Medium" if x >= .8 else "Verify")
            shortlist = eligible[[c for c in shortlist_cols if c in eligible.columns]].copy()
            st.dataframe(shortlist, use_container_width=True, hide_index=True, column_config={
                "total_score": st.column_config.ProgressColumn("Fit score", min_value=0, max_value=100, format="%.1f"),
                "fit_percentile": st.column_config.NumberColumn("Fit percentile", format="%.1f"),
                "minimum_available_pct": st.column_config.ProgressColumn("Minimum weekly availability", min_value=0, max_value=100, format="%.0f%%"),
            })

            chosen = st.selectbox("Investigate candidate", eligible.resource_id.astype(str).tolist(), format_func=lambda rid: display_name(eligible, rid))
            row = eligible[eligible.resource_id.astype(str).eq(str(chosen))].iloc[0]
            req = st.session_state.request
            detail_left, detail_right = st.columns([1.15, 1])
            with detail_left:
                st.markdown(f"## {row.resource_name}")
                st.caption(f"{row.grade} · {row.team} · {row.location} · {row.time_zone}")
                st.success(f"Top-line recommendation: **{row["total_score"]:.1f}/100** · **{row["fit_percentile"]:.0f}th percentile** among feasible candidates.")
                st.markdown("### Why this person is a fit")
                reasons = []
                if row.score_components.get("mandatory_skills", 0) >= weights["mandatory_skills"] * 90:
                    reasons.append("Meets the mandatory capability set at or above the requested proficiency.")
                if row.score_components.get("relevant_evidence", 0) >= weights["relevant_evidence"] * 75:
                    reasons.append("Has relevant delivery evidence and project context.")
                if row.minimum_available_pct >= req["allocation_pct"]:
                    reasons.append(f"Maintains at least {row.minimum_available_pct:.0f}% confirmed availability across the request window.")
                if row.geography_expertise:
                    reasons.append(f"Geographic expertise: {row.geography_expertise.replace('|', ', ')}")
                if not reasons:
                    reasons.append("Fits the hard gates and is ranked by the visible evidence-based score.")
                for item in reasons:
                    st.markdown("✓ " + item)

                st.markdown("### Mandatory gates")
                for gate, ok in row.gates.items():
                    if ok:
                        st.markdown(f"<span class='pass'>✓ {gate}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='fail'>✕ {gate}</span>", unsafe_allow_html=True)

                st.markdown("### Skill comparison")
                combined = {**req.get("mandatory_skills", {}), **req.get("preferred_skills", {})}
                skill_rows = []
                resource_row = resources[resources.resource_id.astype(str).eq(str(chosen))].iloc[0]
                person_skills = parse_skill_string(resource_row.get("skills"))
                for skill, level in combined.items():
                    actual = person_skills.get(skill, 0)
                    skill_rows.append({
                        "Skill": skill, "Requirement": PROFICIENCY_LABELS[level - 1],
                        "Candidate": PROFICIENCY_LABELS[actual - 1] if actual in PROFICIENCY.values() else "Not listed",
                        "Gap": "None" if actual >= level else f"Needs {PROFICIENCY_LABELS[level - 1]}",
                    })
                st.dataframe(pd.DataFrame(skill_rows), use_container_width=True, hide_index=True)

                if row.evidence_summary:
                    st.markdown("### Relevant delivery evidence")
                    for item in row.evidence_summary:
                        st.markdown("• " + item)
                if row.risks:
                    st.markdown("### Verify before confirming")
                    for risk in row.risks:
                        st.markdown(f'<div class="warn">⚠ {risk}</div>', unsafe_allow_html=True)

                st.markdown("### Contact path")
                c1, c2 = st.columns(2)
                c1.markdown(f"**Resource:** {row.contact_email or 'Not provided'}")
                c2.markdown(f"**Manager:** {row.manager_name}<br>{row.manager_email or 'Not provided'}", unsafe_allow_html=True)

            with detail_right:
                st.markdown("### Score contribution")
                comp = row.score_components
                chart_df = pd.DataFrame({"Component": [k.replace("_", " ").title() for k in comp], "Points": [round(v, 2) for v in comp.values()]})
                fig = px.bar(chart_df, x="Points", y="Component", orientation="h", text_auto=".1f")
                fig.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)
                st.caption("These are actual weighted points out of 100. Hard-gate eligibility is decided before scoring.")

                st.markdown("### Capacity summary")
                st.metric("Minimum available", f"{row["minimum_available_pct"]:.0f}%")
                st.metric("Weeks below demand", f"{int(row["weeks_below_demand"])}")
                st.metric("Tentative-risk weeks", f"{int(row["tentative_risk_weeks"])}")
                st.metric("Data confidence", f"{row.profile_confidence * 100:.0f}%")

            st.markdown("### Genuine alternatives")
            alternatives = build_alternatives(table, str(chosen), limit=3)
            if alternatives:
                alt_df = pd.DataFrame(alternatives)
                alt_df["total_score"] = alt_df.total_score.round(1)
                st.dataframe(alt_df.rename(columns={"resource_name": "Candidate", "team": "Team", "grade": "Grade", "location": "Location", "total_score": "Fit score", "fit_percentile": "Percentile", "minimum_available_pct": "Min availability", "tentative_risk_weeks": "Tentative-risk weeks"}), use_container_width=True, hide_index=True)
            else:
                st.info("No additional feasible backup is available under the same hard constraints.")

            st.markdown("### Human review")
            dc1, dc2 = st.columns(2)
            with dc1:
                decision = st.selectbox("Decision", ["Not reviewed", "Shortlist", "Hold", "Reject", "Override recommendation"], key="review_decision")
            with dc2:
                reason = st.selectbox("Reason", ["Select reason", "Strong overall fit", "Capacity concern", "Skill gap", "Location/time-zone", "Profile verification", "Business context not captured"], key="review_reason")
            note = st.text_area("Reviewer note", key="review_note")
            if st.button("Record decision", type="secondary"):
                st.session_state.decisions.append({"request_id": req["request_id"], "resource_id": row.resource_id, "resource_name": row.resource_name, "system_score": row.total_score, "decision": decision, "reason": reason, "note": note})
                st.success("Decision recorded in this browser session.")

            st.download_button("Download recommendation audit CSV", serialize_df(table), "rm_recommendation_audit.csv", "text/csv")

# ---------------- Selected capacity ----------------
with TABS[3]:
    st.subheader("Selected-resource capacity")
    match = st.session_state.results
    req = st.session_state.request
    if match is None or req is None:
        st.info("Run a structured match first.")
    else:
        eligible = match.table[match.table.status.eq("Eligible")]
        if eligible.empty:
            st.info("No selected resource exists because no one passed every mandatory gate.")
        else:
            rid = st.selectbox("Resource", eligible.resource_id.astype(str).tolist(), format_func=lambda x: display_name(eligible, x), key="capacity_person")
            cap = candidate_capacity(capacity, rid, req["start_date"], req["end_date"], req["allocation_pct"])
            person = resources[resources.resource_id.astype(str).eq(str(rid))].iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Demand", f"{req['allocation_pct']}%")
            c2.metric("Minimum confirmed headroom", f"{cap.available_pct.min():.0f}%")
            c3.metric("Weeks below demand", int((cap.available_pct < req["allocation_pct"]).sum()))
            c4.metric("Tentative-risk weeks", int((cap.net_available_after_tentative_pct < req["allocation_pct"]).sum()))
            plot_cols = ["available_pct", "required_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct"]
            cap_plot = cap[["week_start"] + plot_cols].melt(id_vars="week_start", var_name="Series", value_name="Percent")
            cap_plot["Series"] = cap_plot["Series"].replace({"available_pct": "Available", "required_pct": "Requested", "confirmed_allocation_pct": "Confirmed allocation", "tentative_allocation_pct": "Tentative allocation", "leave_pct": "Leave"})
            fig = px.line(cap_plot, x="week_start", y="Percent", color="Series", markers=True)
            fig.update_yaxes(range=[0, 100])
            fig.update_layout(height=430, margin=dict(l=0, r=0, t=15, b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(cap[["week_start", "working_capacity_pct", "confirmed_allocation_pct", "tentative_allocation_pct", "leave_pct", "available_pct", "required_pct", "gap_pct", "tentative_gap_pct", "status"]], use_container_width=True, hide_index=True)
            st.caption(f"This view is intentionally specific to {person.resource_name}. It evaluates the complete request horizon at weekly grain rather than hiding a bad week inside an average.")

# ---------------- Capability map ----------------
with TABS[4]:
    st.subheader("Capability & cross-team intelligence")
    st.caption("This view is for finding capability pools and SMEs, not merely drawing an average utilization line.")
    q1, q2 = st.columns(2)
    with q1:
        skill_focus = st.selectbox("Find supply for a skill", ["All skills"] + SKILL_CATALOG, key="portfolio_skill")
    with q2:
        geo_focus = st.selectbox("Geography focus", ["All locations"] + LOCATIONS + ["Europe", "APAC", "North America"], key="portfolio_geo")

    portfolio = resources.copy()
    if skill_focus != "All skills":
        portfolio = portfolio[portfolio.skills.fillna("").map(lambda x: skill_focus in parse_skill_string(x))]
    if geo_focus != "All locations":
        portfolio = portfolio[portfolio.geography_expertise.fillna("").map(lambda x: geo_focus in split_pipe(x)) | portfolio.location.eq(geo_focus)]
    if portfolio.empty:
        st.info("No people match this capability/geography slice. No error is raised and no weak substitute is invented.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("People in pool", len(portfolio))
        m2.metric("Teams", int(portfolio.team.nunique()))
        m3.metric("Locations", int(portfolio.location.nunique()))
        m4.metric("Senior / SME pool", int(portfolio.grade.isin(["Engagement Manager", "Principal", "Senior Principal"]).sum()))
        st.dataframe(portfolio[["resource_name", "role_title", "grade", "team", "location", "time_zone", "domains", "skills", "geography_expertise", "project_expertise", "contact_email", "manager_name"]].head(100), use_container_width=True, hide_index=True)

    st.markdown("### Supply by skill")
    supply_rows = []
    for skill in SKILL_CATALOG:
        count = int(resources.skills.fillna("").map(lambda x: skill in parse_skill_string(x)).sum())
        if count:
            supply_rows.append({"Skill": skill, "People": count})
    supply = pd.DataFrame(supply_rows).sort_values("People", ascending=False).head(20)
    st.plotly_chart(px.bar(supply, x="People", y="Skill", orientation="h"), use_container_width=True)

    if st.session_state.results is not None:
        eligible = st.session_state.results.table[st.session_state.results.table.status.eq("Eligible")]
        if not eligible.empty:
            st.markdown("### Feasible capacity by team")
            team = eligible.groupby("team", as_index=False).agg(
                Feasible=("resource_id", "count"), MedianScore=("total_score", "median"),
                BestScore=("total_score", "max"), MinWeeklyAvailability=("minimum_available_pct", "min"),
            ).sort_values("Feasible", ascending=False)
            st.dataframe(team, use_container_width=True, hide_index=True)

# ---------------- Audit & data ----------------
with TABS[5]:
    st.subheader("Audit, data quality & architecture")
    health = dataset_health(resources, capacity, evidence)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Resource rows", health["resource_count"])
    a2.metric("Capacity rows", health["capacity_rows"])
    a3.metric("Delivery records", health["evidence_rows"])
    a4.metric("Skill catalogue", len(SKILL_CATALOG))

    for title, key in [("Resources", "resources"), ("Capacity", "capacity"), ("Evidence", "evidence")]:
        errs = health[key + "_errors"]
        warns = health[key + "_warnings"]
        with st.expander(f"{title} validation", expanded=bool(errs)):
            if errs:
                for e in errs:
                    st.error(e)
            else:
                st.success(f"{title} schema checks passed.")
            for w in warns[:12]:
                st.warning(w)

    if st.session_state.results is not None:
        st.markdown("### Current request rule snapshot")
        st.json({
            "request": st.session_state.request,
            "weights": weights,
            "rule_version": RULE_VERSION,
            "taxonomy_version": TAXONOMY_VERSION,
            "data_version": DATA_VERSION,
        })
    if st.session_state.decisions:
        st.download_button("Download reviewer decisions", pd.DataFrame(st.session_state.decisions).to_csv(index=False).encode("utf-8"), "rm_reviewer_decisions.csv", "text/csv")

    st.markdown("### Future LLM integration contract")
    st.code(json.dumps(mock_llm_adapter_spec(), indent=2), language="json")
    st.caption("The future LLM should interpret language only. It should produce a structured intent, after which the deterministic validation, eligibility and scoring engine remains authoritative.")

    st.markdown("### Product guardrails")
    st.markdown("""
    **Hard delivery constraints:** location and explicitly selected time zone are strict eligibility gates. A candidate cannot score their way around them.

    **Grade hierarchy:** Analyst → Associate Consultant → Consultant → Senior Consultant → Engagement Manager → Principal → Senior Principal. The UI prevents an invalid minimum/maximum range.

    **Explainability:** the shortlist shows gates, percentiles, score contributions, evidence, capacity risk, confidence and contact paths.

    **Human control:** the system recommends and explains. It never autonomously assigns a person.

    **No protected-attribute scoring:** protected or sensitive personal attributes are not used in matching.
    """)
