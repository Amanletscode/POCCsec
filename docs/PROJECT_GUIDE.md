# CSEC RM Copilot — Complete Project Guide

## How to study this project

Use this order if the project is new to you:

1. Read sections 1–3 to understand the business problem and product scope.
2. Read sections 4–5 to understand the files and end-to-end flow.
3. Open the application and follow section 6 tab by tab.
4. Read sections 7–8 to understand gates and scoring.
5. Read sections 9–11 before discussing LLMs, governance or production readiness.
6. Use the separate stakeholder walkthrough to practise the live presentation.
7. Keep the data dictionary open whenever a field name is unclear.

Do not try to memorize every formula first. The most important concept is:

**Hard gates decide who is allowed into the shortlist. Scores only rank the people who pass.**

## 1. Why this application exists

CSEC has people across multiple teams, grades, locations, time zones and capability areas. A Resource Management (RM) team may know the people in its own group very well, but may not have complete visibility across the wider organization.

The CSEC RM Copilot helps an RM or project lead answer:

- Who is technically suitable for this work?
- Who is actually available for the required dates and allocation?
- Why has one person ranked above another?
- Which strict condition excluded a person?
- Is another team carrying suitable available capacity?
- Who can be considered as a backup?
- What should a human reviewer verify before making a staffing decision?

The application is a **decision-support tool**. It does not allocate a person automatically and it does not replace RM judgement.

## 2. The simplest way to understand the product

Think of the product as five connected layers:

1. **Request:** What work needs to be staffed?
2. **People data:** What skills, experience, location and interests does each person have?
3. **Capacity data:** How much time does each person have during every requested week?
4. **Rules and ranking:** Who passes the non-negotiable conditions, and how strongly do the remaining people fit?
5. **Human decision:** RM reviews the explanation, risks and alternatives before taking action.

The application has two front doors:

- **Copilot search** for quick questions such as “Who has MMX expertise in Europe?”
- **Structured match** for a fully defined staffing requirement.

Both use governed CSEC terminology. A future LLM can improve language interpretation, but it should not control eligibility or final scoring.

## 3. Current POC scope

The included synthetic dataset contains:

- 320 resource profiles;
- 9,600 weekly capacity records;
- 1,321 delivery-evidence records;
- 22 teams;
- 11 locations;
- 7 grades;
- more than 50 governed skills;
- 30 capacity weeks from 31 August 2026 through 22 March 2027;
- an average of 4.1 delivery records per person.

All names, contacts and operational records are synthetic. They must not be presented as real CSEC employee data.

## 4. Project structure

### `app.py`

This is the Streamlit user interface. It:

- loads demo or uploaded data;
- stores the current request and results in session state;
- displays all six application tabs;
- calls validation before matching;
- calls the deterministic engine;
- explains recommendations, exclusions, risks and alternatives;
- records reviewer decisions in the current browser session;
- supports CSV downloads.

### `modules/config.py`

This is the governed business vocabulary and policy configuration. It contains:

- proficiency levels;
- grade order;
- allowed languages;
- locations and time zones;
- domains;
- skill catalogue;
- aliases such as `powerbi` → `Power BI`;
- discovery aliases such as `MMX` → `Market Mix Modeling`;
- default scoring weights;
- rule, taxonomy and data version identifiers;
- capacity policy defaults.

### `modules/data.py`

This is the data access and standardization layer. It:

- reads CSV and Excel data;
- locates expected workbook sheets;
- maps common alternative column names to canonical names;
- adds optional columns when they are absent;
- converts dates and numbers into safe formats;
- loads the demo CSV files;
- produces the combined data-health report.

### `modules/validation.py`

This is the quality-control layer. It validates:

- resource schema and identifiers;
- grade and numeric ranges;
- weekly capacity schema and logical consistency;
- evidence schema and scoring ranges;
- request dates, allocation, grade range and catalogue values;
- skill text and skill aliases.

### `modules/engine.py`

