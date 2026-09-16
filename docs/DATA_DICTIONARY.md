# CSEC RM Copilot — Data Dictionary

## 1. Purpose of this document

This document explains every important field used by the application:

- what the field means;
- its expected format;
- an example;
- whether it is required;
- how it is validated;
- how the application uses it.

The POC uses three source datasets:

1. Resources — one row per person.
2. Capacity — one row per person per week.
3. Delivery evidence — one row per historical project experience.

All three are connected by `resource_id`.

### Important meaning of “required”

This document uses “required” to mean required by the canonical validation schema. The current upload flow canonicalizes data before validation, and canonicalization creates defaults for some absent columns. Therefore, an uploaded source workbook may technically pass after fields have been defaulted.

This is convenient for a POC but is not sufficient production governance. A production pipeline should:

- validate raw source columns first;
- record which values were supplied versus defaulted;
- never convert an unknown capacity value into a genuine zero;
- reject missing fields that are operationally essential.

## 2. General formatting rules

### IDs

IDs are treated as text. Whitespace is removed at the beginning and end. They must be non-empty and unique in Resources.

### Dates

Dates should use ISO format:

`YYYY-MM-DD`

Example: `2026-09-14`

### Percentages

Percentages are stored as numbers from 0 to 100, not decimals.

- Correct: `50`
- Incorrect for this schema: `0.50`

### Multi-value text

Multiple values are separated with a vertical pipe:

`English|Hindi`

Semicolons are also accepted by parsing helpers, but pipe is the preferred governed format.

### Skills with proficiency

Each skill is stored as:

`Skill name:Level`

Multiple skills use pipes:

`SQL:4|Python:3|Power BI:2`

Allowed levels are:

- 1 — Awareness
- 2 — Working
- 3 — Proficient
- 4 — Expert

Unknown skills, malformed values and unsupported levels are ignored by the parser. Data validation warns when a non-empty skill field produces no valid governed skills.

## 3. Resources dataset

### File and workbook names

- Demo file: `data/resources.csv`
- Preferred workbook sheet: `Resources`
- Accepted alternatives: `Resource`, `Employees`, `Employee`

### Grain

One row represents one resource/person.

### Current POC size

320 rows.

## 3.1 `resource_id`

- Meaning: Stable unique identifier for the person.
- Type: Text.
- Example: `EMP-1001`
- Required: Yes.
- Validation: Must be non-empty and unique.
- Used for: Joining Resources to Capacity and Delivery Evidence; identifying recommendations and decisions.
- Production guidance: Use a governed employee/resource key, not a mutable email address.

## 3.2 `resource_name`

- Meaning: Display name.
- Type: Text.
- Example: `Aarav Sharma`
- Required: Yes.
- Validation: Must be non-empty.
- Used for: UI display, exports and reviewer decisions.
- Scoring: Not used.

## 3.3 `team`

- Meaning: Organizational or capability team.
- Type: Text.
- Example: `CSEC Analytics India`
- Required: Yes in the canonical resource schema.
- Used for: Results display, capability map and cross-team capacity summary.
- Scoring: Not directly scored.
- Production guidance: Use a stable team ID as well as a display name.

## 3.4 `grade`

- Meaning: Governed seniority level.
- Type: Controlled text.
- Example: `Consultant`
- Required: Yes.
- Allowed values, in order:
  - Analyst
  - Associate Consultant
  - Consultant
  - Senior Consultant
  - Engagement Manager
  - Principal
  - Senior Principal
- Validation: Unknown values are blocking errors.
- Used for: Hard minimum/maximum grade gate and display.

## 3.5 `role_title`

- Meaning: Current role/title.
- Type: Text.
- Example: `Consultant`
- Required: Optional; canonicalization adds a blank value when missing.
- Used for: Display, discovery search and delivery context.
- Structured scoring: Not currently scored against the request role title.

## 3.6 `location`

