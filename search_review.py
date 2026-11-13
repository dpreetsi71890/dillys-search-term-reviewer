#!/usr/bin/env python3
"""Read an Excel search export and prepare an approval-only weekly review.

No network calls, ad platform writes, credentials, or runtime AI are used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import load_workbook

VERSION = "1.0.0"
REQUIRED = ["Search Term", "Campaign", "Match Type", "Impressions", "Clicks", "Cost ($)", "Platform Conversions", "CRM Leads"]


class InputError(ValueError):
    """The input cannot safely support recommendations."""


def normalized(value):
    return " ".join(str(value).split()).casefold()


def text_value(value, label):
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{label}: expected nonempty text.")
    return " ".join(value.split())


def number(value, label, integer=False):
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        raise InputError(f"{label}: missing or invalid numeric value; blanks are not zero.")
    try:
        parsed = Decimal(str(value).strip().replace(",", "").replace("$", ""))
    except InvalidOperation as exc:
        raise InputError(f"{label}: invalid numeric value {value!r}.") from exc
    if not parsed.is_finite() or parsed < 0:
        raise InputError(f"{label}: values must be finite and nonnegative.")
    if integer and parsed != parsed.to_integral_value():
        raise InputError(f"{label}: expected a whole-number count.")
    return int(parsed) if integer else parsed


def read_config(path):
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read config {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise InputError("Config must be a JSON object.")
    for key in ("search_sheet", "campaign_sheet", "scope_note"):
        text_value(config.get(key), f"config.{key}")
    for key in ("min_spend", "min_clicks", "stale_after_days"):
        parsed = number(config.get(key), f"config.{key}", integer=key != "min_spend")
        config[key] = float(parsed) if key == "min_spend" else parsed
    if not isinstance(config.get("product_labels"), dict) or not config["product_labels"]:
        raise InputError("config.product_labels must be a nonempty mapping.")
    for label, product in config["product_labels"].items():
        text_value(label, "config.product_labels label")
        text_value(product, "config.product_labels value")
    for key in ("buyer_intent_patterns", "review_patterns", "negative_patterns"):
        if not isinstance(config.get(key), list):
            raise InputError(f"config.{key} must be a list.")
        for item in config[key]:
            if key != "buyer_intent_patterns" and not isinstance(item, dict):
                raise InputError(f"Every config.{key} entry must be an object.")
            pattern = item if key == "buyer_intent_patterns" else item.get("pattern")
            try:
                re.compile(pattern, re.IGNORECASE)
            except (re.error, TypeError) as exc:
                raise InputError(f"Invalid regex in config.{key}: {exc}") from exc
            if key != "buyer_intent_patterns":
                for field in ("id", "reason"):
                    text_value(item.get(field), f"config.{key}.{field}")
                if not isinstance(item.get("products"), list) or not item["products"]:
                    raise InputError(f"config.{key}.products must be a nonempty list.")
    return config


def header_map(sheet, names):
    values = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    headers = [normalized(v) if v is not None else "" for v in values]
    if len([h for h in headers if h]) != len(set(h for h in headers if h)):
        raise InputError(f"{sheet.title}: duplicate column headers.")
    missing = [n for n in names if normalized(n) not in headers]
    if missing:
        raise InputError(f"{sheet.title}: missing columns: {', '.join(missing)}.")
    return {name: headers.index(normalized(name)) for name in names}


def source_date_from_readme(workbook):
    if "README" not in workbook.sheetnames:
        return None
    dates = set()
    for row in workbook["README"].iter_rows(values_only=True):
        for value in row:
            if not isinstance(value, str):
                continue
            match = re.search(r"Data pulled\s+([A-Za-z]+\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})", value, re.IGNORECASE)
            if match:
                for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
                    try:
                        dates.add(datetime.strptime(match.group(1), fmt).date())
                        break
                    except ValueError:
                        continue
    if len(dates) > 1:
        raise InputError("README contains conflicting data-pulled dates; supply --source-as-of after checking the export.")
    return next(iter(dates), None)


def read_dataset(path, config, source_override=None):
    if not path.is_file():
        raise InputError(f"Dataset not found: {path}")
    if path.suffix.lower() != ".xlsx":
        raise InputError("Input must be an .xlsx workbook.")
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise InputError(f"Cannot open workbook: {exc}") from exc
    warnings = []
    try:
        if config["search_sheet"] not in workbook.sheetnames:
            raise InputError(f"Missing worksheet: {config['search_sheet']}")
        source_date = source_override or source_date_from_readme(workbook)
        products = {}
        labels = {normalized(k): v for k, v in config["product_labels"].items()}
        if config["campaign_sheet"] in workbook.sheetnames:
            campaign_sheet = workbook[config["campaign_sheet"]]
            columns = header_map(campaign_sheet, ["Campaign", "Product"])
            for row_number, row in enumerate(campaign_sheet.iter_rows(min_row=2, values_only=True), 2):
                campaign = row[columns["Campaign"]]
                product = row[columns["Product"]]
                if not campaign or not product or normalized(campaign) == "total":
                    continue
                key = normalized(campaign)
                mapped = labels.get(normalized(product), "unknown")
                if key in products and products[key] != mapped:
                    raise InputError(f"Conflicting product mapping for campaign {campaign!r}.")
                products[key] = mapped
        else:
            warnings.append("Campaign product mapping sheet is missing. All campaign products are unknown and will require manual review.")
        sheet = workbook[config["search_sheet"]]
        columns = header_map(sheet, REQUIRED)
        grouped, seen = {}, set()
        source_count = 0
        for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), 2):
            if all(value is None or value == "" for value in row):
                continue
            get = lambda name: row[columns[name]]
            term = text_value(get("Search Term"), f"{sheet.title}!A{row_number}")
            campaign = text_value(get("Campaign"), f"{sheet.title} row {row_number} Campaign")
            match_type = text_value(get("Match Type"), f"{sheet.title} row {row_number} Match Type")
            duplicate_key = (normalized(campaign), normalized(term), normalized(match_type))
            if duplicate_key in seen:
                raise InputError(f"Duplicate campaign/query/match-type key at row {row_number}. Aggregate or remove duplicate export rows before running; they cannot be safely added.")
            seen.add(duplicate_key)
            parsed = {}
            for header, key, integer in (("Impressions", "impressions", True), ("Clicks", "clicks", True), ("Cost ($)", "cost", False), ("Platform Conversions", "platform_conversions", False), ("CRM Leads", "crm_leads", True)):
                parsed[key] = number(get(header), f"{sheet.title} row {row_number} {header}", integer)
            if parsed["clicks"] > parsed["impressions"]:
                raise InputError(f"{sheet.title} row {row_number}: clicks exceed impressions.")
            key = (normalized(campaign), normalized(term))
            if key not in grouped:
                grouped[key] = {"campaign": campaign, "search_term": term, "product": products.get(normalized(campaign), "unknown"), "match_types": [], "source_rows": [], "impressions": 0, "clicks": 0, "cost": Decimal(0), "platform_conversions": Decimal(0), "crm_leads": 0}
            target = grouped[key]
            target["match_types"].append(match_type)
            target["source_rows"].append(row_number)
            for metric, value in parsed.items():
                target[metric] += value
            source_count += 1
        if not grouped:
            raise InputError("Search-term worksheet has no data rows; a blank export is not evidence that waste disappeared.")
        unknown = sorted({row["campaign"] for row in grouped.values() if row["product"] == "unknown"})
        if unknown:
            warnings.append("Unknown product mapping; no negative will be proposed for: " + "; ".join(unknown))
        for row in grouped.values():
            row["cost"] = float(row["cost"].quantize(Decimal("0.01")))
            row["platform_conversions"] = float(row["platform_conversions"])
        return list(grouped.values()), source_date, warnings, source_count
    finally:
        workbook.close()


def classify(row, config):
    """A rule match creates a proposal; it never approves a platform change."""
    term = normalized(row["search_term"])
    sufficient = row["cost"] >= config["min_spend"] and row["clicks"] >= config["min_clicks"]
    if row["crm_leads"] > 0:
        return "KEEP", "crm_leads_present", "This campaign/query produced CRM leads. Keep eligible; this tool does not evaluate downstream lead quality or prove profitability."
    if sufficient:
        for rule in config["review_patterns"]:
            if row["product"] in rule["products"] and re.search(rule["pattern"], term, re.IGNORECASE):
                return "REVIEW", rule["id"], rule["reason"]
    if any(re.search(pattern, term, re.IGNORECASE) for pattern in config["buyer_intent_patterns"]):
        return ("REVIEW" if sufficient else "MONITOR"), "protected_buyer_intent", "Pricing, comparison, developer or business language can indicate relevant buying or evaluation intent. Review the offer, landing page and tracking; do not exclude solely for zero leads."
    if not sufficient:
        return "MONITOR", "below_evidence_threshold", f"Below the review threshold of ${config['min_spend']:,.0f} spend AND {config['min_clicks']} clicks. Gather more evidence; do not infer irrelevance from zero leads."
    if row["product"] == "unknown":
        return "REVIEW", "unknown_product", "Map this campaign to the correct product and inspect intent before proposing any exclusion."
    for rule in config["negative_patterns"]:
        if row["product"] in rule["products"] and re.search(rule["pattern"], term, re.IGNORECASE):
            return "PROPOSE_EXACT_NEGATIVE", rule["id"], rule["reason"]
    return "REVIEW", "unclassified_zero_lead_spend", "Spend and clicks exceed the review thresholds with zero CRM leads, but the intent is not confidently classified. Check intent, tracking and the offer before deciding."


def build_report(rows, config, source_date, as_of, input_path, warnings, source_count):
    warnings = list(warnings)
    age = (as_of - source_date).days if source_date else None
    if age is None:
        freshness = "unknown"
        warnings.append("No source data-pulled date was found. Refresh or verify the export date before approving any change; file modification time is not evidence of freshness.")
    elif age < 0:
        raise InputError("Source date is later than --as-of; use a review date on or after the source date.")
    elif age > config["stale_after_days"]:
        freshness = "stale"
        warnings.append(f"Source is {age} days old as of this review, exceeding the {config['stale_after_days']}-day freshness threshold. Refresh the export before approving changes.")
    else:
        freshness = "current_for_review_date"
    results = []
    for original in rows:
        row = dict(original)
        action, rule, reason = classify(row, config)
        identity = normalized(row["campaign"]) + "|" + normalized(row["search_term"])
        row.update({
            "proposal_id": hashlib.sha256(identity.encode()).hexdigest()[:12],
            "action": action,
            "priority": "P1" if action == "PROPOSE_EXACT_NEGATIVE" else "P2" if action == "REVIEW" else "P3",
            "rule_id": rule,
            "reason": reason,
            "source_reference": f"{config['search_sheet']} rows " + ", ".join(map(str, row["source_rows"])),
            "proposed_negative": row["search_term"] if action == "PROPOSE_EXACT_NEGATIVE" else "",
            "negative_match_type": "Exact" if action == "PROPOSE_EXACT_NEGATIVE" else "",
            "change_scope": "Campaign only" if action == "PROPOSE_EXACT_NEGATIVE" else "",
            "approval_status": "AWAITING_HUMAN_REVIEW" if action in {"PROPOSE_EXACT_NEGATIVE", "REVIEW"} else "NO_CHANGE_PROPOSED",
            "freshness_gate": "REFRESH_REQUIRED" if freshness != "current_for_review_date" else "REVIEW_REQUIRED",
            "next_step": "Verify current export, campaign intent, tracking and existing negatives. If approved, add only this exact term to this campaign; record the reviewer and date. Check qualified volume and cost/MQL over 2–4 weeks; revert if relevant demand is blocked." if action == "PROPOSE_EXACT_NEGATIVE" else "Review intent, attribution and relevant product outcomes; record the decision before changing targeting." if action == "REVIEW" else "Keep monitoring; no platform change is proposed.",
        })
        results.append(row)
    rank = {"PROPOSE_EXACT_NEGATIVE": 0, "REVIEW": 1, "MONITOR": 2, "KEEP": 3}
    results.sort(key=lambda row: (rank[row["action"]], -row["cost"], normalized(row["campaign"]), normalized(row["search_term"])))
    total = round(sum(r["cost"] for r in rows), 2)
    zero = [r for r in results if r["crm_leads"] == 0]
    candidates = [r for r in results if r["action"] == "PROPOSE_EXACT_NEGATIVE"]
    manual = [r for r in results if r["action"] == "REVIEW"]
    return {
        "schema_version": 1,
        "tool_version": VERSION,
        "review_as_of": as_of.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"filename": input_path.name, "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(), "sheet": config["search_sheet"], "source_as_of": source_date.isoformat() if source_date else None, "age_days": age, "freshness": freshness, "source_rows": source_count, "campaign_query_pairs": len(rows), "scope_note": config["scope_note"]},
        "config": config,
        "metrics": {"export_spend": total, "zero_lead_pairs": len(zero), "zero_lead_spend": round(sum(r["cost"] for r in zero), 2), "zero_lead_share_pct": round(sum(r["cost"] for r in zero) / total * 100, 2) if total else 0, "exact_negative_proposals": len(candidates), "proposal_historical_spend": round(sum(r["cost"] for r in candidates), 2), "manual_review_pairs": len(manual), "manual_review_historical_spend": round(sum(r["cost"] for r in manual), 2), "actions": dict(Counter(r["action"] for r in results))},
        "automation_boundary": {"automatic": ["Read and validate the workbook", "Recalculate every query using current values", "Classify configured intent patterns", "Create and prioritize draft proposals with evidence", "Save reports and flag stale data"], "human_required": ["Verify intent, tracking and source freshness", "Approve or reject each exact negative", "Apply changes to the ad platform and log reviewer/date", "Approve any budget or bid change", "Check qualified-volume impact and reverse harmful exclusions"], "platform_changes_applied": 0},
        "warnings": warnings,
        "limitations": ["Historical spend attached to a flagged query is an exposure measure, not forecast or guaranteed savings.", "A rolling snapshot is rerun weekly; its rows are not weekly cohorts. Do not sum reports from overlapping exports.", "CRM leads do not establish MQL quality, incremental demand, pipeline or profitability.", "Intent patterns are editable assumptions and can misclassify new language. A person must approve every targeting change.", "The code does not read or write existing platform negative lists; an approver must check for duplicates and conflicts.", "Negative proposals are exact and campaign-specific; never turn a full query into an account-wide broad exclusion."],
        "results": results,
    }


def markdown_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def summary_markdown(report):
    m, source = report["metrics"], report["source"]
    lines = ["# Dilly's Search Term Reviewer", "", "Relay Cloud paid search / weekly review", "", f"Review date: {report['review_as_of']}. Source data pulled: {source['source_as_of'] or 'unknown'}. Freshness: {source['freshness']}.", "", f"The selected export contains {source['campaign_query_pairs']} campaign/query pairs and ${m['export_spend']:,.2f} in historical spend. {m['zero_lead_pairs']} pairs produced zero CRM leads, representing ${m['zero_lead_spend']:,.2f} ({m['zero_lead_share_pct']:.1f}%) of this export.", "", f"I propose {m['exact_negative_proposals']} campaign-level exact negatives for human review. They account for ${m['proposal_historical_spend']:,.2f} of historical spend. Another {m['manual_review_pairs']} pairs (${m['manual_review_historical_spend']:,.2f}) need an intent or tracking review. These amounts are not projected savings. No targeting, bids or budgets were changed.", "", "## Scope and freshness", "", source["scope_note"], ""]
    lines.extend(f"- {warning}" for warning in report["warnings"])
    if not report["warnings"]:
        lines.append("The source date is within the configured freshness limit for this review date. Human approval is still required.")
    lines += ["", "## Proposed changes", "", "| Priority | Campaign | Search term | Historical spend | Clicks | CRM leads | Proposed action |", "|---|---|---|---:|---:|---:|---|"]
    proposed = [r for r in report["results"] if r["action"] in {"PROPOSE_EXACT_NEGATIVE", "REVIEW"}]
    for row in proposed:
        action = "Exact negative after approval" if row["action"] == "PROPOSE_EXACT_NEGATIVE" else "Review before changing"
        lines.append("| " + " | ".join(markdown_cell(v) for v in (row["priority"], row["campaign"], row["search_term"], f"${row['cost']:,.2f}", row["clicks"], row["crm_leads"], action)) + " |")
    if not proposed:
        lines.append("| — | — | No changes proposed | — | — | — | Continue monitoring |")
    lines += ["", "## Why each proposal was raised", ""]
    for row in proposed:
        lines.append(f"- **{markdown_cell(row['search_term'])}** in {markdown_cell(row['campaign'])}: {row['reason']} Evidence: {row['source_reference']}. Approval: {row['approval_status']}.")
    lines += ["", "## Approval and follow up", "", "The automation reads, checks, classifies and writes reports on its own. A person approves each exclusion, checks existing negatives, applies it in the ad platform and records the decision. Stale or undated exports must be refreshed before approval. Review cost per MQL and qualified volume over 2–4 weeks; reverse a negative if it blocks verified relevant demand. Avoid automatic broad negatives or automatic budget changes.", "", "Queries with any CRM leads stay eligible. Pricing and comparison intent remains protected from automatic negative proposals. Ambiguous free API and free business-receptionist queries require an intent review.", "", "## Files", "", "- proposals.csv: review queue with metrics, rules, source rows and approval status.", "- report.json: complete results for every query, configuration, source fingerprint and limitations.", "- report.html: readable report that opens in a browser without a server.", "", "## Limitations", ""]
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    m, source = report["metrics"], report["source"]
    labels = {"PROPOSE_EXACT_NEGATIVE": "Propose an exclusion", "REVIEW": "Take a closer look", "KEEP": "Keep eligible", "MONITOR": "Watch for now"}
    needs_refresh = source["freshness"] != "current_for_review_date"
    entries = []
    for index, row in enumerate(report["results"], 1):
        actionable = row["action"] in {"PROPOSE_EXACT_NEGATIVE", "REVIEW"}
        identity = esc(row["proposal_id"])
        approval_note = "Refresh the source before approving." if needs_refresh else "A recorded approval does not apply a change."
        form = ""
        if actionable:
            disabled = " disabled" if needs_refresh else ""
            form = f'''<details class="decision-panel"><summary>Record a decision <span>Optional review notes</span></summary><div class="decision-grid"><label for="decision-{identity}">Decision<select id="decision-{identity}" data-field="decision"><option value="pending">Pending review</option><option value="approved"{disabled}>Approve proposal</option><option value="rejected">Reject proposal</option><option value="investigate">Investigate further</option></select></label><label for="reviewer-{identity}">Reviewer<input id="reviewer-{identity}" data-field="reviewer" placeholder="Your name" autocomplete="off"></label><label class="notes-label" for="notes-{identity}">Notes<textarea id="notes-{identity}" data-field="notes" rows="2" placeholder="What did you check? What should happen next?"></textarea></label></div><p class="form-foot">{esc(approval_note)} Notes stay in this page until you download the review CSV.</p></details>'''
        action_note = "Human approval required · exact match · this campaign only" if row["action"] == "PROPOSE_EXACT_NEGATIVE" else "Human judgment required · no exclusion proposed" if row["action"] == "REVIEW" else "No change proposed"
        entries.append(f'''<article class="entry" data-id="{identity}" data-action="{esc(row['action'])}" data-search="{esc(row['search_term'] + ' ' + row['campaign'])}"><div class="entry-number">{index:02d}</div><div class="entry-content"><div class="entry-top"><div><div class="campaign">{esc(row['campaign'])}</div><h3>{esc(row['search_term'])}</h3></div><span class="action-tag {'review-tag' if actionable else 'keep-tag'}">{esc(labels[row['action']])}</span></div><div class="entry-facts"><div><span>Historical spend</span><strong>${row['cost']:,.2f}</strong></div><div><span>Clicks</span><strong>{row['clicks']:,}</strong></div><div><span>CRM leads</span><strong>{row['crm_leads']:,}</strong></div><p>{esc(action_note)}</p></div><p class="reason">{esc(row['reason'])}</p><details class="evidence"><summary>Evidence and next step</summary><div><p><strong>Source</strong> {esc(row['source_reference'])}</p><p><strong>Rule</strong> {esc(row['rule_id'])} · <strong>Status</strong> {esc(row['approval_status'])}</p><p>{esc(row['next_step'])}</p></div></details>{form}</div></article>''')
    payload = {"rows": report["results"], "source_sha256": source["sha256"], "source_as_of": source["source_as_of"], "review_as_of": report["review_as_of"], "stale_after_days": report["config"]["stale_after_days"], "config_sha256": hashlib.sha256(json.dumps(report["config"], sort_keys=True).encode()).hexdigest()}
    encoded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    warnings = "".join(f"<li>{esc(w)}</li>" for w in report["warnings"])
    freshness = "Refresh needed" if needs_refresh else "Source date checked"
    values = {
        "ENTRIES": "".join(entries), "PAYLOAD": encoded, "REVIEW_DATE": esc(report["review_as_of"]), "SOURCE_DATE": esc(source["source_as_of"] or "Unknown"), "FRESHNESS": freshness,
        "WARNINGS": f'<div class="freshness-note"><strong>Before you approve</strong><ul>{warnings}</ul></div>' if warnings else "",
        "ZERO_SPEND": f"${m['zero_lead_spend']:,.0f}", "EXPORT_SPEND": f"${m['export_spend']:,.0f}", "ZERO_SHARE": f"{m['zero_lead_share_pct']:.1f}%", "ZERO_PAIRS": str(m["zero_lead_pairs"]),
        "EXCLUSIONS": str(m["exact_negative_proposals"]), "REVIEWS": str(m["manual_review_pairs"]), "KEPT": str(m["actions"].get("KEEP", 0)), "MONITORED": str(m["actions"].get("MONITOR", 0)), "TOTAL": str(source["campaign_query_pairs"]), "DECISIONS": str(m["exact_negative_proposals"] + m["manual_review_pairs"]), "PROPOSAL_SPEND": f"${m['proposal_historical_spend']:,.0f}",
        "SCOPE": esc(source["scope_note"]), "THRESHOLD": f"${report['config']['min_spend']:,.0f}", "CLICKS": str(report["config"]["min_clicks"]), "SOURCE_HASH": esc(source["sha256"]),
    }
    template = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dilly's Search Term Reviewer</title>
<style>
:root{--paper:#f6f2e8;--ink:#1e342d;--green:#193d33;--muted:#5e6a60;--line:#d8d9ca;--orange:#a74620;--peach:#f7e5d6;--white:#fffdf7}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,input,select,textarea{font:inherit}button,a,input,select,textarea,summary{outline-offset:4px}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #b64e26}button{cursor:pointer}button:disabled{cursor:not-allowed}a{color:inherit}.masthead{background:var(--green);color:var(--paper);padding:36px max(6vw,24px) 28px}.masthead-inner,.page{max-width:1360px;margin:auto}.topline{display:flex;justify-content:space-between;align-items:center;gap:20px}.brand-lockup{display:flex;align-items:center;gap:14px}.monogram{position:relative;display:grid;place-items:center;width:46px;height:46px;border:1px solid #9bb3a1;border-radius:50%;font:italic 37px Georgia,serif}.monogram:after{content:"";position:absolute;width:7px;height:7px;border-radius:50%;background:#e5a06c;right:-2px;bottom:3px}.eyebrow,.date-strip,.campaign,.entry-number,.fact-label,.entry-facts strong,.entry-facts span,.count,.footer-meta{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}.eyebrow{font-size:11px;letter-spacing:.13em;text-transform:uppercase}.top-note{font-size:12px;color:#c2d3c5;margin:0}h1{font:normal clamp(36px,4.4vw,64px)/1.08 Georgia,"Times New Roman",serif;letter-spacing:-.04em;margin:36px 0 30px}h1 em{font-weight:normal;color:#efbb91}h1 span{display:block}.date-strip{display:flex;flex-wrap:wrap;gap:18px 38px;font-size:11px;letter-spacing:.025em;border-top:1px solid #486255;padding-top:20px;color:#d9e1d5}.date-strip b{color:#fffdf7;font-weight:500}.date-strip .status{margin-left:auto;color:#f2c49f}.status:before{content:"";display:inline-block;width:6px;height:6px;margin-right:9px;background:#eab588;border-radius:50%}.page{padding:0 32px}.overview{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:70px;padding:45px 0 36px;border-bottom:1px solid var(--line)}.section-kicker{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.14em;color:var(--orange);margin:0 0 12px}.exposure{font:normal clamp(48px,5.3vw,74px)/1 Georgia,serif;letter-spacing:-.055em;margin:7px 0 14px}.exposure span{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:normal;display:inline-block;max-width:210px;margin-left:20px;color:var(--muted)}.overview-lead{max-width:650px;font-size:16px;margin:14px 0}.overview-lead strong{font-weight:650}.scope{color:var(--muted);font-size:12px;max-width:660px;margin:16px 0 0}.line-stats{display:flex;gap:23px;margin:26px 0 0;flex-wrap:wrap}.line-stats div{border-left:2px solid #bd6b44;padding-left:12px}.line-stats strong{font:normal 27px Georgia,serif;display:block;line-height:1.1}.line-stats span{font-size:11px;color:var(--muted)}.rules{padding-left:28px;border-left:1px solid var(--line)}h2{font:normal 27px/1.2 Georgia,serif;letter-spacing:-.025em;margin:0 0 18px}.rules ol{padding-left:19px;margin:0}.rules li{padding-left:5px;margin-bottom:12px;font-size:12px;line-height:1.6}.rules li::marker{font-family:ui-monospace,monospace;color:var(--orange)}.rules strong{display:block;font-weight:650;color:var(--ink)}.rules .quiet{color:var(--muted)}.freshness-note{background:var(--peach);padding:15px 20px;border-left:3px solid var(--orange);font-size:13px;margin:26px 0 0}.freshness-note ul{margin:5px 0 0;padding-left:18px}.workbench{padding:33px 0 25px}.workbench-top{display:flex;align-items:flex-start;justify-content:space-between;gap:25px}.workbench h2{font-size:32px;margin:0 0 5px}.workbench p{font-size:13px;color:var(--muted);margin:0}.export-button{background:var(--green);border:1px solid var(--green);color:var(--paper);padding:11px 17px;font-size:12px;white-space:nowrap;border-radius:3px}.export-button:hover{background:#285242}.download-note{display:block;font-size:10px;max-width:215px;text-align:right;color:var(--muted);margin-top:7px}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:24px;flex-wrap:wrap}.filters{display:flex;gap:6px;flex-wrap:wrap}.filter{border:1px solid var(--line);padding:8px 12px;border-radius:3px;background:transparent;color:var(--muted);font-size:11px}.filter .count{margin-left:6px;font-size:10px;opacity:.8}.filter[aria-pressed="true"]{background:var(--green);border-color:var(--green);color:var(--paper)}.filter:hover{border-color:var(--green)}.search-wrap{min-width:230px;flex:1;max-width:310px}.search-wrap input{width:100%;border:0;border-bottom:1px solid #93a08e;padding:8px 3px;background:transparent;font-size:12px;border-radius:0;color:var(--ink)}.sr-only{position:absolute;width:1px;height:1px;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}.results-status{font-size:11px;color:var(--muted);margin-top:14px!important}.entry{display:grid;grid-template-columns:36px minmax(0,1fr);gap:18px;padding:28px 0;border-top:1px solid var(--line)}.entry[hidden]{display:none}.entry-number{font-size:11px;color:#849183;padding-top:4px}.entry-top{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.campaign{font-size:10px;letter-spacing:.03em;color:var(--muted);overflow-wrap:anywhere}.entry h3{font:normal 28px/1.22 Georgia,serif;margin:4px 0 15px;letter-spacing:-.025em;overflow-wrap:anywhere}.action-tag{font-size:10px;padding:5px 9px;border-radius:3px;white-space:nowrap;margin-top:2px}.review-tag{background:var(--peach);color:#8a3c1b}.keep-tag{background:#e5ebdf;color:#345b43}.entry-facts{display:flex;gap:30px;align-items:flex-end;flex-wrap:wrap}.entry-facts div{display:flex;flex-direction:column;gap:2px}.entry-facts span{font-size:9px;letter-spacing:.02em;color:var(--muted);text-transform:uppercase}.entry-facts strong{font-size:13px;font-weight:500}.entry-facts p{font-size:11px;margin:0 0 1px auto;color:var(--muted)}.reason{font-size:13px;line-height:1.65;max-width:920px;margin:16px 0 10px}.evidence{font-size:11px;color:var(--muted)}summary{cursor:pointer;list-style-position:inside}.evidence summary{color:var(--green);font-weight:550}.evidence div{padding:7px 15px;border-left:2px solid var(--line);margin-top:8px}.evidence p{margin:5px 0;overflow-wrap:anywhere}.decision-panel{margin-top:14px;border:1px solid var(--line);background:#f0eee3;border-radius:3px}.decision-panel>summary{padding:10px 13px;font-size:11px;font-weight:600}.decision-panel>summary span{margin-left:13px;color:var(--muted);font-size:10px;font-weight:400}.decision-grid{display:grid;grid-template-columns:190px 1fr;gap:12px;padding:5px 13px 0}.decision-grid label{font-size:10px;font-weight:600}.decision-grid input,.decision-grid select,.decision-grid textarea{display:block;width:100%;margin-top:5px;padding:8px 10px;border:1px solid #b8c1b2;border-radius:2px;background:var(--white);font-size:12px;color:var(--ink)}.decision-grid textarea{resize:vertical;min-height:58px}.notes-label{grid-column:1/-1}.form-foot{font-size:10px;color:var(--muted);padding:0 13px 11px;margin:8px 0 0}.empty{padding:40px 0;text-align:center;border-top:1px solid var(--line);font-family:Georgia,serif;font-size:21px}.footer{border-top:1px solid var(--line);padding:28px 0 40px;margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:50px}.footer p{font-size:11px;color:var(--muted);margin:0 0 9px}.footer strong{font-weight:600;color:var(--ink)}.footer-meta{font-size:9px!important;overflow-wrap:anywhere}.download-status{min-height:20px;color:var(--green)!important;font-size:11px!important;text-align:right;margin:7px 0 0!important}.noscript{background:var(--peach);padding:18px;font-size:13px}body.has-js .entry[data-action="KEEP"],body.has-js .entry[data-action="MONITOR"]{display:none}body.has-js .entry.shown{display:grid}body.has-js .entry[hidden]{display:none}@media(max-width:900px){.overview{grid-template-columns:1fr;gap:28px}.rules{padding:22px 0 0;border-left:0;border-top:1px solid var(--line)}.rules ol{display:grid;grid-template-columns:1fr 1fr;gap:10px 35px}.rules li{margin-bottom:0}.entry-facts p{margin-left:0}.masthead{padding-top:24px}.top-note{display:none}.date-strip .status{margin-left:0}.page{padding:0 24px}.overview{padding-top:32px}.exposure span{max-width:260px}.toolbar{align-items:stretch}.search-wrap{max-width:none}.footer{gap:25px}}@media(max-width:560px){.masthead{padding:22px 20px}.page{padding:0 20px}.eyebrow{font-size:9px}.monogram{width:39px;height:39px;font-size:30px}h1{margin:26px 0}.date-strip{gap:8px 22px;font-size:9px}.exposure span{display:block;margin:14px 0 0;max-width:none}.line-stats{gap:18px}.rules ol{display:block}.rules li{margin-bottom:12px}.workbench-top{display:block}.export-area{margin-top:17px}.download-note{text-align:left;max-width:none}.download-status{text-align:left!important}.filters{gap:5px}.filter{padding:7px 9px;font-size:10px}.search-wrap{min-width:100%;max-width:100%}.entry{grid-template-columns:22px minmax(0,1fr);gap:10px;padding:22px 0}.entry-top{display:block}.entry h3{font-size:26px;margin-bottom:10px}.action-tag{display:inline-block;margin:0 0 12px}.entry-facts{gap:18px}.entry-facts p{flex-basis:100%}.decision-grid{grid-template-columns:1fr}.notes-label{grid-column:auto}.decision-panel>summary span{display:block;margin-left:14px}.footer{grid-template-columns:1fr;gap:12px}.workbench h2{font-size:28px}}@media print{.masthead{background:white;color:black;border-bottom:2px solid black}.masthead h1 em,.date-strip,.date-strip b{color:black}.toolbar,.export-area,.decision-panel{display:none}.entry{break-inside:avoid}.page{max-width:none;padding:0}.overview{padding-top:20px}.entry[hidden],body.has-js .entry[data-action="KEEP"],body.has-js .entry[data-action="MONITOR"]{display:grid!important}.footer{break-inside:avoid}}
</style></head><body>
<header class="masthead"><div class="masthead-inner"><div class="topline"><div class="brand-lockup"><div class="monogram" aria-hidden="true">D</div><div class="eyebrow">Relay Cloud paid search<br>Weekly review</div></div><p class="top-note">A working notebook for search decisions.</p></div><h1><em>Dilly's</em><span>Search Term Reviewer</span></h1><div class="date-strip"><span>REVIEW <b>@@REVIEW_DATE@@</b></span><span>SOURCE <b>@@SOURCE_DATE@@</b></span><span class="status" id="freshness-status">@@FRESHNESS@@</span></div></div></header>
<main class="page"><section class="overview" aria-labelledby="overview-title"><div><p class="section-kicker" id="overview-title">Where the spend needs a second look</p><div class="exposure">@@ZERO_SPEND@@<span>spent on @@ZERO_PAIRS@@ searches with no recorded CRM leads</span></div><p class="overview-lead">That is <strong>@@ZERO_SHARE@@ of the @@EXPORT_SPEND@@ selected export</strong>. The reviewer proposes @@EXCLUSIONS@@ exact exclusions and leaves @@REVIEWS@@ searches open for a closer look.</p><div class="line-stats"><div><strong>@@EXCLUSIONS@@</strong><span>Proposed exclusions</span></div><div><strong>@@REVIEWS@@</strong><span>Closer looks</span></div><div><strong>@@KEPT@@</strong><span>Kept eligible</span></div></div><p class="scope">The exclusion proposals account for @@PROPOSAL_SPEND@@ in historical spend. This is exposure to review, not a savings forecast. @@SCOPE@@</p></div><aside class="rules"><h2>The rules I care about</h2><ol><li><strong>Give buying intent a chance.</strong><span class="quiet">Keep converting searches eligible. Pricing, comparisons and developer or business language get a review before any exclusion.</span></li><li><strong>Ask for enough evidence.</strong><span class="quiet">Zero CRM leads, at least @@THRESHOLD@@ in spend and @@CLICKS@@ clicks. Ambiguous intent goes to a person.</span></li><li><strong>Keep the final call human.</strong><span class="quiet">Verify fresh data, approve an exact query for one campaign, and check qualified demand after the change.</span></li></ol></aside></section>
<p class="scope" id="snapshot-note">This report is a snapshot dated @@REVIEW_DATE@@. Opening the page does not refresh the data.</p>@@WARNINGS@@<noscript><p class="noscript">JavaScript is off. Every query is shown below. Use proposals.csv to record decisions; filters and the download button require JavaScript.</p></noscript>
<section class="workbench" aria-labelledby="queue-title"><div class="workbench-top"><div><p class="section-kicker">The working list</p><h2 id="queue-title">Read the reason. Make the call.</h2><p>Ordered by proposed action, then historical spend. No ad-platform changes have been applied.</p></div><div class="export-area"><button class="export-button" id="download" type="button">Download review CSV <span aria-hidden="true">↓</span></button><span class="download-note">Notes are not autosaved. Download before closing or refreshing this page.</span><p id="download-status" class="download-status" role="status"></p></div></div><div class="toolbar"><div class="filters" role="group" aria-label="Filter search terms"><button class="filter" type="button" data-filter="decision" aria-pressed="true">Decision queue <span class="count">@@DECISIONS@@</span></button><button class="filter" type="button" data-filter="PROPOSE_EXACT_NEGATIVE" aria-pressed="false">Exclusions <span class="count">@@EXCLUSIONS@@</span></button><button class="filter" type="button" data-filter="REVIEW" aria-pressed="false">Closer look <span class="count">@@REVIEWS@@</span></button><button class="filter" type="button" data-filter="KEEP" aria-pressed="false">Kept eligible <span class="count">@@KEPT@@</span></button><button class="filter" type="button" data-filter="all" aria-pressed="false">All terms <span class="count">@@TOTAL@@</span></button></div><label class="search-wrap"><span class="sr-only">Search query or campaign</span><input type="search" id="query-search" placeholder="Search a query or campaign…" autocomplete="off"></label></div><p class="results-status" id="results-status" role="status">All @@TOTAL@@ queries are available below.</p></section>
<section id="entries" aria-label="Search term reviews">@@ENTRIES@@</section><p class="empty" id="empty" hidden>No matching searches. Try another term or filter.</p>
<footer class="footer"><div><p><strong>After the decision</strong><br>Check existing negatives before applying an approved change. Review qualified volume and cost per MQL over 2–4 weeks. Reverse an exclusion that blocks relevant demand.</p><p>“Keep eligible” means the query produced a CRM lead; it does not establish quality, incremental demand or profitability.</p></div><div><p><strong>The paper trail</strong><br>The downloaded CSV records your decisions. The original proposals.csv and report.json remain unchanged. Use report.json for complete rules and limitations.</p><p class="footer-meta">SOURCE SHA256<br>@@SOURCE_HASH@@</p></div></footer></main>
<script type="application/json" id="review-data">@@PAYLOAD@@</script>
<script>
"use strict";
(() => {
  const payload = JSON.parse(document.getElementById("review-data").textContent);
  const entries = Array.from(document.querySelectorAll(".entry"));
  const buttons = Array.from(document.querySelectorAll(".filter"));
  const search = document.getElementById("query-search");
  const status = document.getElementById("results-status");
  const now = new Date();
  const today = now.toISOString().slice(0, 10);
  const sourceUTC = payload.source_as_of ? Date.parse(payload.source_as_of + "T00:00:00Z") : NaN;
  function needsSourceRefresh() {
    const checkedAt = new Date();
    const checkedDayUTC = Date.UTC(checkedAt.getUTCFullYear(), checkedAt.getUTCMonth(), checkedAt.getUTCDate());
    const ageDays = Math.floor((checkedDayUTC - sourceUTC) / 86400000);
    return !Number.isFinite(ageDays) || ageDays < 0 || ageDays > payload.stale_after_days;
  }
  const refreshRequiredNow = needsSourceRefresh();
  if (payload.review_as_of !== today) {
    document.getElementById("snapshot-note").textContent = "Historical review dated " + payload.review_as_of + ". Opening this page does not refresh its data. Current freshness is checked against " + today + " (UTC).";
  }
  if (refreshRequiredNow) {
    document.getElementById("freshness-status").textContent = "Refresh needed now";
    document.querySelectorAll('option[value="approved"]').forEach(option => { option.disabled = true; });
    document.querySelectorAll(".form-foot").forEach(note => { note.textContent = "Refresh the source before approving. Notes stay in this page until you download the review CSV."; });
  }
  let activeFilter = "decision";
  const proposed = action => action === "PROPOSE_EXACT_NEGATIVE" || action === "REVIEW";
  function applyFilter() {
    const needle = search.value.trim().toLocaleLowerCase();
    let count = 0;
    entries.forEach(entry => {
      const action = entry.dataset.action;
      const category = activeFilter === "all" || (activeFilter === "decision" ? proposed(action) : action === activeFilter);
      const show = category && entry.dataset.search.toLocaleLowerCase().includes(needle);
      entry.hidden = !show;
      entry.classList.toggle("shown", show);
      if (show) count += 1;
    });
    buttons.forEach(button => button.setAttribute("aria-pressed", String(button.dataset.filter === activeFilter)));
    status.textContent = count + (count === 1 ? " search shown" : " searches shown") + " · filters do not change the export";
    document.getElementById("empty").hidden = count !== 0;
  }
  document.body.classList.add("has-js");
  buttons.forEach(button => button.addEventListener("click", () => { activeFilter = button.dataset.filter; applyFilter(); }));
  search.addEventListener("input", applyFilter);
  document.querySelectorAll('[data-field="reviewer"]').forEach(input => input.addEventListener("input", () => input.setCustomValidity("")));
  const csvCell = value => {
    let text = value == null ? "" : String(value);
    if (/^\s*[=+\-@]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  };
  document.getElementById("download").addEventListener("click", () => {
    const refreshRequiredAtExport = needsSourceRefresh();
    const rows = [];
    for (const row of payload.rows.filter(row => proposed(row.action))) {
      const entry = document.querySelector('[data-id="' + row.proposal_id + '"]');
      const decision = entry.querySelector('[data-field="decision"]').value;
      const reviewerField = entry.querySelector('[data-field="reviewer"]');
      const reviewer = reviewerField.value.trim();
      if (decision === "approved" && refreshRequiredAtExport) {
        document.getElementById("download-status").textContent = "Refresh the source and rerun the reviewer before recording an approval.";
        return;
      }
      if (decision === "approved" && !reviewer) {
        entry.hidden = false;
        entry.classList.add("shown");
        entry.querySelector(".decision-panel").open = true;
        reviewerField.setCustomValidity("Add your name before exporting an approval.");
        reviewerField.reportValidity();
        document.getElementById("download-status").textContent = "Add a reviewer name for each approval, then download again.";
        return;
      }
      rows.push({...row, decision, reviewer, reviewed_on: decision === "pending" ? "" : new Date().toISOString(), notes: entry.querySelector('[data-field="notes"]').value, freshness_gate: refreshRequiredAtExport ? "REFRESH_REQUIRED" : row.freshness_gate, source_sha256: payload.source_sha256, config_sha256: payload.config_sha256, source_as_of: payload.source_as_of, review_as_of: payload.review_as_of, platform_changes_applied: 0});
    }
    const fields = ["proposal_id","priority","campaign","search_term","product","cost","clicks","crm_leads","platform_conversions","action","proposed_negative","negative_match_type","change_scope","rule_id","reason","source_reference","approval_status","freshness_gate","next_step","decision","reviewer","reviewed_on","notes","source_as_of","review_as_of","source_sha256","config_sha256","platform_changes_applied"];
    const csv = "\ufeff" + [fields.map(csvCell).join(","), ...rows.map(row => fields.map(field => csvCell(row[field])).join(","))].join("\r\n") + "\r\n";
    const url = URL.createObjectURL(new Blob([csv], {type:"text/csv;charset=utf-8;"}));
    const link = document.createElement("a");
    link.href = url;
    link.download = "dilly-search-review-" + payload.review_as_of + ".csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    document.getElementById("download-status").textContent = "Review CSV downloaded. No ad-platform changes were applied.";
  });
  applyFilter();
})();
</script></body></html>'''
    return re.sub(r"@@([A-Z_]+)@@", lambda match: values[match.group(1)], template)


def write_outputs(report, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "summary.md").write_text(summary_markdown(report), encoding="utf-8")
    (output / "report.html").write_text(render_html(report), encoding="utf-8")
    fields = ["proposal_id", "priority", "campaign", "search_term", "product", "cost", "clicks", "crm_leads", "platform_conversions", "action", "proposed_negative", "negative_match_type", "change_scope", "rule_id", "reason", "source_reference", "approval_status", "freshness_gate", "next_step", "decision", "reviewer", "reviewed_on", "notes"]
    with (output / "proposals.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["results"]:
            if row["action"] in {"PROPOSE_EXACT_NEGATIVE", "REVIEW"}:
                writer.writerow({key: csv_safe(row.get(key, "")) for key in fields})


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD.") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Path to the .xlsx dataset")
    parser.add_argument("--output", type=Path, default=Path("output"), help="Directory for four generated reports")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--as-of", type=iso_date, default=datetime.now(timezone.utc).date(), help="Review date, default today in UTC; historical demo uses 2026-10-01")
    parser.add_argument("--source-as-of", type=iso_date, help="Actual export date, if not present in README; do not use today's date for an old export")
    args = parser.parse_args(argv)
    try:
        config = read_config(args.config)
        rows, source_date, warnings, source_count = read_dataset(args.input, config, args.source_as_of)
        report = build_report(rows, config, source_date, args.as_of, args.input, warnings, source_count)
        write_outputs(report, args.output)
    except (InputError, OSError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Reviewed {len(rows)} campaign/query pairs. Proposed {report['metrics']['exact_negative_proposals']} exact negatives; {report['metrics']['manual_review_pairs']} manual reviews. Applied 0 platform changes.")
    print(f"Reports: {args.output.resolve()}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
