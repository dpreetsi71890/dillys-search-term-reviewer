# Dilly's Search Term Reviewer

Dilly's Search Term Reviewer turns Relay Cloud's search export into a practical review list. It shows what each query cost, whether it produced a CRM lead, and what to do next. Clearly irrelevant searches receive a proposed campaign-level exclusion. Ambiguous searches stay open for a closer look, with the evidence and reasoning beside them.

**The tool prepares recommendations. A person approves and implements any ad-platform change.** It does not connect to an advertising account, change a budget, or upload exclusions. It uses no API keys and makes no model calls.

## Open the example first

Download and unzip the project, open the extracted folder (`dillys-search-term-reviewer` or `dillys-search-term-reviewer-main`), and double-click **`sample_output/report.html`**. It opens in your browser. You can see the completed review without installing Python, opening a terminal, or setting up GitHub.

Start with **Decision queue** to see the items needing attention. Use **Exclusions**, **Closer look**, **Kept eligible**, or **All terms** to narrow the list, or search for a query or campaign. Expand **Evidence and next step** to inspect the reasoning behind a recommendation.

To generate a fresh review, follow the local instructions below or use the [browser-only GitHub guide](docs/GITHUB_BEGINNER_GUIDE.md). Open [Actions](https://github.com/dpreetsi71890/dillys-search-term-reviewer/actions) to view completed runs or start another review.

**GitHub verification:** the [first automated run](https://github.com/dpreetsi71890/dillys-search-term-reviewer/actions/runs/43438033969) passed all 15 tests and generated the four report files on November 13, 2026. The current-date review correctly flagged the supplied historical workbook as needing a refresh before live changes can be approved.

## Run it in under 10 minutes

You need **Python 3.10 or newer** and internet access once to install the Excel-reading dependency. GitHub is optional for running the downloaded project locally. Python installers are available at [python.org/downloads](https://www.python.org/downloads/).

1. Download and unzip the project, or clone its GitHub repository. The extracted folder may be named `dillys-search-term-reviewer-main`; a clone is usually named `dillys-search-term-reviewer`.
2. Open a terminal in the project folder. You should see `search_review.py`, `config.json`, and `requirements.txt` there.
3. The supplied workbook is included at `data/relay_cloud_paid_media_dataset.xlsx`. For another export, place the replacement workbook at that same path or change `--input`.
4. Run the commands for your computer below. These commands create a separate Python environment without requiring an activation step.

### Mac or Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python search_review.py --input data/relay_cloud_paid_media_dataset.xlsx --config config.json --output output --as-of 2026-10-01
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe search_review.py --input data/relay_cloud_paid_media_dataset.xlsx --config config.json --output output --as-of 2026-10-01
```

Open `output/report.html` in your browser, or read `output/summary.md`. The `--as-of 2026-10-01` argument reproduces the historical exercise at its data-extract date. For a current operational review, omit `--as-of`; the tool will assess source freshness against the date it runs.

**API keys:** none. **Runtime AI cost:** none. GitHub Actions usage, if enabled, is subject to your account's allowance and settings.

## What the output contains

| File | What it is for |
|---|---|
| `summary.md` | A short narrative of the findings, proposed next steps, and limitations. |
| `proposals.csv` | A spreadsheet-friendly review queue with query, campaign, cost, clicks, leads, reasoning, and approval status. |
| `report.json` | Structured results and run metadata for another system to read. |
| `report.html` | A browser review screen with filters, search, evidence, decision fields, and a CSV download. It works without a hosted website. |

The checked-in `sample_output/` folder contains the output produced on the supplied dataset. It is evidence of the historical sample run; an operational run writes a new output folder. Review the sample summary for its exact counts and classifications.

### Findings on the supplied export

The export contains **$51,030** across 28 campaign/query groups. Thirteen groups produced no CRM leads, representing **$19,640, or 38.5%**, of that selected spend. The review separates them as follows:

| Review outcome | Groups | Historical spend |
|---|---:|---:|
| Proposed exact-match exclusions, pending approval | 11 | $16,460 |
| Ambiguous intent requiring investigation | 2 | $3,180 |
| Protected searches with CRM leads | 15 | $31,390 |

The two ambiguous searches are `ai receptionist free` and `free llm api`. A business receptionist and a developer API can be relevant even when the searcher wants a free option. The output therefore does not treat all zero-lead spend as automatically removable. These are historical amounts, not a savings forecast.

## How decisions work

The default evidence threshold is **at least $500 in spend, at least 50 clicks, and zero CRM leads** in the supplied reporting window. These are proposed operating thresholds, not proven statistical significance. Change the settings in `config.json` as the account's economics and data improve.

The rules then distinguish intent:

- Recognized irrelevant intent, such as job searches or competitor login/support navigation, can become a proposed exact-match exclusion for the specific campaign.
- Searches with recorded CRM leads are protected from automatic exclusion proposals. Pricing and comparison intent are also protected.
- Ambiguous searches, including developer searches for a free API or a free business receptionist, require investigation. The presence of the word “free” alone does not justify blocking a search.
- Unknown campaigns or product mappings require review instead of a guessed exclusion.

Each proposed action includes its reasoning and supporting source rows. The program normalizes query spelling for grouping, combines distinct match-type rows for the same campaign/query, and validates required data. Missing lead counts must not be treated as zero leads. Data errors stop the run instead of silently turning unreliable inputs into recommendations.

### What runs automatically and what needs approval

| Automatic work | Human decision |
|---|---|
| Read and validate the workbook. | Confirm the export is current and tracking is reliable. |
| Calculate evidence and identify review candidates. | Decide whether the query truly conflicts with the product and offer. |
| Draft a campaign-specific proposal and explanation. | Approve, reject, or modify the proposed exclusion. |
| Save a summary and review files. | Apply approved changes in the platform and record what changed. |

After implementation, compare qualified lead volume and cost per qualified lead over a suitable review window. A reduction in spend alone does not establish that the change improved the business.

In the browser report, use **Record a decision** to mark a proposal as pending, approve, reject, or investigate. Enter the reviewer's name and any notes, then click **Download review CSV**. The download includes all proposed exclusions and closer-look items, even when a filter hides some of them, plus source and configuration fingerprints to identify the run.

**Browser edits are not autosaved. Download the review CSV before refreshing or closing the page.** Approve is disabled when the browser's current UTC date identifies old, undated, or future-dated source data. The historical sample can still be explored and annotated; use a fresh export before approving live changes. A recorded approval does not change an advertising account.

You can also fill in the blank `decision`, `reviewer`, `reviewed_on`, and `notes` columns in a copy of `proposals.csv`. Archive the completed review separately before another run: generated drafts are replaced, and the tool does not carry approvals forward or apply changes from a completed review.

## Weekly operation and next month's data

The included GitHub workflow, **Dilly's weekly search review**, lives in `.github/workflows/weekly-review.yml`. It supports a manual run and a Monday schedule at **16:17 UTC** (8:17 a.m. Pacific standard time or 9:17 a.m. Pacific daylight time). The schedule becomes active after the workflow is uploaded to an enabled repository's default branch. GitHub schedules may run later than their specified time. Each run saves its files as the **`dillys-search-review-report`** artifact; it does not fetch a new advertising export. Uploading changes runs the tests and a current-date review; scheduled runs also use the current date. Only a manual run with `demo` set to `true` uses the historical exercise date.

For each weekly review:

1. Replace the workbook with the latest export while preserving its required sheet and column structure.
2. Update the extract date in the workbook README, or supply the actual extract date through `--source-as-of YYYY-MM-DD` when running locally. Do not use today's date unless the data was actually refreshed today.
3. Run the tool without the historical `--as-of` argument. On GitHub, use the normal current-date mode.
4. Read freshness warnings, review proposals, and keep a record of approved changes outside the generated output.

The source is a **selected rolling 90-day query export**, not a complete account report or a single week's spending. Repeated weekly runs can include the same historical spend. Do not sum those snapshots, call all zero-lead spend waste, or present proposed exclusions as guaranteed savings.

## Verification

Run the tests from the project root:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

On Windows, replace `.venv/bin/python` with `.\.venv\Scripts\python.exe`. Tests cover source calculations and important decision safeguards; they do not prove that an exclusion will improve live campaign performance.

## Where to look next

- [GitHub beginner guide](docs/GITHUB_BEGINNER_GUIDE.md): run the project, read the results, and share it using your browser.
- [Automation ideas](docs/AUTOMATION_IDEAS.md): a prioritized backlog for the wider paid-media plan.
- [AI assistance note](AI_ASSISTANCE.md): how AI helped build this submission and which recommendations were corrected.

### Sources

Business inputs come from the supplied `relay_cloud_paid_media_dataset.xlsx`, especially `Search Terms (last 90d)`, `Campaign Summary (6 mo)`, and `README`. The task requirements come from the supplied candidate brief. GitHub workflow behavior is documented in [workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) and [manual runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