- Meaning: Primary work location.
- Type: Controlled text.
- Example: `India`
- Required: Yes.
- Allowed POC values:
  - India
  - UK
  - France
  - Germany
  - Spain
  - USA
  - Canada
  - Singapore
  - Japan
  - Australia
  - Philippines
- Validation: Unknown values create a warning.
- Used for: Strict location gate when the request selects locations; capability filtering; display.
- Production caution: Location must not be treated as proof of nationality or work authorization.

## 3.7 `time_zone`

- Meaning: Primary working time zone in IANA format.
- Type: Controlled text.
- Example: `Asia/Kolkata`
- Required: Yes.
- Allowed POC values:
  - Asia/Kolkata
  - Europe/London
  - Europe/Paris
  - Europe/Berlin
  - America/New_York
  - America/Chicago
  - America/Los_Angeles
  - America/Toronto
  - Asia/Singapore
  - Asia/Manila
  - Asia/Tokyo
  - Australia/Sydney
- Validation: Unknown values create a warning.
- Used for: Strict time-zone gate when selected; display and discovery.
- Limitation: The POC checks exact time-zone identity, not overlapping working hours.

## 3.8 `languages`

- Meaning: Languages the person can use for delivery.
- Type: Pipe-delimited controlled text.
- Example: `English|Hindi`
- Required: Yes.
- Used for: The person must contain every mandatory request language.
- Validation: Request languages are governed; profile language values are not fully validated against the catalogue in the current POC.
- Production guidance: Add language proficiency levels if client-facing fluency matters.

## 3.9 `skills`

- Meaning: Governed skills and proficiency levels.
- Type: Pipe-delimited `Skill:Level` pairs.
- Example: `Claims Data:3|Healthcare Data:3|Power BI:4|Python:3|SQL:4`
- Required: Yes.
- Validation:
  - skill must exist in `SKILL_CATALOG` or resolve through an alias;
  - level must be 1, 2, 3 or 4;
  - malformed tokens are ignored safely;
  - a warning is issued when non-empty input has no valid entries.
- Used for:
  - mandatory skill presence gate;
  - mandatory proficiency gate;
  - preferred skill score;
  - proficiency-depth score;
  - capability map;
  - natural-language discovery.
- Production guidance: Store skills in a normalized child table rather than a single string.

## 3.10 `domains`

- Meaning: Business or delivery contexts in which the person has experience.
- Type: Pipe-delimited controlled text.
- Example: `Healthcare|Patient Services|Real World Evidence`
- Required: Yes.
- Used for:
  - optional hard domain gate;
  - domain-fit score;
  - discovery and capability filtering.
- Production guidance: Define whether domain means training, project exposure or verified expertise.

## 3.11 `development_interests`

- Meaning: Skills or capability areas the person wants to develop/use.
- Type: Pipe-delimited governed skills.
- Example: `Agentic AI|GenAI`
- Required: Yes in the canonical schema, but it may be blank.
- Used for: Low-weight development-alignment score against preferred skills.
- Guardrail: Development interest must never substitute for mandatory delivery readiness.

## 3.12 `years_experience`

- Meaning: Total relevant professional experience in years.
- Type: Number; decimals allowed.
- Example: `6.2`
- Required: Yes.
- Validation: Expected range 0–60. Missing/non-numeric values warn; out-of-range values block.
- Used for: 10% of the internal relevant-evidence component, capped at 10 years.
- Caution: This can correlate with age and should be reviewed for fairness. Grade and verified experience may be safer business indicators.

## 3.13 `delivery_rating`

- Meaning: Historical delivery-quality rating.
- Type: Number from 0 to 5.
- Example: `4.7`
- Required: Yes.
- Validation: Missing/non-numeric values warn; outside 0–5 blocks.
- Used for: 10% of the internal relevant-evidence component.
- Production guidance: Define source, reviewer, period and calibration. Uncontrolled ratings can create bias.

## 3.14 `profile_confidence`

