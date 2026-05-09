"""Build a structured Markdown financial briefing."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path.cwd()
TEMPLATE_PATH = SKILL_ROOT / "templates" / "daily_report_template.md"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports"


FORM_EXPLANATIONS = {
    "10-K": "Annual report with audited financial statements and broad business disclosures.",
    "10-Q": "Quarterly report with unaudited financial statements and interim disclosures.",
    "8-K": "Current report for material events disclosed between periodic reports.",
    "4": "Insider ownership transaction report.",
    "3": "Initial insider ownership report.",
    "5": "Annual insider ownership transaction report.",
    "S-1": "Registration statement for securities offerings.",
}


SIGNAL_BY_CATEGORY = {
    "annual_report": "Annual reports often contain updated risk factors, audited financials, and management discussion.",
    "quarterly_report": "Quarterly reports often contain interim financial updates and recent operating disclosures.",
    "current_report": "Current reports can indicate a material company event that may merit reading the filing.",
    "ownership": "Ownership forms report insider or beneficial owner transactions.",
    "registration": "Registration filings can relate to securities offerings or registration activity.",
    "other": "Review the filing type and document title for context.",
}


def render_list(items: list[str], empty_message: str = "No reportable items available.") -> str:
    """Render Markdown bullets with a fallback."""
    if not items:
        return f"- {empty_message}"
    return "\n".join(f"- {item}" for item in items)


def render_filings(items: list[dict[str, Any]]) -> str:
    """Render the latest SEC filings as a Markdown table."""
    if not items:
        return "No reportable SEC filings available."

    rows = [
        "| Filing Date | Form | Category | Accession Number | Primary Document | URL |",
        "|---:|---|---|---|---|---|",
    ]
    for item in items:
        rows.append(
            "| {filing_date} | {form} | {category} | {accession_number} | {primary_document} | {url} |".format(
                filing_date=item.get("filing_date"),
                form=item.get("form"),
                category=item.get("category"),
                accession_number=item.get("accession_number"),
                primary_document=item.get("primary_document"),
                url=item.get("url"),
            )
        )
    return "\n".join(rows)


def render_form_explanations(items: list[dict[str, Any]]) -> str:
    """Explain filing forms found in the current report."""
    forms = sorted({str(item.get("form")) for item in items if item.get("form")})
    explanations = []
    for form in forms:
        base_form = form.replace("/A", "")
        explanation = FORM_EXPLANATIONS.get(base_form, "SEC filing type. Read the source document for details.")
        explanations.append(f"{form}: {explanation}")
    return render_list(explanations)


def render_risk_signals(items: list[dict[str, Any]]) -> str:
    """Render neutral disclosure signals without giving investment advice."""
    categories = sorted({str(item.get("category")) for item in items if item.get("category")})
    signals = [SIGNAL_BY_CATEGORY.get(category, SIGNAL_BY_CATEGORY["other"]) for category in categories]
    return render_list(signals, "No disclosure signals found in the fetched filing metadata.")


def render_sources(items: list[dict[str, Any]]) -> str:
    """Render source metadata for traceability."""
    if not items:
        return "No source items collected."

    rows = [
        "| Source | Filing Date | Retrieved Time | URL |",
        "|---|---:|---:|---|",
    ]
    for item in items:
        rows.append(
            "| {source} | {filing_date} | {retrieved_time} | {url} |".format(
                source=item.get("source"),
                filing_date=item.get("filing_date"),
                retrieved_time=item.get("retrieved_time"),
                url=item.get("url"),
            )
        )
    return "\n".join(rows)


def render_macro_summary(macro_data: list[dict[str, Any]]) -> str:
    """Render latest values for each FRED macro series."""
    if not macro_data:
        return "- No FRED macro data available."

    frame = pd.DataFrame(macro_data)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["date", "value"]).sort_values("date")
    if frame.empty:
        return "- No numeric FRED macro observations available."

    lines: list[str] = []
    for series_id, series_frame in frame.groupby("series_id"):
        latest = series_frame.iloc[-1]
        lines.append(
            "{series_id}: {series_name}, latest value {value:.2f} on {date}".format(
                series_id=series_id,
                series_name=latest["series_name"],
                value=latest["value"],
                date=latest["date"].date().isoformat(),
            )
        )
    return render_list(lines)


def render_macro_charts(chart_paths: list[Path]) -> str:
    """Render chart image links relative to the report file."""
    if not chart_paths:
        return "- No macro charts generated."
    return "\n".join(f"![{path.stem}]({path})" for path in chart_paths)


def render_source_log(sec_items: list[dict[str, Any]], macro_data: list[dict[str, Any]]) -> str:
    """Render source metadata for both SEC and FRED."""
    rows = [
        "| Source | Item | Published / Filing Date | Retrieved Time | URL |",
        "|---|---|---:|---:|---|",
    ]
    for item in sec_items:
        rows.append(
            "| SEC EDGAR | {form} {accession_number} | {filing_date} | {retrieved_time} | {url} |".format(
                form=item.get("form"),
                accession_number=item.get("accession_number"),
                filing_date=item.get("filing_date"),
                retrieved_time=item.get("retrieved_time"),
                url=item.get("url"),
            )
        )
    for item in macro_data:
        rows.append(
            "| FRED | {series_id} | {published_time} | {retrieved_time} | {url} |".format(
                series_id=item.get("series_id"),
                published_time=item.get("published_time"),
                retrieved_time=item.get("retrieved_time"),
                url=item.get("url"),
            )
        )

    if len(rows) == 2:
        return "No source items collected."
    return "\n".join(rows)


def render_limitations(limitations: list[str]) -> str:
    """Render limitations for the report."""
    base_limitations = [
        "This MVP uses only public SEC EDGAR and FRED data.",
        "SEC EDGAR requires SEC_USER_AGENT. FRED requires FRED_API_KEY for macro data.",
        "No private data, paywalled data, or login-gated content is used.",
        "This report is informational and does not contain investment recommendations.",
    ]
    return render_list([*base_limitations, *limitations])


def build_report(
    items: list[dict[str, Any]],
    macro_data: list[dict[str, Any]],
    chart_paths: list[Path],
    limitations: list[str] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Build the Markdown financial briefing and return its path."""
    logging.info("Building Markdown financial briefing report")
    output_dir = output_dir or DEFAULT_REPORT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    limitations = limitations or []

    report_date = date.today().isoformat()
    included_items = [item for item in items if item.get("include_in_report")]
    company_name = included_items[0].get("company_name") if included_items else "the selected company"
    cik = included_items[0].get("cik") if included_items else "unknown"
    category_counts = Counter(str(item.get("category")) for item in included_items if item.get("category"))
    category_summary = ", ".join(f"{category}: {count}" for category, count in sorted(category_counts.items()))
    if not category_summary:
        category_summary = "no reportable filings"

    executive_summary = (
        f"Collected {len(included_items)} reportable SEC EDGAR filings for {company_name} "
        f"(CIK {cik}) and {len(macro_data)} FRED macro observations. "
        f"SEC filing categories: {category_summary}."
    )

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    report = (
        template.replace("{{ report_date }}", report_date)
        .replace("{{ executive_summary }}", executive_summary)
        .replace("{{ macro_data_summary }}", render_macro_summary(macro_data))
        .replace("{{ macro_charts }}", render_macro_charts(chart_paths))
        .replace("{{ latest_sec_filings }}", render_filings(included_items))
        .replace("{{ source_log }}", render_source_log(items, macro_data))
        .replace("{{ limitations }}", render_limitations(limitations))
    )

    output_path = output_dir / f"financial_briefing_{datetime.now(timezone.utc).date().isoformat()}.md"
    output_path.write_text(report, encoding="utf-8")
    logging.info("Saved report at %s", output_path)
    return output_path