This is the authoritative deterministic matcher. It:

- creates the weekly request window;
- calculates confirmed and tentative availability;
- applies hard eligibility gates;
- calculates score components;
- ranks only eligible candidates;
- creates audit information for excluded candidates;
- returns true alternatives and clearly labelled near matches.

### `modules/discovery.py`

This is the current no-LLM natural-language interpretation layer. It:

- recognizes governed skills, domains, locations, languages and time zones;
- recognizes aliases such as MMX, pricing, Europe and Asia;
- classifies the broad intent;
- searches profiles and delivery evidence;
- returns relevant people and contact paths;
- defines the future LLM adapter contract.

### `modules/sample_data.py`

This generates reproducible synthetic demo data. It creates:

- realistic resource profiles;
- curated anchor profiles for important demo scenarios;
- weekly capacity;
- historical delivery evidence;
- teams, managers and synthetic contact details.

### `data/`

This contains the active demo files:

- `resources.csv`;
- `capacity.csv`;
- `delivery_evidence.csv`.

### `tests/`

This contains automated tests for:

- hard gates;
- zero-match handling;
- grade validation;
- skill aliases;
- capacity gaps and missing data;
- discovery questions;
- workbook canonicalization;
- scoring bounds;
- near-match behaviour;
- Streamlit startup and empty-query handling.

## 5. End-to-end application flow

### Step 1: Start the application

Run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit executes `app.py` from top to bottom. Demo data is loaded and cached. If demo CSV files do not exist, the synthetic generator creates them.

### Step 2: Select the data source

By default, the three demo CSV files are used.

An RM user may upload an Excel workbook. The application searches for:

- `Resources`, `Resource`, `Employees` or `Employee`;
- `Capacity`, `Weekly Capacity` or `WeeklyCapacity`;
- `DeliveryEvidence`, `Evidence`, `Project History` or `ProjectHistory`.

The Resources sheet is essential. Capacity and evidence are canonicalized even when optional columns are missing.

Use `.xlsx` for the current environment. Although the uploader also displays `.xls` as accepted, legacy `.xls` reading normally requires the separate `xlrd` package, which is not included in `requirements.txt`.

Important POC ingestion behaviour:

- Canonicalization happens before validation.
- Missing resource columns can be created with defaults such as `Unassigned`, `Analyst`, `Unknown`, `English`, `0` or `0.5`.
- Missing capacity percentage columns can be created as zero.
- Missing evidence fields can be created as blank/zero values.
- A missing Capacity sheet becomes an empty capacity dataset and therefore blocks structured matching.
- An empty Evidence sheet is allowed with a warning and produces conservative evidence scores.

Because default-filling can hide defects in a source workbook, production ingestion should validate the raw schema before adding defaults and should distinguish “unknown” from a genuine zero value.

### Step 3: Validate data

Every active dataset is checked before matching. Blocking errors stop matching. Warnings remain visible for human review.

Examples of blocking errors:

- duplicate or blank resource IDs;
- an unsupported grade;
- invalid dates;
- percentages outside 0–100;
- confirmed allocation plus leave exceeding working capacity;
- capacity or evidence referring to an unknown resource ID;
- duplicate resource/week capacity rows.

Examples of warnings:

- an unknown location or time zone;
- a profile with no parseable governed skills;
- tentative work that may overbook capacity;
- capacity dates that are not Mondays;
- empty delivery evidence.

### Step 4: Define demand

The structured request captures:

- request ID;
- role or opportunity;
- start and end dates;
- weekly allocation percentage;
- grade range;
- allowed locations;
- allowed time zones;
- mandatory languages;
- relevant domains;
- mandatory skills and minimum proficiency;
- preferred skills and preferred proficiency;
- whether capacity is a hard gate;
- whether domain is a hard gate.

### Step 5: Validate the request

The request is rejected when:

- dates are invalid;
- the end is before the start;
- duration is greater than two years;
- allocation is outside 1–100%;
- grade minimum is above grade maximum;
- a selected catalogue value is unsupported;
- a skill proficiency is outside 1–4.

The application warns, rather than fails, when:

- no skills are selected;
- a skill appears as both mandatory and preferred;
- selected locations and time zones do not overlap.

### Step 6: Build weekly demand

Dates are converted into Monday-based weeks. For example, a request starting Wednesday 16 September is evaluated from Monday 14 September.

Every week in the request window is checked. The engine does not use only an average, because an average can hide one critical unavailable week.

### Step 7: Apply hard gates

Each person is tested against all strict constraints. A person becomes **Excluded** if any required gate fails.

The gates are:

- selected location;
- selected time zone;
- all required languages;
- selected domain when strict-domain mode is enabled;
- grade range;
- presence of every mandatory skill;
- minimum level for every mandatory skill;
- complete capacity data for every requested week;
- enough confirmed weekly capacity when hard-capacity mode is enabled.

A high score can never compensate for a failed hard gate.

### Step 8: Score feasible candidates

Eligible people receive a 0–100 fit score. The score is a weighted combination of:

- mandatory skill coverage;
- preferred skill coverage;
- proficiency depth;
- relevant delivery evidence;
- capacity resilience;
- domain fit;
- development-interest alignment;
- profile confidence.

The default weights add to 100%. If a user changes them, they are automatically normalized back to 100%.

### Step 9: Rank and explain

Eligible people are ordered by:

1. total score;
2. minimum weekly availability;
3. profile confidence.

The results include:

- rank;
- score;
- percentile among feasible candidates;
- minimum availability;
- capacity risks;
- confidence;
- passed gates;
- skill comparison;
- evidence;
- contact path;
- alternatives.

### Step 10: Human review

The reviewer records:

- decision;
- reason;
- optional note.

This is stored only in the current Streamlit browser session. It can be downloaded as CSV, but it is not yet written to a permanent database.

## 6. Tab-by-tab walkthrough

## Tab 1 — Copilot

### Purpose

Use this for quick capability discovery when the request is not yet fully structured.

### “Ask the capability network”

This means searching the governed profiles and delivery history across the available CSEC population.

### Example questions

- “I have an MMX project, who should I contact?”
- “Who has expertise in price elasticity for Europe?”
- “Find India consultants with SQL and Python.”
- “Who are the GenAI and Agentic AI SMEs?”

### “Use current structured staffing request as context”

This indicates the intended future connection between discovery and the current structured request.

**Current implementation limitation:** the checkbox sets an internal `chat_resource_mode` session flag for resource-matching questions, but that flag is not currently read anywhere else. Therefore, checking it does not yet narrow or combine the discovery result with the structured shortlist.

### “Detected skills / geography / domain / context”

These show what the deterministic interpreter recognized in the question.

### “Relevance”

This is a discovery-search score, not the structured fit score. It reflects recognized skill, domain, geography, language, time-zone and text matches.

It is an additive relevance value, not a percentage and not capped at 100 in a fully specified query:

- recognized skill match: 35 points plus 5 per matched skill, with the extra portion capped at 15;
- domain overlap: 20 points;
- location or geography overlap: 20 points;
- exact time-zone match: 15 points;
- all requested languages present: 10 points;
- matching free-text context: 3 points per term, capped at 15.

When the interpreter detects none of the governed filters, it uses a small fallback capability score capped at 65. Discovery relevance should never be compared directly with the structured 0–100 fit score.

### “People and teams to contact”

The result includes the resource, team and direct/manager contact details where available. This tab helps locate expertise; it does not confirm availability unless the structured matcher is used.

### Important limitation

The current Copilot does not call an LLM. It uses exact vocabulary, aliases and transparent term matching. This makes it safe and demonstrable without an API key, but less flexible than a future approved model.

The **Open current request in Recommendations** button currently sets an `active_tab_hint` session value but Streamlit does not consume it to switch tabs. The user must manually open the Recommendations tab.