- Meaning: Trust level for profile completeness/currentness.
- Type: Decimal from 0 to 1.
- Example: `0.97`
- Required: Yes.
- Validation: Missing/non-numeric values warn; outside 0–1 blocks.
- Used for:
  - 3% total scoring weight;
  - confidence label;
  - risk flag below 0.80;
  - ranking tie-break.
- Labels:
  - High: 0.90–1.00
  - Medium: 0.80–0.89
  - Verify: below 0.80
- Important: This is data confidence, not predicted employee performance.

## 3.15 `profile_updated`

- Meaning: Date of latest profile update.
- Type: Date.
- Example: `2026-08-16`
- Required: Yes.
- Canonicalization: Converted to a date/time value; invalid input becomes missing.
- Current use: Data display/source context only.
- Limitation: The engine does not currently reduce confidence automatically for stale profiles.

## 3.16 `contact_email`

- Meaning: Resource contact address.
- Type: Text/email.
- Example: `aarav.sharma@csec-demo.example`
- Required: Optional.
- Used for: Contact path in discovery and recommendations.
- Scoring: Not used.
- Production guidance: Protect as personal data and apply access control.

## 3.17 `manager_name`

- Meaning: Resource manager.
- Type: Text.
- Example: `Anika Kapoor`
- Required: Optional; defaults to `Not provided`.
- Used for: Contact/escalation path.
- Scoring: Not used.

## 3.18 `manager_email`

- Meaning: Manager contact address.
- Type: Text/email.
- Example: `anika.kapoor@csec-demo.example`
- Required: Optional.
- Used for: Contact/escalation path.
- Scoring: Not used.

## 3.19 `geography_expertise`

- Meaning: Broader geographies where the person has delivery knowledge.
- Type: Pipe-delimited text.
- Example: `Europe|India`
- Required: Optional.
- Used for: Discovery and capability-map geography filtering.
- Strict matching: Does not satisfy the strict profile-location gate.

## 3.20 `country_expertise`

- Meaning: Countries where the person has market or delivery experience.
- Type: Pipe-delimited text.
- Example: `Germany|India|UK`
- Required: Optional.
- Used for: Natural-language discovery.
- Strict matching: Does not satisfy the strict profile-location gate.

## 3.21 `project_expertise`

- Meaning: Named project methods or experience themes.
- Type: Pipe-delimited text.
- Example: `Claims Analytics|Healthcare Analytics|RWE`
- Required: Optional.
- Used for: Natural-language discovery and display.
- Structured scoring: Historical Delivery Evidence provides the more formal evidence input.

## 3.22 `capability_tags`

- Meaning: Search labels assigned to the profile.
- Type: Pipe-delimited text.
- Example: `Cross-team analytics|Healthcare SME`
- Required: Optional.
- Used for: Natural-language discovery.
- Caution: An `SME` tag should be governed and approved, not self-declared without criteria.

## 3.23 `expertise_summary`

- Meaning: Human-readable summary of the profile.
- Type: Text.
- Example: `Consultant in CSEC Analytics India with 6.2 years' experience...`
- Required: Optional.
- Used for: Discovery search and display.
- Structured scoring: Not directly scored.

## 4. Capacity dataset

### File and workbook names

- Demo file: `data/capacity.csv`
- Preferred workbook sheet: `Capacity`
- Accepted alternatives: `Weekly Capacity`, `WeeklyCapacity`

### Grain

One row represents one resource for one week.

### Current POC size

9,600 rows: 320 resources × 30 weeks.

Canonicalization creates missing percentage columns with `0.0`. This means a malformed upload could interpret an absent allocation/leave column as zero. Raw-schema validation should happen before defaulting in production.

## 4.1 `resource_id`

- Meaning: Resource foreign key.
- Type: Text.
- Example: `EMP-1001`
- Required: Yes.
- Validation: Must exist in Resources.
- Used for: Joining weekly capacity to the person.

## 4.2 `week_start`

