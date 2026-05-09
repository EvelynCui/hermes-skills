"""Run the MVP daily financial briefing workflow."""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from build_report import build_report
from clean_and_score_news import clean_and_score_items
from fetch_sources import fetch_all_sources, save_items, save_raw_payloads
from generate_charts import generate_macro_charts
from send_email import send_report_email


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def configured_path(env_name: str, fallback: str) -> Path:
    """Read a path from the environment, relative to the project root if needed."""
    raw_value = os.getenv(env_name, fallback)
    path = Path(raw_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def setup_logging(log_dir: Path) -> Path:
    """Write logs to both the console and logs/YYYY-MM-DD/run.log."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return log_path


def parse_args() -> argparse.Namespace:
    """Parse beginner-friendly command line options."""
    parser = argparse.ArgumentParser(description="Run the daily financial briefing MVP.")
    parser.add_argument(
        "--cik",
        default=None,
        help="Optional company CIK. Defaults to SEC_CIK in .env, then 0000320193.",
    )
    parser.add_argument("--sec-limit", type=int, default=10, help="Number of SEC filings to include.")
    parser.add_argument("--fred-limit", type=int, default=60, help="Number of observations per FRED series.")
    return parser.parse_args()


def main() -> None:
    """Run each simple workflow step in order."""
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    today = date.today().isoformat()

    data_root = configured_path("DATA_OUTPUT_DIR", "data")
    report_root = configured_path("REPORT_OUTPUT_DIR", "reports")
    chart_root = configured_path("CHART_OUTPUT_DIR", "charts")
    log_root = configured_path("LOG_OUTPUT_DIR", "logs")
    raw_dir = data_root / "raw" / today
    report_dir = report_root / today
    chart_dir = chart_root / today
    log_dir = log_root / today
    raw_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    chart_dir.mkdir(parents=True, exist_ok=True)

    log_path = setup_logging(log_dir)
    logging.info("Starting daily financial briefing MVP")
    logging.info("Raw data directory: %s", raw_dir)
    logging.info("Report directory: %s", report_dir)
    logging.info("Chart directory: %s", chart_dir)

    logging.info("Fetching SEC EDGAR filings and FRED macro data")
    fetch_result = fetch_all_sources(cik=args.cik, sec_limit=args.sec_limit, fred_limit=args.fred_limit)
    logging.info("Using SEC CIK %s", fetch_result["cik"])
    raw_payload_paths = save_raw_payloads(fetch_result["raw_payloads"], raw_dir)
    raw_items = fetch_result["items"]
    macro_data = fetch_result["macro_data"]
    normalized_path = save_items(raw_items, raw_dir)
    logging.info("Saved %s raw payload files", len(raw_payload_paths))
    logging.info("Saved normalized source items to %s", normalized_path)

    logging.info("Cleaning and scoring source items")
    cleaned_items = clean_and_score_items(raw_items)
    cleaned_path = raw_dir / "cleaned_items.json"
    cleaned_path.write_text(json.dumps(cleaned_items, indent=2), encoding="utf-8")
    logging.info("Saved cleaned source items to %s", cleaned_path)

    macro_path = raw_dir / "fred_macro_data.json"
    macro_path.write_text(json.dumps(macro_data, indent=2), encoding="utf-8")
    logging.info("Saved cleaned FRED macro data to %s", macro_path)

    logging.info("Generating macro charts")
    chart_paths = generate_macro_charts(macro_data, chart_dir)
    logging.info("Generated %s macro chart files", len(chart_paths))

    limitations = list(fetch_result["limitations"])

    logging.info("Building Markdown report")
    report_path = build_report(cleaned_items, macro_data, chart_paths, limitations, report_dir)
    included_count = sum(1 for item in cleaned_items if item.get("include_in_report"))
    logging.info("Reportable item count: %s", included_count)

    if os.getenv("SEND_EMAIL", "false").lower() == "true":
        logging.info("SEND_EMAIL=true, attempting email delivery")
        try:
            send_report_email(report_path)
        except Exception as exc:
            logging.exception("Email delivery failed: %s", exc)
    else:
        logging.info("SEND_EMAIL is not true; email delivery skipped")

    logging.info("Finished daily financial briefing MVP")

    print("Done.")
    print(f"Raw data directory: {raw_dir}")
    print(f"Normalized items: {normalized_path}")
    print(f"Cleaned items: {cleaned_path}")
    print(f"Macro data: {macro_path}")
    print(f"Charts directory: {chart_dir}")
    print(f"Report: {report_path}")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