## Tab 2 — Structured match

### Purpose

Use this when the staffing requirement is known and a defensible shortlist is required.

### Request ID

A traceable business identifier such as `REQ-2026-001`.

### Opportunity / role

A short label for the work, such as `Healthcare Data Analyst`. It is currently descriptive and is not a scoring field.

### Required allocation

The percentage of one full-time person's weekly capacity required by the project. For example, 50% means approximately half of the person's working capacity for every week.

### Start and end dates

The delivery period. Capacity is evaluated at weekly grain across the entire period.

### Minimum and maximum grade

The allowed seniority range. Grade is evaluated using the governed order:

`Analyst → Associate Consultant → Consultant → Senior Consultant → Engagement Manager → Principal → Senior Principal`

### Allowed work locations — STRICT

If locations are selected, a person must have one of those profile locations. Blank means no location restriction.

### Allowed time zones — STRICT

If time zones are selected, a person must have one of them. Blank means no time-zone restriction.

Location and time zone are separate because a request may have a contractual location requirement as well as a collaboration-hours requirement.

### Mandatory languages

Every selected language must appear in the resource profile. This is a hard gate.

### Relevant domains

Business or delivery context such as Healthcare or Pricing & Promotion.

- With **Hard domain gate off**, domain influences score.
- With **Hard domain gate on**, at least one requested domain must match.

### Hard capacity gate

- On: the person must meet the required allocation in every week.
- Off: capacity shortfalls do not exclude the person, but risks are shown.

Missing weekly capacity data remains a hard failure because missing data must not be treated as free capacity.

### Mandatory skills

Every selected skill must be present at or above the selected proficiency. Failure causes exclusion.

### Preferred skills

These improve ranking but do not exclude a person.

### Proficiency levels

- **Awareness (1):** understands basic concepts and terminology.
- **Working (2):** can perform standard tasks with some support.
- **Proficient (3):** can work independently on normal delivery.
- **Expert (4):** can lead, design, advise or solve complex problems.

These definitions should be formally agreed with CSEC capability owners before production.

### Run explainable match

This validates the active data and request, applies all gates, calculates scores and stores the result in session state.

## Tab 3 — Recommendations

### Resources assessed

The number of profiles evaluated.

### Feasible

People who passed every hard gate.

### Excluded

People who failed at least one hard gate.

### Request weeks

The number of Monday-based weekly periods evaluated.

### Zero-match diagnostics

When nobody passes, the application does not invent a candidate. It shows how many people failed each type of gate.

Counts can overlap because one person may fail multiple constraints.

### Near matches for explicit review

These are excluded people who fail only one or two hard gates. They are not recommendations. They help RM understand whether a business constraint could be reconsidered explicitly.

### Fit score

A 0–100 weighted comparison score for eligible people. It is not a probability of project success and not a measure of employee value.

### Fit percentile

The candidate's relative position among feasible people in this particular run. A 100th percentile candidate has the highest score in the feasible group.

Percentile is request-specific and should not be compared across unrelated requests.

### Minimum weekly availability

The lowest confirmed availability found in any requested week. This is intentionally conservative.

### Weeks below demand

The number of requested weeks where confirmed availability is lower than the required allocation.

### Tentative-risk weeks

The number of weeks where availability would become insufficient if tentative commitments are confirmed.

Tentative work does not currently exclude the person, but it creates a risk flag.

### Confidence label

This comes from profile confidence:

- High: at least 0.90;
- Medium: at least 0.80 and below 0.90;
- Verify: below 0.80.

It reflects confidence in data completeness/currentness, not confidence that the person will perform well.

### Why this person is a fit

Plain-language reasons generated from the actual gates and score components.

### Mandatory gates

A visible pass/fail list. These establish eligibility before ranking.

### Skill comparison

Shows requested proficiency, candidate proficiency and any gap for mandatory and preferred skills.

### Relevant delivery evidence