- Meaning: Start date of the capacity week.
- Type: Date.
- Example: `2026-09-14`
- Required: Yes.
- Validation:
  - must parse as a valid date;
  - duplicate `resource_id + week_start` rows are blocked;
  - non-Monday dates create a warning.
- Used for: Reindexing every person to the complete Monday-based request horizon.

## 4.3 `working_capacity_pct`

- Meaning: Maximum workable capacity for the week after employment pattern, part-time schedule or similar base adjustment.
- Type: Percentage 0–100.
- Example: `100`; a part-time week may be `80`.
- Required: Yes.
- Validation: Numeric and within 0–100.
- Used for: Availability calculation.

## 4.4 `confirmed_allocation_pct`

- Meaning: Capacity already committed to confirmed work.
- Type: Percentage 0–100.
- Example: `33`
- Required: Yes.
- Validation:
  - numeric and within 0–100;
  - confirmed allocation plus leave cannot exceed working capacity.
- Used for: Confirmed availability and hard-capacity gate.

## 4.5 `tentative_allocation_pct`

- Meaning: Potential work that is not yet confirmed.
- Type: Percentage 0–100.
- Example: `8`
- Required: Yes.
- Validation:
  - numeric and within 0–100;
  - total tentative overbooking creates a warning.
- Used for: Tentative-risk weeks.
- Current policy: Tentative allocation does not reduce hard-gate availability.

## 4.6 `leave_pct`

- Meaning: Known absence during the week.
- Type: Percentage 0–100.
- Example: `10`
- Required: Yes.
- Validation:
  - numeric and within 0–100;
  - confirmed allocation plus leave cannot exceed working capacity.
- Used for: Confirmed availability.

## 4.7 Derived capacity fields

These fields are calculated by the engine and do not need to exist in the source file.

### `data_missing`

True when working capacity, confirmed allocation or leave is absent for a requested week.

### `available_pct`

`working_capacity_pct − confirmed_allocation_pct − leave_pct`

Clipped to 0–100.

### `net_available_after_tentative_pct`

`available_pct − tentative_allocation_pct`

Clipped to 0–100.

### `required_pct`

The allocation requested by the staffing request.

### `gap_pct`

`maximum(required_pct − available_pct, 0)`

### `tentative_gap_pct`

`maximum(required_pct − net_available_after_tentative_pct, 0)`

### `status`

- Missing capacity data
- Covered
- Below demand

## 4.8 Capacity summary measures

### `min_available_pct`

Lowest confirmed availability across requested weeks.

### `median_available_pct`

Middle confirmed availability across requested weeks.

### `p10_available_pct`

Tenth-percentile availability. This represents a conservative lower-end availability level and is used to reward resilient headroom.

### `weeks_below_demand`

Count of requested weeks where comparable availability is lower than requested allocation.

### `max_gap_pct`

Largest capacity shortfall.

### `tentative_risk_weeks`

Count of weeks where capacity would be insufficient after tentative work.

### `coverage_ratio`

Share of requested weeks meeting demand, from 0 to 1.

### `missing_weeks`

Count of requested weeks with incomplete source capacity.

## 5. Delivery Evidence dataset

### File and workbook names

- Demo file: `data/delivery_evidence.csv`
- Preferred workbook sheet: `DeliveryEvidence`
- Accepted alternatives: `Evidence`, `Project History`, `ProjectHistory`

### Grain

One row represents one historical project experience for one resource.

### Current POC size

1,321 rows.

When the sheet is absent, the POC creates an empty evidence dataset with the canonical columns. This is allowed with a warning; candidates then receive zero relevant-evidence score. When individual evidence fields are missing, canonicalization may fill blank or zero defaults before validation.

## 5.1 `resource_id`

- Meaning: Resource foreign key.
- Type: Text.
- Example: `EMP-1001`
- Required: Yes.
- Validation: Must exist in Resources.
- Used for: Joining evidence to the person.

