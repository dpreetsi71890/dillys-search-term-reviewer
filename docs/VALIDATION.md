# Validation record

Project: Dilly's Search Term Reviewer for the Relay Cloud exercise.

The program was run locally with Python 3.12.14 and openpyxl 3.1.5. The reproducible demonstration uses an evaluation date of October 1, 2026, matching the supplied workbook's extract date.

## Checks completed

- Fifteen behavior tests passed with `python -m unittest discover -s tests -v`. Tests use miniature temporary workbooks, so replacing the operational workbook next month does not invalidate a fixed historical expectation.
- The actual supplied workbook produced 28 campaign/query groups and $51,030 in selected export spend.
- Thirteen groups had zero CRM leads and $19,640 of historical spend. Eleven proposed exclusions accounted for $16,460; two ambiguous queries accounted for $3,180.
- Fifteen lead-producing queries remained eligible. The three pricing queries retained all 17 recorded CRM leads.
- A current-date review on November 13, 2026 correctly marked the October 1 export as 43 days old and required a refresh before approval.
- The workflow YAML parsed with manual, upload-triggered, and weekly runs and read-only repository permissions. A hosted GitHub run has not yet been verified; that requires the project to be uploaded to an authenticated account.
- The branded HTML was checked for unique element IDs, complete embedded source records, escaped text, and valid JavaScript syntax. Its interactive controls were reviewed in code; a live browser interaction test could not run in the build environment.

## Limits of these checks

These checks validate calculation, input handling, and proposed decision rules. They do not prove that any exclusion improves live marketing results. Historical spend is not forecast savings. Live changes require approval and a later review of qualified demand.