Recent historical records, ordered by project end and outcome score, that help a reviewer verify context.

### Verify before confirming

Risk flags such as:

- tentative commitments;
- confirmed capacity shortfalls in non-strict mode;
- profile confidence below 80%;
- limited relevant delivery evidence.

### Score contribution

Shows the actual weighted points contributed by each component. The points sum to the total score.

### Genuine alternatives

Other people who passed the same hard gates. The selected person is deliberately excluded from this list.

### Human review

The system recommendation remains advisory. The reviewer can shortlist, hold, reject or override it and record a reason.

### Recommendation audit CSV

Exports the full result, including excluded candidates, gates, reasons and component scores. Complex list/dictionary fields are serialized as JSON strings.

## Tab 4 — Selected capacity

### Purpose

To inspect the weekly capacity of one feasible candidate.

### Working capacity

The percentage of standard capacity the person can work. A part-time week could be 80 rather than 100.

### Confirmed allocation

Already committed project work.

### Tentative allocation

Potential work that is not yet confirmed.

### Leave

Known absence percentage.

### Available

Calculated as:

`working capacity − confirmed allocation − leave`

The value is clipped between 0 and 100.

### Net availability after tentative work

Calculated as:

`available capacity − tentative allocation`

### Gap

Calculated as:

`maximum(requested allocation − available capacity, 0)`

### Status

- Covered: confirmed availability meets demand.
- Below demand: confirmed availability is insufficient.
- Missing capacity data: one or more required source values are absent.

## Tab 5 — Capability map

### Purpose

To understand supply across teams, locations and skills rather than only finding one individual.

### Find supply for a skill

Filters profiles containing the selected governed skill.

### Geography focus

Filters by profile location or declared geography expertise.

### People in pool

Count of matching profiles.

### Teams

Number of distinct teams represented.

### Locations

Number of distinct profile locations.

### Senior / SME pool

Count of Engagement Managers, Principals and Senior Principals in the selected pool. This is a seniority count, not proof that every person is an SME.

### Supply by skill

Counts how many profiles list each governed skill. It measures declared profile supply, not availability or verified mastery.

The current chart uses the full resource dataset. It does not change when the skill/geography pool above it is filtered.

### Feasible capacity by team

For the current structured request, groups eligible candidates by team and shows:

- number feasible;
- median score;
- best score;
- minimum weekly availability.

This supports cross-team capacity balancing.

## Tab 6 — Audit & data

### Purpose

To make the model inspectable, versioned and safer to operate.

### Resource rows / capacity rows / delivery records

Counts of the active source data.

### Validation sections

Show schema errors and quality warnings for each dataset.

### Current request rule snapshot

Captures:

- current structured request;
- normalized weights;
- rule version;
- taxonomy version;
- data version.

This is important because a score should always be traceable to the rules and data version that produced it.

### Reviewer decisions download

Exports decisions recorded in the current browser session.

### Future LLM integration contract

Documents the fields an approved LLM may extract. The LLM may translate language into structured intent, but may not change hard gates or scoring policy.

### Product guardrails

Summarizes strict constraints, explainability, human control and the exclusion of protected personal attributes.

## 7. How scoring works

## 7.1 Default component weights

- Mandatory skills: 35%
- Preferred skills: 10%
- Proficiency: 10%
- Relevant evidence: 15%
- Capacity: 15%
- Delivery/domain fit: 8%
- Development alignment: 4%
- Data confidence: 3%

User-entered weights are normalized. For example, if entered values total 200, every value is divided by 200 so the final weights total 1.0.

## 7.2 Mandatory skill score

For each mandatory skill:

`minimum(candidate level ÷ requested level, 1) × 100`

The component is the average across mandatory skills.

For eligible candidates this will normally be 100 because mandatory proficiency is also a hard gate.

## 7.3 Preferred skill score

Uses the same coverage formula, but preferred gaps do not exclude a person.

When no preferred skills are selected, the component uses a neutral value of 50.