## 5.2 `project_name`

- Meaning: Historical engagement/project title.
- Type: Text.
- Example: `Claims reporting transformation`
- Required: Yes.
- Used for: Explanation, discovery and evidence summary.

## 5.3 `project_type`

- Meaning: Broad delivery type.
- Type: Text.
- Example: `Analytics / Consulting`
- Required: Yes.
- Used for: Discovery and context.
- Current structured scoring: Not independently weighted.

## 5.4 `domain`

- Meaning: Domain of the historical project.
- Type: Text, preferably governed.
- Example: `Healthcare`
- Required: Yes.
- Used for: Evidence relevance against requested domains.

## 5.5 `role`

- Meaning: Role performed on the project.
- Type: Text.
- Example: `Consultant`
- Required: Yes.
- Used for: Evidence explanation and discovery.
- Current structured scoring: Not compared directly to requested role.

## 5.6 `skills_used`

- Meaning: Skills demonstrably used on the historical project.
- Type: Pipe-delimited skill names without levels.
- Example: `SQL|Claims Data|Healthcare Data|RAG`
- Required: Yes.
- Used for: Evidence skill-overlap calculation and discovery.

## 5.7 `duration_months`

- Meaning: Project duration in months.
- Type: Non-negative number.
- Example: `4`
- Required: Yes.
- Validation: Must be numeric and non-negative.
- Used for: Evidence summary.
- Current scoring: Duration is not directly weighted.

## 5.8 `project_end`

- Meaning: Date the project ended.
- Type: Date.
- Example: `2024-07-31`
- Required: Yes.
- Used for: Recency score and sorting the displayed evidence.
- Recency policy: Value declines linearly over five years relative to the request start date.

## 5.9 `outcome_score`

- Meaning: Historical project outcome/quality score.
- Type: Number from 0 to 5.
- Example: `4.5`
- Required: Yes.
- Validation: Must be numeric and within 0–5.
- Used for: Evidence quality and explanation.
- Production guidance: Define an auditable source and calibration method.

## 6. Structured staffing request

This is created by the UI and passed to `run_matching`.

## 6.1 `request_id`

- Meaning: Business/audit identifier.
- Type: Text.
- Example: `REQ-2026-001`
- Required by UI: Yes; blank becomes `UNNAMED-REQUEST`.
- Current scoring: Not used.

## 6.2 `role_title`

- Meaning: Requested opportunity or role.
- Type: Text.
- Example: `Healthcare Data Analyst`
- Required by UI: Yes; blank becomes `Unspecified opportunity`.
- Current scoring: Not used.
- Future use: An LLM may translate the description into governed skills/domains.

## 6.3 `start_date`

- Meaning: Start of demand.
- Type: Date.
- Required: Yes.
- Validation: Valid date; cannot be after end date.

## 6.4 `end_date`

- Meaning: End of demand.
- Type: Date.
- Required: Yes.
- Validation: Valid date; not before start; request cannot exceed two years.

## 6.5 `allocation_pct`

- Meaning: Weekly percentage required.
- Type: Number.
- Example: `50`
- Required: Yes.
- Validation: 1–100.

## 6.6 `allowed_locations`

- Meaning: Acceptable profile work locations.
- Type: List of governed locations.
- Example: `["India"]`
- Empty meaning: No location restriction.
- Rule: Hard gate when non-empty.

## 6.7 `time_zones`

- Meaning: Acceptable profile time zones.
- Type: List of governed time zones.
- Example: `["Asia/Kolkata"]`
- Empty meaning: No time-zone restriction.
- Rule: Hard gate when non-empty.

## 6.8 `languages`

- Meaning: Languages mandatory for the work.
- Type: List of governed languages.
- Example: `["English"]`
- Empty meaning: No language restriction.
- Rule: Candidate must contain every selected language.

## 6.9 `domains`

