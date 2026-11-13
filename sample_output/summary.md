# Dilly's Search Term Reviewer

Relay Cloud paid search / weekly review

Review date: 2026-10-01. Source data pulled: 2026-10-01. Freshness: current_for_review_date.

The selected export contains 28 campaign/query pairs and $51,030.00 in historical spend. 13 pairs produced zero CRM leads, representing $19,640.00 (38.5%) of this export.

I propose 11 campaign-level exact negatives for human review. They account for $16,460.00 of historical spend. Another 2 pairs ($3,180.00) need an intent or tracking review. These amounts are not projected savings. No targeting, bids or budgets were changed.

## Scope and freshness

Selected rolling 90-day search-term export. This is not a full-account export and not one week of spend. Repeated runs may cover overlapping dates; never add their spend together.

The source date is within the configured freshness limit for this review date. Human approval is still required.

## Proposed changes

| Priority | Campaign | Search term | Historical spend | Clicks | CRM leads | Proposed action |
|---|---|---|---:|---:|---:|---|
| P1 | GS - Competitor - Voice AI | vapi login | $2,520.00 | 210 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - AI Contact Center | call center jobs remote | $2,400.00 | 300 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - Voice AI Agents | ai voice generator free | $2,340.00 | 260 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - Voice AI Agents | free ai voice changer | $1,890.00 | 210 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - Voice AI Agents | voice ai jobs | $1,710.00 | 190 | 0 | Exact negative after approval |
| P1 | GS - Competitor - Voice AI | vapi status | $1,320.00 | 110 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - Voice AI Agents | text to speech online free | $1,260.00 | 140 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - AI Contact Center | chatgpt voice mode | $960.00 | 120 | 0 | Exact negative after approval |
| P1 | GS - Competitor - Voice AI | retell ai support | $840.00 | 70 | 0 | Exact negative after approval |
| P1 | INF - GS - Category Search | chatgpt free | $660.00 | 110 | 0 | Exact negative after approval |
| P1 | GS - NonBrand - AI Contact Center | ai customer service jobs | $560.00 | 70 | 0 | Exact negative after approval |
| P2 | GS - NonBrand - AI Contact Center | ai receptionist free | $2,640.00 | 330 | 0 | Review before changing |
| P2 | INF - GS - Category Search | free llm api | $540.00 | 90 | 0 | Review before changing |

## Why each proposal was raised

- **vapi login** in GS - Competitor - Voice AI: The query appears to be navigation or support for an existing competitor user. Keep competitor pricing and alternative searches eligible. Evidence: Search Terms (last 90d) rows 22. Approval: AWAITING_HUMAN_REVIEW.
- **call center jobs remote** in GS - NonBrand - AI Contact Center: The query expresses job-seeker intent rather than intent to buy the advertised product. Evidence: Search Terms (last 90d) rows 16. Approval: AWAITING_HUMAN_REVIEW.
- **ai voice generator free** in GS - NonBrand - Voice AI Agents: The query names a consumer voice tool or consumer ChatGPT feature rather than a business phone-agent platform. Evidence: Search Terms (last 90d) rows 8. Approval: AWAITING_HUMAN_REVIEW.
- **free ai voice changer** in GS - NonBrand - Voice AI Agents: The query names a consumer voice tool or consumer ChatGPT feature rather than a business phone-agent platform. Evidence: Search Terms (last 90d) rows 9. Approval: AWAITING_HUMAN_REVIEW.
- **voice ai jobs** in GS - NonBrand - Voice AI Agents: The query expresses job-seeker intent rather than intent to buy the advertised product. Evidence: Search Terms (last 90d) rows 7. Approval: AWAITING_HUMAN_REVIEW.
- **vapi status** in GS - Competitor - Voice AI: The query appears to be navigation or support for an existing competitor user. Keep competitor pricing and alternative searches eligible. Evidence: Search Terms (last 90d) rows 23. Approval: AWAITING_HUMAN_REVIEW.
- **text to speech online free** in GS - NonBrand - Voice AI Agents: The query names a consumer voice tool or consumer ChatGPT feature rather than a business phone-agent platform. Evidence: Search Terms (last 90d) rows 10. Approval: AWAITING_HUMAN_REVIEW.
- **chatgpt voice mode** in GS - NonBrand - AI Contact Center: The query names a consumer voice tool or consumer ChatGPT feature rather than a business phone-agent platform. Evidence: Search Terms (last 90d) rows 17. Approval: AWAITING_HUMAN_REVIEW.
- **retell ai support** in GS - Competitor - Voice AI: The query appears to be navigation or support for an existing competitor user. Keep competitor pricing and alternative searches eligible. Evidence: Search Terms (last 90d) rows 24. Approval: AWAITING_HUMAN_REVIEW.
- **chatgpt free** in INF - GS - Category Search: The query asks for the consumer ChatGPT service and does not express API or developer intent. Evidence: Search Terms (last 90d) rows 29. Approval: AWAITING_HUMAN_REVIEW.
- **ai customer service jobs** in GS - NonBrand - AI Contact Center: The query expresses job-seeker intent rather than intent to buy the advertised product. Evidence: Search Terms (last 90d) rows 18. Approval: AWAITING_HUMAN_REVIEW.
- **ai receptionist free** in GS - NonBrand - AI Contact Center: Free receptionist searches may still be a business buyer evaluating a trial. Review the landing page and lead quality before excluding this exact query. Evidence: Search Terms (last 90d) rows 15. Approval: AWAITING_HUMAN_REVIEW.
- **free llm api** in INF - GS - Category Search: A free API query can be developer evaluation intent. Inspect activation and later payment evidence; zero CRM leads alone does not prove it is irrelevant. Evidence: Search Terms (last 90d) rows 28. Approval: AWAITING_HUMAN_REVIEW.

## Approval and follow up

The automation reads, checks, classifies and writes reports on its own. A person approves each exclusion, checks existing negatives, applies it in the ad platform and records the decision. Stale or undated exports must be refreshed before approval. Review cost per MQL and qualified volume over 2–4 weeks; reverse a negative if it blocks verified relevant demand. Avoid automatic broad negatives or automatic budget changes.

Queries with any CRM leads stay eligible. Pricing and comparison intent remains protected from automatic negative proposals. Ambiguous free API and free business-receptionist queries require an intent review.

## Files

- proposals.csv: review queue with metrics, rules, source rows and approval status.
- report.json: complete results for every query, configuration, source fingerprint and limitations.
- report.html: readable report that opens in a browser without a server.

## Limitations

- Historical spend attached to a flagged query is an exposure measure, not forecast or guaranteed savings.
- A rolling snapshot is rerun weekly; its rows are not weekly cohorts. Do not sum reports from overlapping exports.
- CRM leads do not establish MQL quality, incremental demand, pipeline or profitability.
- Intent patterns are editable assumptions and can misclassify new language. A person must approve every targeting change.
- The code does not read or write existing platform negative lists; an approver must check for duplicates and conflicts.
- Negative proposals are exact and campaign-specific; never turn a full query into an account-wide broad exclusion.