## 7.4 Proficiency score

This separates meeting the threshold from depth above the threshold:

- up to 70 points for reaching the requested level;
- up to 30 additional points for proficiency above the requested level.

An Expert can therefore rank above someone who only meets the requested minimum, while mandatory absence still causes exclusion before scoring.

## 7.5 Relevant evidence score

For every evidence record, the engine calculates:

- skill overlap with requested skills;
- requested-domain match;
- outcome quality from 0–5;
- recency over a five-year window.

The final evidence component combines:

- 45% average relevance of the three strongest records;
- 20% average outcome quality;
- 15% average recency;
- 10% years of experience, capped at 10 years;
- 10% delivery rating.

Evidence is supportive context. It must not be interpreted as a guaranteed performance prediction.

## 7.6 Capacity score

If the person fails some weeks in non-strict mode:

`coverage ratio × 70`

If every week is covered:

`70 + up to 30 points for resilient tenth-percentile headroom`

This rewards someone who not only meets demand but has safer capacity across the horizon.

## 7.7 Delivery/domain fit

Calculated as the percentage of requested domains found in the profile.

When no domain is requested, the component uses a neutral value of 50.

## 7.8 Development alignment

Measures how many preferred skills also appear in the person's development interests.

This is deliberately low-weighted. Development goals can support employee growth, but should not override delivery readiness.

## 7.9 Data confidence

`profile_confidence × 100`

Profile confidence is capped between 0 and 1.

## 7.10 Total score

Each normalized component is multiplied by its configured weight. The weighted points are added.

`total fit = sum(component score × component weight)`

An excluded person receives:

- `total_score = 0`, because they are not recommendable under current gates;
- a separate `potential_score` for transparent near-match diagnostics.

## 8. Hard rules versus soft signals

### Hard rules

These decide eligibility:

- selected location;
- selected time zone;
- selected mandatory languages;
- grade range;
- mandatory skill presence;
- mandatory skill proficiency;
- complete capacity data;
- weekly capacity when strict mode is on;
- domain when strict-domain mode is on.

### Soft signals

These affect order or create risks:

- preferred skills;
- extra proficiency;
- evidence relevance and recency;
- capacity headroom;
- domain when strict-domain mode is off;
- development interests;
- profile confidence;
- tentative allocations.

### Why this separation matters

Without separation, a strong score could hide an unacceptable condition. For example, excellent Python experience must not compensate for a mandatory French-language requirement that the person does not meet.

## 9. Natural-language discovery and future LLM

## 9.1 What works now

The deterministic interpreter:

- converts known aliases into catalogue values;
- detects exact phrases;
- searches profile, expertise and evidence text;
- recognizes broad search intent;
- returns transparent matches.

## 9.2 What an LLM should do later

An approved LLM can:

- understand unstructured project descriptions;
- identify likely skills and domains;
- extract dates, allocation, location, time-zone and language needs;
- ask clarification questions;
- populate a draft structured request;
- summarize deterministic results in business language.

## 9.3 What an LLM must never do

It must not:

- invent employee skills;
- bypass data validation;
- decide hard-gate policy;
- silently change weights;
- assign people automatically;
- expose sensitive data;
- treat prompt instructions as permission to override governance.

LLM output should be validated against a strict structured schema and the governed catalogues before it reaches the matching engine.

## 10. Guardrails required before production

### Human control

- Recommendations require RM/project-lead review.
- Overrides require a reason.
- No automatic allocation.

### Fairness

- Do not include age, gender, race, religion, disability, marital status or similar protected attributes.
- Do not use names or locations as proxies for protected identity.
- Regularly test whether rankings create unexplained group-level disparities.

### Data quality

- Define owners for profiles, capacity and delivery evidence.
- Record source-system timestamps.
- Expire stale profiles.
- Do not treat missing information as positive information.

### Security and privacy

- Add authentication and role-based access.
- Limit contact and staffing data to authorized users.
- Encrypt data in transit and at rest.
- Maintain access and decision audit logs.
- Apply retention rules.

