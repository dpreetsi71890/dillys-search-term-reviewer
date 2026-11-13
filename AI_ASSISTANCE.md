# AI assistance and review corrections

Project: **Dilly's Search Term Reviewer**, built for the Relay Cloud exercise.

ChatGPT helped analyze the supplied workbook, draft the Python implementation, design the branded report, write the GitHub workflow and documentation, and review the output. The automation itself uses transparent rules and does not call an AI model. It needs no AI API key and incurs no model usage charges.

The review made these changes to the initial approach:

1. **Narrow the blocking proposals.** The initial diagnosis grouped `ai receptionist free` with off-target Voice searches. That term could represent a business buyer evaluating a trial. The build keeps it in human investigation alongside `free llm api`, rather than proposing an exclusion. The proposed negative list is therefore narrower than the original diagnosis.
2. **Protect demonstrated demand.** A query with a recorded CRM lead is protected from an exclusion proposal. Pricing, comparison, and developer intent are not treated as waste simply because the query includes a competitor name or the word `free`. High cost on a relevant zero-lead query prompts investigation.
3. **Use the right time basis.** The search-term tab is a selected rolling 90-day export. Its spend is historical exposure, not weekly savings, not a forecast, and not a complete account total. The tool is run weekly; repeated runs must not be added together.
4. **Check freshness and data quality.** Missing CRM values are not assumed to mean zero leads. An old extraction date requires a fresh export before a proposed campaign change is ready for approval. The historical demonstration uses an explicit October 1, 2026 evaluation date.
5. **Keep approval separate from detection.** The tool can validate, calculate, classify, rank, and write reports on its own. Every live keyword exclusion, bid change, or budget change remains a human decision. There is no ad-platform write connection.

AI was useful for turning the analysis into repeatable code and for proposing edge cases to test. It was less reliable when broad intent labels could hide valid buyer demand, and when period totals could be mistaken for incremental savings. These corrections are part of the implementation and are reflected in the saved sample output.

## Validation status

The program was run locally on the supplied workbook. The repository contains its saved output and automated checks for the decision boundaries and input handling. The scheduled workflow is supplied for GitHub; a hosted run still needs to be verified after the files are placed in an authenticated GitHub account.
