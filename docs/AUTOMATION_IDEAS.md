# What to automate after Dilly's Search Term Reviewer

Start by using Dilly's Search Term Reviewer for the weekly query review. The next useful additions are checks on conversion measurement and budget pacing: both affect how confidently Relay Cloud can act on its other reports. The list below puts those dependencies first. Only the search reviewer is built here; the other rows are proposals.

Effort estimates describe a small prototype using clean exports: **small** means roughly half a day to a day, and **medium** means roughly two to four days. Production connectors, permissions, data cleanup, and adoption can take longer. These are planning estimates, not delivery commitments.

## Prioritized backlog

| Priority and idea | Inputs and rule | Output and human decision | Effort |
|---|---|---|---|
| **1 Dilly's Search Term Reviewer — built** | Query cost, clicks, CRM leads, and campaign product. Apply evidence thresholds and conservative intent rules. | A ranked query review queue with campaign-specific proposed exclusions. A person confirms relevance, approves exclusions, and applies them. | Small |
| **2 Conversion measurement check** | Monthly platform conversions and CRM leads; ideally a conversion-action export. Flag a sharp conversion rise without matching CRM improvement and changes to primary conversion definitions. | A reconciliation report and specific tracking checks. RevOps validates joins and definitions before changing conversion settings. | Small for aggregate checks; medium with action-level data |
| **3 Budget pacing monitor** | Dated spend and approved monthly allocations by product and channel. Compare spend to the elapsed share of the month; distinguish ceilings from mandatory spend. | A forecast and alert for likely overrun or unusual underspend. Demand Gen approves any reallocation; the system does not raise budgets to exhaust an allowance. | Small after daily spend is available |
| **4 Pipeline quality review** | Campaign spend, leads, MQLs, SQOs, cohort dates, and first/last-touch opportunity records. Compare mature cohorts and keep expansion separate. | A mature-cohort scorecard highlighting spend rising faster than qualified demand. A person judges deal value, attribution, and sales capacity before changing budgets. | Medium |
| **5 Creative and frequency review** | Weekly creative impressions, clicks, spend, reach, and rolling frequency. Flag deterioration against each creative's baseline, supported by meaningful volume. | A creative refresh brief and a proposed capped test. A person approves new creative, audience rules, and frequency caps. Cumulative frequency must not be treated as weekly frequency. | Small for CTR alerts; medium for proper rolling reach/frequency |
| **6 Lead follow-up and quality review** | Lead creation, assignment, first contact, qualification, and rejection reason. Flag overdue follow-up and repeated low-quality sources. | A prioritized follow-up list and source-quality summary. Sales owns outreach and RevOps approves assignment changes. The supplied workbook lacks these lead-level timestamps. | Medium |
| **7 Inference activation and retention review** | Account creation, campaign source, keys, requests, tokens, and billing events. Calculate 30-day activation and week-four retention only for fully observed cohorts. | A channel scorecard and investigation requests when acquisition gets more expensive without stronger retained use. Product Analytics validates cohort joins; Demand Gen approves scale changes. | Medium after event data is available |
| **8 Weekly decision summary** | Outputs from the checks above and a record of approved actions. Summarize what changed, what matters, and what needs a decision. | A short manager brief with linked evidence and pending decisions. A person reviews claims and approves sending it. Optional AI can draft the narrative; calculations remain deterministic. | Small once upstream reports exist |

## Recommended order

**First, use Dilly's Search Term Reviewer each week.** Work through the proposed exclusions, record the decisions, and check qualified volume after approved changes. The scope is small enough to inspect each recommendation. Its reported spend is historical exposure to the candidate queries, not guaranteed future savings.

**Next, add the conversion check and budget pacing monitor.** These catch two problems that can distort every other decision: misleading conversion counts and drift from the approved allocation. The conversion check can start with the supplied monthly export. Useful intra-month pacing requires daily or at least weekly spend, which is additional data.

**Then add pipeline and product-usage cohort reporting.** Voice needs mature qualified pipeline evidence; Inference needs account activation and retained usage. A single generic “best CPA” ranking would repeat the problem identified in the diagnosis.

## Examples of useful alerts

- **Measurement:** “Platform conversions rose, but CRM leads did not. Check conversion definitions and tracking before increasing spend.”
- **Pacing:** “At the current rate, this channel may exceed its approved monthly ceiling. Review the forecast and decide whether to reduce delivery.”
- **Inference:** “The newest accounts have not completed their observation window. Hold the retention judgment until the cohort is mature.”

These are examples of proposed alert wording, not findings produced by the current search-review code.

## What should stay with a person

Automate collection, validation, calculations, draft recommendations, and review queues. Keep campaign pauses, budget increases, broad exclusions, conversion-definition changes, customer outreach, and claims of causal lift subject to human review. Better data can support faster decisions; it does not make every business decision suitable for unattended execution.

## Source basis

The backlog follows the issues and measurement requirements in the completed Parts 1 and 2 and the supplied workbook: `Platform Performance`, `CRM Funnel`, `Budget Plan vs Actual`, `Creative Weekly`, `Opportunities`, `Inference Usage by Source`, and `Change Log`. Required inputs absent from those tabs are identified above. The current project implements the search-term workflow only.
