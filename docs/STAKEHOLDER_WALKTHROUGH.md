# CSEC RM Copilot — Stakeholder Walkthrough and Presentation Script

## 1. Presentation objective

The goal is not to claim that the POC has solved resource management completely. The goal is to demonstrate a credible, governed decision-support approach that:

- improves visibility across CSEC;
- separates strict constraints from ranking preferences;
- combines capability and weekly capacity;
- explains every recommendation;
- handles zero matches honestly;
- supports human RM decisions;
- can accept an approved LLM later without making the LLM the decision-maker.

## 2. Recommended presentation structure

Use this sequence:

1. Business problem — 2 minutes
2. Solution and guardrails — 2 minutes
3. Live capability discovery — 2 minutes
4. Structured staffing request — 3 minutes
5. Recommendation explanation — 4 minutes
6. Capacity and cross-team view — 2 minutes
7. Audit, limitations and roadmap — 3 minutes

Total: approximately 18 minutes.

## 3. Opening statement

You can say:

> CSEC has a broad global capability network, but resource managers may not always have complete visibility across teams, locations and delivery histories. This can cause avoidable staffing delays, missed cross-team opportunities and uneven capacity pressure. The CSEC RM Copilot is a decision-support application that combines a staffing requirement with governed employee capability, weekly availability and prior delivery evidence. It recommends feasible people, explains why they fit, highlights risks and keeps the final decision with RM and project leadership.

## 4. Explain what the product is — and is not

Say:

> This is not an automatic allocation tool and it does not replace RM judgement. It first applies non-negotiable business rules, then ranks only the people who pass those rules. A high score can never hide a failed mandatory constraint. The current POC also does not require an LLM API. Its matching engine is deterministic, so the same data and request produce the same result.

Key message:

- AI can improve how a user describes a request.
- Deterministic rules should remain responsible for eligibility and scoring.
- Humans remain responsible for staffing decisions.

## 5. Live demonstration preparation

Before the meeting:

1. Open a PowerShell terminal in the `POCCsec` folder.
2. Stop older Streamlit processes so only one server is running.
3. Run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

4. Open the local URL shown by Streamlit.
5. Confirm the sidebar shows:
   - 320 resources;
   - 9,600 capacity rows;
   - 1,321 delivery records;
   - no blocking data errors.
6. Keep browser zoom around 90–100%.
7. Do one practice run before the meeting.

## 6. Demo part 1 — Copilot capability discovery

### What to show

Open the Copilot tab.

### What to say

> The first entry point is for a manager who may not yet have a complete staffing specification. They can ask a simple capability question. The current version uses governed vocabulary and aliases rather than an external LLM, which allows us to demonstrate the product without API access.

### Query 1

Use:

`I have an MMX project, who should I contact?`

### Explain the result

Say:

> The interpreter recognizes MMX as Market Mix Modeling and searches skills, project expertise, capability tags and historical evidence. It returns people and contact paths. This is an expertise-discovery result; it does not yet confirm that those people are available.

Expected leading names include curated European pricing/MMX profiles such as Camille Dubois, Lena Fischer or Sofia Martinez.

### Query 2

Use:

`Who has expertise in price elasticity for Europe?`

Explain:

> The query contains both a governed skill and geography. Europe expands to the relevant European locations, while Price Elasticity maps directly to the skills catalogue.

### Important distinction

Say:

> Copilot relevance is not the final staffing fit score. For an auditable staffing decision we move to the structured matcher.

## 7. Demo part 2 — Structured staffing request

Open the Structured match tab.

Use this scenario:

- Request ID: `REQ-2026-001`
- Opportunity / role: `Healthcare Data Analyst`
- Start: `14 September 2026`
- End: `30 November 2026`
- Required allocation: `50%`
- Minimum grade: `Analyst`
- Maximum grade: `Consultant`
- Allowed location: `India`
- Allowed time zone: `Asia/Kolkata`
- Mandatory language: `English`
- Relevant domain: `Healthcare`
- Hard capacity gate: On
- Hard domain gate: Off
- Mandatory SQL: Proficient
- Mandatory Python: Working
- Mandatory Healthcare Data: Working
- Preferred Power BI: Working
- Preferred Claims Data: Working

### Explain each business choice

Say:

> We need half of one person's weekly capacity for the full period. Location and time zone are strict for this example. English is mandatory. Healthcare is relevant but not made a strict gate, because transferable analytics experience may still be valuable. SQL, Python and Healthcare Data are non-negotiable. Power BI and Claims Data are useful but not mandatory.

### Run the match

Click **Run explainable match**.

Expected result with the current synthetic data:

- 320 resources assessed;
- 2 feasible;
- Aarav Sharma ranked first;
- approximately 88.2/100 fit;
- minimum confirmed weekly availability of 64%.