### Business-policy gaps

The POC does not yet model:

- work authorization;
- legal employing entity;
- security clearance;
- rate/cost;
- client conflicts;
- contractual restrictions;
- holiday calendars;
- daily working-hour overlap;
- partial-week start/end proration;
- confirmed bookings created by this application.

These must be governed fields before production use.

## 11. Known POC limitations

- Synthetic data is designed for demonstration, not operational decisions.
- The app is a single Streamlit script, not a production service architecture.
- Uploaded workbooks are held only for the current session.
- Reviewer decisions are not persisted centrally.
- There is no authentication or role-based access.
- There is no real HR, PSA, CRM or capacity-system connection.
- Search uses deterministic phrase/alias matching, not semantic embeddings.
- The role title itself does not affect ranking.
- Tentative allocation creates a risk but is not currently reserved by the hard capacity gate.
- Capacity is weekly and Monday-based.
- Profile confidence is supplied data; the app does not calculate it from source lineage.
- Delivery ratings and outcomes require governance to avoid inconsistent or biased input.
- Fit scores are relative decision aids, not calibrated probabilities.

## 12. How to run and test

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### Run

```powershell
python -m streamlit run app.py
```

### Test

```powershell
python -m pytest -q
```

Expected current result: 21 passing tests.

### Common stale-import issue

If Streamlit says a recently added function cannot be imported:

1. close all old Streamlit processes;
2. verify only one server is running;
3. delete project `__pycache__` directories if necessary;
4. restart using the virtual environment's Python.

## 12.1 What Streamlit remembers

Streamlit reruns `app.py` after interactions, while selected values are retained in per-browser session state:

- `request` — current structured request;
- `results` — latest `MatchResult`;
- `decisions` — reviewer decisions recorded during the session;
- `chat_history` — Copilot searches, with only the latest three displayed;
- `chat_query` — text populated by an example button;
- `chat_resource_mode` — currently written but not used;
- `active_tab_hint` — currently written but not used for navigation.

Closing/clearing the Streamlit session loses this state unless the user has downloaded an export. Uploaded data, decisions and chat history are not persisted to a database.

## 13. Key glossary

### Allocation

The percentage of a person's working capacity requested or already committed.

### Availability

Working capacity remaining after confirmed allocation and leave.

### Capability

A broad ability area that may contain skills, domain experience or methods.

### Capacity

How much work a person can take during a specific period.

### Canonicalization

Converting different source names and formats into one standard internal schema.

### Confidence

Confidence in profile data quality/currentness. It is not predicted performance.

### Deterministic

The same input data, request, rules and weights produce the same output.

### Development interest

A capability the employee would like to build or use.

### Domain

Business or delivery context such as Healthcare or Pricing & Promotion.

### Eligibility

Whether a person passes every hard gate.

### Evidence

Historical project records supporting claimed delivery experience.

### Fit percentile

Relative score position among eligible candidates for the same request.

### Fit score

Weighted comparison score for an eligible candidate.

### Guardrail

A rule that prevents unsafe, unfair, misleading or unauthorized use.

### Hard gate

A non-negotiable condition. Failure excludes the person.

### Headroom

Availability remaining above the requested allocation.

### Near match

An excluded person who fails only a small number of hard gates and is shown only for explicit review.

### Profile confidence

A 0–1 source field expressing trust in a profile's completeness/currentness.

### Proficiency

Skill level from Awareness (1) to Expert (4).

### RM

Resource Management: the business function coordinating staffing and capacity.

### SME

Subject Matter Expert.

### Soft signal

Information that affects ranking or risk but does not independently exclude a person.

### Taxonomy

The governed catalogue of skills, domains, grades and related terms.

### Tentative allocation

Potential work not yet confirmed.

### Utilization

The portion of available working capacity already assigned to productive work. This POC stores allocations and derives headroom; it does not maintain a separate utilization field.