- Meaning: Relevant business/delivery domains.
- Type: List of governed domains.
- Example: `["Healthcare"]`
- Rule:
  - soft score when `domain_strict` is false;
  - hard intersection gate when `domain_strict` is true.

## 6.10 `mandatory_skills`

- Meaning: Required skill-to-minimum-level mapping.
- Type: Dictionary.
- Example: `{"SQL": 3, "Python": 2, "Healthcare Data": 2}`
- Rule: Every skill and minimum level must be met.

## 6.11 `preferred_skills`

- Meaning: Nice-to-have skill-to-level mapping.
- Type: Dictionary.
- Example: `{"Power BI": 2, "Claims Data": 2}`
- Rule: Influences ranking; does not independently exclude.

## 6.12 `grade_min`

- Meaning: Lowest acceptable grade.
- Type: Governed grade.
- Example: `Analyst`
- Rule: Hard lower-bound gate.

## 6.13 `grade_max`

- Meaning: Highest acceptable grade.
- Type: Governed grade.
- Example: `Consultant`
- Rule: Hard upper-bound gate.

## 6.14 `capacity_strict`

- Meaning: Whether confirmed weekly capacity is non-negotiable.
- Type: Boolean.
- Example: `true`
- Rule:
  - true: any week below demand excludes;
  - false: shortfalls are risks, not exclusions.

## 6.15 `domain_strict`

- Meaning: Whether domain experience is non-negotiable.
- Type: Boolean.
- Example: `false`
- Rule:
  - true: at least one domain must match;
  - false: domain contributes only to ranking.

## 7. Matching result fields

The engine produces one result row per assessed resource.

## 7.1 Identity and context

### `resource_id`

Resource identifier.

### `resource_name`

Display name.

### `team`

Team.

### `grade`

Grade.

### `role_title`

Current role.

### `location`

Profile work location.

### `time_zone`

Profile time zone.

### `languages`

Profile languages.

## 7.2 Eligibility and explanation

### `status`

`Eligible` or `Excluded`.

### `exclusion_reasons`

List of plain-language failures.

### `gates`

Dictionary of each gate and its Boolean result.

### `missing_mandatory_skills`

Required skills absent from the profile.

### `below_mandatory_skills`

Present mandatory skills below the requested level.

### `missing_preferred_skills`

Preferred skills absent from the profile.

## 7.3 Ranking and score

### `total_score`

Weighted fit score for eligible candidates. Excluded candidates receive zero.

### `potential_score`

Underlying weighted score retained for excluded-candidate audit and near-match ordering.

### `score_components`

Dictionary of weighted points:

- mandatory_skills;
- preferred_skills;
- proficiency;
- relevant_evidence;
- capacity;
- delivery_fit;
- development_alignment;
- data_confidence.

### `rank`

Sequential rank among eligible candidates, starting at 1. Excluded candidates receive 0.

### `fit_percentile`

Relative total-score percentile among eligible candidates in the current request.

## 7.4 Capacity result

### `minimum_available_pct`

Minimum confirmed weekly availability.

### `median_available_pct`

Median confirmed weekly availability.

### `weeks_below_demand`

Weeks where confirmed availability is insufficient.

### `max_gap_pct`

Largest confirmed capacity shortfall.

### `tentative_risk_weeks`

Weeks that become insufficient after tentative allocation.

### `missing_capacity_weeks`

Requested weeks with incomplete data.

### `coverage_ratio`

Proportion of requested weeks meeting demand.

## 7.5 Evidence and confidence

### `evidence_summary`

Up to four recent records formatted as:

`Project | Domain | Duration | Outcome`

### `years_experience`

Numeric value copied from Resources.

### `delivery_rating`

Numeric value copied from Resources.

### `profile_confidence`

Clamped 0–1 profile confidence.

### `confidence_label`

High, Medium or Verify.

### `risks`

List of capacity, confidence or evidence warnings.

## 7.6 Contact and discovery context

### `manager_name`

Manager name.

### `manager_email`

Manager email.

