# Using Dilly's Search Term Reviewer on GitHub

**Your private repository is already set up:** [dpreetsi71890/dillys-search-term-reviewer](https://github.com/dpreetsi71890/dillys-search-term-reviewer). The [first automated run](https://github.com/dpreetsi71890/dillys-search-term-reviewer/actions/runs/43438033969) succeeded. Start at section 3 to run another review, section 4 to read the results, or section 6 to give the reviewers access. Sections 1 and 2 are reference instructions for creating another copy.

**Start with the finished example.** Download and unzip the project, open the extracted folder (`dillys-search-term-reviewer` or `dillys-search-term-reviewer-main`), and double-click `sample_output/report.html`. It opens in your browser without an installation or a terminal. The guide below explains how to run the project again and give the reviewers a working repository link.

GitHub is a place to keep the project's files and share a link with the reviewers. A **repository**, usually shortened to **repo**, is the project's folder on GitHub. A **commit** saves a set of changes. **Actions** is the section that runs automated instructions. An **artifact** is a downloadable file produced by one of those runs.

You can complete the steps below in your browser. You do not need to learn programming or install Git to upload the project and run its included workflow.

## 1 Create the repository

1. Sign in to GitHub, or create an account if you do not have one.
2. Open [github.com/new](https://github.com/new).
3. Choose your own account as the owner. Enter `dillys-search-term-reviewer` as the repository name.
4. Choose **Private**. You can give the reviewers access later. This keeps the complete exercise and dataset out of public search.
5. Leave the options to add a README, `.gitignore`, and license unselected; this package already contains the files it needs.
6. Click **Create repository**.

GitHub's [repository creation instructions](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository) explain the same controls if the page wording changes.

## 2 Upload the actual project files

Unzip the delivered project on your computer. Open the extracted `dillys-search-term-reviewer` folder. Its contents should include `README.md`, `search_review.py`, `config.json`, `requirements.txt`, and folders such as `data`, `docs`, `sample_output`, and `tests`.

On an empty repository, click **uploading an existing file**. If you already have files in it, choose **Add file → Upload files**. Drag the extracted project's **contents** into the upload area, preserving the folders. Do not upload only the ZIP, and do not put the whole project inside an extra folder: `search_review.py` and `README.md` must appear directly on the main repository page.

Enter a short save message, such as `Add Dilly's Search Term Reviewer`, and save the changes. GitHub may call this **Commit changes** or **Propose changes**, depending on the branch settings. For your new personal repository, use the main branch when that choice is offered.

The `.github` folder can be hidden on your computer. That folder contains the instructions that enable Actions. After uploading, check the repository for `.github/workflows/weekly-review.yml`. If it is missing:

1. Open the uploaded file `docs/weekly-review.yml.txt` and copy all its contents.
2. Return to the main repository page and select **Add file → Create new file**.
3. Enter `.github/workflows/weekly-review.yml` as the complete filename.
4. Paste the copied text into the editor and save it on the main branch.

The leading dot and both folders in that path matter. GitHub looks in that location for workflow files. See [uploading files](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) and [creating files](https://docs.github.com/en/repositories/working-with-files/managing-files/creating-new-files).

## 3 Run the example without installing Python

1. Open the repository's **Actions** tab.
2. If GitHub asks you to enable workflows, enable them for your repository.
3. Choose **Dilly's weekly search review** in the left sidebar.
4. Click **Run workflow**, keeping `main` selected.
5. Set **demo** to `true` to reproduce the supplied historical exercise at October 1, 2026. Then click the final **Run workflow** button.
6. Open the new run. Wait for the jobs to finish. A green check indicates that the workflow completed; a red mark means you should open the failed step's log.

The Run workflow control appears only after the workflow file is present on the default branch and includes a manual trigger. GitHub documents this in [manually running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

## 4 Read the results

Open the completed run's summary. In **Artifacts**, download **dillys-search-review-report**. Unzip that download and open `report.html` in your browser. Read `summary.md` for the short explanation and open `proposals.csv` in Excel or Google Sheets to review the proposed changes.

In the browser report:

- Start with **Decision queue**, or choose **Exclusions**, **Closer look**, **Kept eligible**, or **All terms**. You can also search by query or campaign.
- Expand **Evidence and next step** to inspect the recommendation.
- Use **Record a decision** on a proposal, add your name and notes, then choose **Download review CSV** to save the review. The download includes every proposed exclusion and closer-look item, not just the visible rows.

**Your browser edits disappear if you refresh or close the page without downloading them.** The historical sample is old data, so its Approve option is disabled when checked against today's date. You can still inspect it, add notes, and record a reject or investigate decision. Fresh source data is required before an approval can be recorded; no decision in the report applies a change to an ad account.

The repository also includes the original `sample_output/` results, so the reviewers can inspect an actual output before running anything. Reports downloaded from a new run reflect that run's input data and settings. GitHub explains artifact downloads in [downloading workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

## 5 Use it weekly

The schedule is Mondays at **16:17 UTC**, which is 8:17 a.m. Pacific standard time or 9:17 a.m. Pacific daylight time. It runs on the data currently in the repository. It cannot fetch a fresh advertising export by itself.

Before a real review, upload a refreshed workbook into `data/` with the same filename and update its actual extract date in its README sheet. Then run with **demo** set to `false`, so the tool checks freshness against the current date. Scheduled runs also use the current date. Old data should produce a freshness warning rather than look newly collected.

Every proposed advertising change still needs a person to approve and implement it. Running the workflow does not modify your advertising account.

Keep the downloaded review CSV separately. A new run generates a fresh draft and does not retain prior approvals. If you prefer Excel, fill in the blank `decision`, `reviewer`, `reviewed_on`, and `notes` columns in a copy of `proposals.csv` instead.

## 6 Send the submission

Copy the URL of the main repository page. That is the repository link requested in Part 3. For a private repository, use **Settings → Collaborators** to invite only the GitHub identities or email addresses provided by the hiring team; confirm access before submitting. GitHub provides [collaborator invitation instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository). Include Parts 1 and 2 separately unless the reviewers ask for them inside the repository.

Before submitting, check that the README opens, the workbook and sample output are present, and at least one GitHub run finishes successfully. The local build and the GitHub run are separate checks: the latter can be verified only after upload.

## Common fixes

| What you see | What to check |
|---|---|
| No workflow in Actions | Confirm `.github/workflows/weekly-review.yml` exists on `main`. |
| No Run workflow button | Confirm the workflow is on the default branch and you have write access. |
| Python cannot find the script | Move the project files out of any extra parent folder to the repository root. |
| Missing input workbook | Confirm `data/relay_cloud_paid_media_dataset.xlsx` was uploaded. |
| Old-data warning | Refresh the export and its actual extract date; do not change the date merely to hide the warning. |
| Reviewer cannot open the link | Check private-repository access for the exact account they supplied. |