Values can change if the synthetic data, request, rules or weights are changed.

## 8. Demo part 3 — Recommendation explanation

Open the Recommendations tab.

### Explain “feasible”

Say:

> Feasible means the person passed every active hard gate. It does not mean the person is automatically selected.

### Explain the shortlist

Point out:

- rank;
- grade and team;
- fit score;
- percentile;
- minimum availability;
- weeks below demand;
- tentative-risk weeks;
- confidence label.

Say:

> The fit score is a transparent comparison score, not a probability of success. Percentile is relative only to feasible people in this request.

### Select Aarav Sharma

Walk through:

1. Why this person is a fit
2. Mandatory gate checks
3. Skill comparison
4. Delivery evidence
5. Risks
6. Contact path
7. Score contribution
8. Capacity summary
9. Genuine alternatives

### Explain the score

Say:

> The total combines mandatory coverage, preferred skills, depth of proficiency, relevant and recent delivery evidence, capacity resilience, domain fit, development alignment and profile confidence. The largest weight is mandatory capability. Capacity and delivery evidence are also material.

### Explain risk flags

Say:

> A person may be eligible but still require verification. Tentative assignments, limited evidence or stale/low-confidence profiles are shown as risks rather than hidden.

### Explain human review

Say:

> RM can shortlist, hold, reject or override a recommendation and record a reason. In a production version this feedback would be persisted and used for audit and controlled model improvement.

## 9. Demo part 4 — Weekly capacity

Open Selected capacity.

Say:

> Average utilization can hide a critical delivery week. Therefore, this view checks every week in the request window.

Explain:

- working capacity is the person's weekly base;
- confirmed allocation is already committed work;
- tentative allocation is possible future work;
- leave is known absence;
- available capacity equals working capacity minus confirmed work and leave;
- the requested 50% line is compared with every week;
- tentative work creates a separate risk view.

Key message:

> Missing capacity is never interpreted as availability.

## 10. Demo part 5 — Capability and cross-team intelligence

Open Capability map.

### Example

Choose a skill such as `GenAI`, `Price Elasticity` or `Healthcare Data`.

Explain:

> This changes the discussion from “Who is one good person?” to “Where does this capability exist across CSEC?” We can see people, teams, locations and senior capability pools.

If a structured match exists, show **Feasible capacity by team**.

Say:

> This supports capacity balancing by showing which teams have feasible people under the same request constraints.

## 11. Demo part 6 — Audit and governance

Open Audit & data.

### Show validation

Say:

> A recommendation is only credible when the source data is visible and validated. Blocking quality errors prevent matching; warnings remain visible.

### Show rule snapshot

Say:

> Every run is associated with a request, normalized weights, rule version, taxonomy version and data version. This gives us reproducibility and auditability.

Current versions:

- Rule version: `RM-RULES-3.1`
- Taxonomy version: `SKILL-CATALOG-2.0`
- Data version: `SYNTHETIC-2026-09.1`

### Show LLM contract

Say:

> When an approved LLM becomes available, it can interpret free text and produce these governed fields. It cannot change eligibility policy or directly assign a person.

## 12. Demonstrate zero-match integrity

This is an optional but powerful part of the demo.

Create an intentionally difficult request, for example:

- India location;
- French mandatory;
- SQL Expert;
- Python Expert;
- Agentic AI Expert;
- strict capacity.

Run the match.

Say:

> A weak system may return a poor candidate just to avoid an empty screen. This application instead reports zero feasible people, explains which constraints caused exclusions and shows near matches only as excluded candidates requiring explicit review.

Point out:

- gate-exclusion chart;
- overlapping exclusion counts;
- near matches clearly labelled as not recommendations.

## 13. How to answer “Why is the score not higher?”

Say:

> A lower score does not necessarily mean a poor employee. It means the available evidence and preferred attributes for this specific request do not produce a perfect match. The score is intentionally conservative and request-specific. It also includes capacity resilience, relevant evidence and profile confidence rather than only checking whether skill names exist.

If stakeholders focus heavily on score:

- bring attention back to eligibility first;
- show component contributions;
- show missing preferred skills/evidence;
- explain that weights are policy decisions requiring calibration;
- avoid changing synthetic data only to produce attractive scores.

## 14. How to explain hard and soft criteria

Use this simple example:

> If French is mandatory for client workshops, it is a hard gate. If French is simply helpful, it should be a preferred signal instead. Hard rules decide who can be considered. Soft signals decide the order of people who can be considered.

Recommended hard criteria when genuinely non-negotiable:

- mandatory skills and minimum levels;
- date window and allocation;
- grade range;
- contractual work location;
- necessary time zone;
- necessary language;
- complete capacity data;
- confirmed weekly headroom;
- domain only when regulation or delivery risk requires it.

Recommended soft criteria:

- preferred skills;
- additional proficiency;
- historical evidence;
- development interests;
- profile confidence;
- tentative commitments;
- non-essential domain familiarity.

## 15. Stakeholder questions and suggested answers

### “Is this really AI if there is no LLM?”

> The current POC uses deterministic decision intelligence and governed natural-language interpretation. This is deliberate because staffing rules must be auditable. An LLM can later improve free-text understanding and explanations, while the deterministic engine remains authoritative.

### “Why not let the LLM select the best employee?”

> LLMs can produce variable or unsupported answers. Staffing decisions involve capacity, policy, fairness and employee impact. The safer architecture uses the LLM only to translate language, then validates and ranks through explicit rules with human approval.

### “Where does the data come from?”

> The POC uses synthetic CSV data generated locally. A production version should integrate governed HR/capability, PSA/capacity and project-outcome systems.

### “Is the score a probability that the project will succeed?”

> No. It is a weighted comparison of fit evidence for the current request.

### “Can a person fail location but still rank first?”

> No. A failed hard gate sets the recommendation score to zero and marks the person excluded.

### “What if capacity data is missing?”

> The person is excluded because missing data is not treated as free capacity.

### “Does tentative work exclude someone?”

> Not in the current policy. It creates a visible risk. The policy can be made stricter if CSEC decides tentative bookings should reserve capacity.

### “How does the app support employee development?”

> Preferred skills are compared with development interests using a small weight. This helps surface suitable growth opportunities without overriding mandatory delivery needs.

### “Can we change the weights?”

> Yes, and the app normalizes them to 100%. However, production weights should be governed, tested and versioned rather than changed casually for individual outcomes.

### “How are skills verified?”

> The POC stores profile skills and supporting delivery evidence, but does not implement formal verification. Production should add verification source, verifier, date and last-used information.

### “Could historical ratings introduce bias?”

> Yes. Delivery ratings, years of experience and manager-entered profiles require fairness review, calibration and source governance before production.

### “Does it use protected personal information?”

> No protected attributes are included in scoring. Production governance should also test for proxy effects.

### “Can this optimize an entire project team?”

> Not yet. The current engine ranks individuals for one staffing request. Team-composition optimization, role dependencies and budget constraints are roadmap capabilities.

### “Can it write allocations back to a scheduling system?”

> Not in the POC. It is read-only decision support. Production integration would need approval, conflict checking, authentication and an auditable confirmation workflow.

## 16. Risks to disclose honestly

Do not hide these:

- data is synthetic;
- no production system integrations;
- no authentication or role-based permissions;
- no permanent reviewer-decision store;
- no formal fairness evaluation yet;
- no work-authorization or legal-entity rules;
- no rate/margin component;
- role-title text is not currently scored;
- weekly capacity does not model daily overlap;
- LLM integration is a future adapter, not current functionality;
- score calibration requires real business feedback.

Being open about these limits makes the proposal more credible.

## 17. Roadmap proposal

### Phase 1 — Governance and data foundations

- Agree skill taxonomy and proficiency definitions.
- Identify authoritative systems.
- Add data owners, lineage, timestamps and verification.
- Confirm hard/soft policy with RM, HR, Legal and Privacy.

### Phase 2 — Secure operational pilot

- Add authentication and role-based access.
- Connect read-only HR/capability and capacity feeds.
- Persist requests, results, decisions and overrides.
- Run fairness and security reviews.
- Pilot with a controlled RM group.

### Phase 3 — Approved LLM interpretation

- Extract structured requests from project descriptions.
- Ask clarification questions.
- Validate every extracted value against governed catalogues.
- Keep deterministic matching unchanged.

### Phase 4 — Learning and optimization

- Use confirmed allocations and outcomes as governed feedback.
- Calibrate weights and thresholds.
- Add team-composition, rate/margin and scenario planning.
- Monitor quality, fairness and business value.

## 18. Closing statement

You can say:

> The value of the CSEC RM Copilot is not simply producing a list of names. It creates one governed workflow connecting demand, capability, evidence and weekly capacity across teams. It makes strict constraints visible, explains every recommendation, handles uncertainty honestly and leaves the final decision with accountable RM and project leaders. The POC gives us a concrete foundation; the next step is to validate the policy and data model with stakeholders before integrating production systems or an approved LLM.

## 19. One-minute summary for senior stakeholders

> CSEC RM Copilot is an explainable resource-matching and capacity-balancing assistant. A user can discover expertise through natural language or submit a structured staffing request. The engine first applies non-negotiable rules such as mandatory skills, grade, location, language and weekly capacity. It then ranks only feasible people using transparent evidence, availability and fit components. It shows risks, backups, cross-team supply and a complete audit trail. The current POC uses synthetic data and does not need an LLM key. Future LLM access would improve request interpretation, while deterministic rules and human approval remain in control.