### `contact_email`

Resource email.

### `geography_expertise`

Copied search/display context.

### `country_expertise`

Copied search/display context.

### `project_expertise`

Copied search/display context.

### `capability_tags`

Copied search/display context.

## 8. Match diagnostics

The `MatchResult` also contains a diagnostics dictionary.

### `resources_assessed`

Number of result rows.

### `eligible`

Number passing every hard gate.

### `excluded`

Number failing one or more hard gates.

### `zero_match`

True when no eligible person exists.

### `request_window_weeks`

Number of weekly periods evaluated.

### `gate_exclusion_counts`

Counts of candidates failing:

- location;
- time zone;
- language;
- domain;
- grade;
- mandatory skill;
- mandatory proficiency;
- capacity data;
- weekly capacity.

Counts overlap when the same person fails multiple gates.

## 9. Discovery intent and result data

## 9.1 `DiscoveryIntent`

### `raw`

Original user question.

### `intent`

One of:

- expert_finder;
- resource_matching;
- capability_discovery.

### `skills`

Recognized governed skills.

### `domains`

Recognized governed domains.

### `locations`

Recognized locations or alias-expanded geographies.

### `time_zones`

Recognized exact time zones.

### `languages`

Recognized governed languages.

### `terms`

Additional search context/tokens.

### `requested_contact`

True when contact/email/reach language appears.

## 9.2 Discovery result fields

Results include identity, team, grade, location, time zone, languages, contact path, relevance score, matched context, key skills, domain/geography/project expertise and profile confidence.

Discovery relevance is an additive search score, not a percentage. A query matching several skills, domain, geography, time zone, language and context can exceed 100. It is not the same as structured fit and does not prove capacity.

## 10. Reviewer decision record

The UI creates:

### `request_id`

Current staffing request.

### `resource_id`

Reviewed candidate.

### `resource_name`

Display name.

### `system_score`

Score at review time.

### `decision`

One of:

- Not reviewed
- Shortlist
- Hold
- Reject
- Override recommendation

### `reason`

One of the configured review reasons.

### `note`

Free-text reviewer explanation.

Current limitation: these records live only in browser session state until downloaded.

## 11. Accepted source-column aliases

During resource canonicalization:

- `employee_id` or `emp_id` → `resource_id`
- `name` or `employee_name` → `resource_name`
- `timezone` or `time zone` → `time_zone`
- `skills_proficiency` or `skill_proficiency` → `skills`
- `therapeutic_areas` or `therapeutic_area` → `domains`
- `development_interest` → `development_interests`
- `manager` → `manager_name`
- `email` or `work_email` → `contact_email`

Column matching is currently case-sensitive. Production ingestion should normalize column case and whitespace first.

Workbook sheet matching is case-insensitive and trims sheet-name whitespace. Column alias matching is case-sensitive.

## 12. Data ownership recommended for production

### Resources

Recommended owner: HR/capability operations with employee attestation.

Recommended refresh: Daily for organizational fields; monthly/quarterly attestation for skills.

### Capacity

Recommended owner: PSA/RM scheduling system.

Recommended refresh: Near-real-time or daily.

### Delivery evidence

Recommended owner: Project closeout/quality process.

Recommended refresh: At project milestones and closure.

### Taxonomy

Recommended owner: CSEC capability governance group.

Recommended refresh: Versioned change process.

### Matching policy

Recommended owner: RM governance with HR, Legal, Privacy and delivery leadership review.

## 13. Minimum production-quality data additions

Before operational use, consider adding:

- source system and source record ID;
- record creation/update timestamps;
- data owner;
- verification status and verifier;
- skill last-used date;
- skill evidence source;
- language proficiency;
- work authorization;
- legal employing entity;
- security clearance;
- client conflict restrictions;
- rate/cost band;
- local holiday/calendar;
- working hours and overlap;
- booking status and booking ID;
- project/customer confidentiality level;
- retention and deletion metadata.
