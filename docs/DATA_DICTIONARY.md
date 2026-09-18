# Data dictionary

## Resources

Grain: one row per person. File: `data/resources.csv`.

Required fields:

- `resource_id`: stable unique text identifier.
- `resource_name`: display name.
- `team`: capability or organizational team.
- `grade`: numeric code in `130, 140, 150, 160, 170, 180`.
- `role_title`: governed designation. Analyst and Associate Consultant both use grade 130.
- `location`: current work country used by the hard location gate.
- `time_zone`: IANA time zone used by the hard time-zone gate.
- `languages`: pipe-delimited delivery languages.
- `skills`: pipe-delimited `Skill:Level` values.
- `domains`: pipe-delimited business domains.
- `development_interests`: pipe-delimited skills.
- `years_experience`: non-negative numeric value.
- `delivery_rating`: numeric value from 0 to 5.
- `profile_updated`: profile update date.

Optional display and contact fields:

- `contact_email`
- `manager_name`
- `manager_email`
- `geography_expertise`: regional expertise such as Europe or APAC; never used as work country.
- `project_expertise`
- `expertise_summary`

Skill proficiency values:

- `1`: Awareness
- `2`: Working
- `3`: Proficient
- `4`: Expert

## Capacity

Grain: one row per person per Monday-based week. File: `data/capacity.csv`.

- `resource_id`: foreign key to Resources.
- `week_start`: week date.
- `available_capacity_pct`: baseline available capacity from 0 to 100. The synthetic demonstration data is intentionally bounded to 30–70%.

The UI converts baseline capacity using 42.5 hours = 100%. Confirmed allocations from the register are deducted from every overlapping employee-week before matching. No working-capacity, leave, or tentative-allocation reconstruction is performed. Matching requires every week in the requested horizon to be present and at or above the requested weekly hours.

## Staffing request

- `request_id`
- `project_name`
- `start_date`
- `end_date`
- `allocation_hours`: requested weekly hours per person, from 0.25 to 42.5.
- `allocation_pct`
- `allowed_locations`
- `allowed_teams`: optional exact team gate; never a score component.
- `time_zones`
- `languages`
- `role_mix`: list of `designation`, derived `grade`, `headcount`, `mandatory_skills`, and `preferred_skills`. Skills are stored per role so a mixed-seniority team can have different expectations.
- `mandatory_skills`: legacy request-level fallback for integrations; the UI stores these within each role.
- `preferred_skills`: legacy request-level fallback for integrations; the UI stores these within each role.
- `custom_weights`: whether manager-supplied ranking weights are active.
- `weights`: mandatory skills, preferred skills, proficiency, and capacity weights. Must total 1.0.

Opportunity record fields are captured with the request and written to the register only. They
never affect eligibility or ranking:

- `client`, `project_description`, `client_location`, `client_facing`
- `therapeutic_area`: governed list
- `kpi_focus_areas`: governed list; stored as `kpi_focus_area` pipe-delimited for the register
- `travel_requirement`: governed list

## Allocation register

File: `data/staffing_register.xlsx`. The app seeds demonstration history and writes two sheets:

- `Opportunities`: Opportunity Number, Project Name, Client, Project Description, Start Date, End Date, Number of Resources Needed, Therapeutic Area, KPI Focus Area, Client Facing?, Client Location, Time Zone, Language Requirement, Travel Requirement.
- `Allocations`: Employee ID, Employee Name, Opportunity Number, Project Name, Allocation Hours / Week, Allocation %, Allocation Start Date, Allocation End Date, Status.

An Employee ID and Opportunity Number pair is unique, so a repeated confirmation does not duplicate an allocation. Historical demonstration rows use a deterministic random employee sample and include people split across multiple projects.

## Search intent

The deterministic parser and a future LLM adapter share these fields:

- `intent`
- `skills`
- `domains`
- `locations`: exact work countries.
- `geographies`: regional expertise.
- `time_zones`
- `languages`
- `designations`
- `availability_min`
- `availability_max`: internal percentages; keyword search also accepts weekly hours and converts them using the 42.5-hour standard.
- `start_date`
- `terms`

All controlled values are validated before search.
