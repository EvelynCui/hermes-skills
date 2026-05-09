"""Fetch public SEC EDGAR filings and FRED macroeconomic data."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
import pandas as pd


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path.cwd()
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CIK = "0000320193"
FRED_SERIES = {
    "FEDFUNDS": "Effective Federal Funds Rate",
    "CPIAUCSL": "Consumer Price Index",
    "UNRATE": "Unemployment Rate",
    "DGS10": "10-Year Treasury Yield",
    "T10Y2Y": "10Y minus 2Y Treasury Spread",
    "GDP": "Gross Domestic Product",
}


def utc_now_iso() -> str:
    """Return the current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def beginner_friendly_request_error(source_name: str, exc: requests.RequestException) -> str:
    """Return a clear API error without printing request URLs or API keys."""
    return (
        f"{source_name} request failed ({exc.__class__.__name__}). "
        "Check your internet connection, source availability, and environment settings."
    )


def get_output_dir() -> Path:
    """Return the configured data output directory."""
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(SKILL_ROOT / ".env")
    return Path(os.getenv("DATA_OUTPUT_DIR", str(DEFAULT_DATA_DIR)))


def normalize_cik(cik: str) -> str:
    """SEC submission endpoints expect a 10 digit CIK."""
    return cik.strip().zfill(10)


def categorize_form(form: str) -> str:
    """Group common SEC forms into beginner-friendly categories."""
    annual_forms = {"10-K", "10-K/A", "20-F", "40-F"}
    quarterly_forms = {"10-Q", "10-Q/A"}
    current_report_forms = {"8-K", "8-K/A", "6-K"}
    ownership_forms = {"3", "3/A", "4", "4/A", "5", "5/A"}
    registration_forms = {"S-1", "S-1/A", "S-3", "S-3/A", "S-4", "S-4/A"}

    if form in annual_forms:
        return "annual_report"
    if form in quarterly_forms:
        return "quarterly_report"
    if form in current_report_forms:
        return "current_report"
    if form in ownership_forms:
        return "ownership"
    if form in registration_forms:
        return "registration"
    return "other"


def sec_archive_url(cik: str, accession_number: str | None, primary_document: str | None) -> str:
    """Build a SEC Archives URL when filing document metadata is available."""
    if not accession_number or not primary_document:
        return f"https://data.sec.gov/submissions/CIK{normalize_cik(cik)}.json"

    clean_accession = accession_number.replace("-", "")
    cik_without_leading_zeroes = str(int(normalize_cik(cik)))
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{cik_without_leading_zeroes}/{clean_accession}/{primary_document}"
    )


def fetch_sec_recent_filings(
    cik: str,
    limit: int = 10,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch recent SEC company filing metadata for one CIK."""
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise ValueError("SEC_USER_AGENT is missing. SEC EDGAR data was skipped.")
    if not cik.strip():
        raise ValueError("SEC_CIK is missing. SEC EDGAR data was skipped.")

    normalized_cik = normalize_cik(cik)
    url = f"https://data.sec.gov/submissions/CIK{normalized_cik}.json"
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    retrieved_time = utc_now_iso()

    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])[:limit]
    filing_dates = recent.get("filingDate", [])[:limit]
    accession_numbers = recent.get("accessionNumber", [])[:limit]
    primary_documents = recent.get("primaryDocument", [])[:limit]
    company_name = payload.get("name", "Unknown company")

    filings: list[dict[str, Any]] = []
    for index, form in enumerate(forms):
        filing_date = filing_dates[index] if index < len(filing_dates) else None
        accession_number = accession_numbers[index] if index < len(accession_numbers) else None
        primary_document = primary_documents[index] if index < len(primary_documents) else None
        filings.append(
            {
                "form": form,
                "filing_date": filing_date,
                "accession_number": accession_number,
                "primary_document": primary_document,
                "source": "SEC EDGAR",
                "url": sec_archive_url(normalized_cik, accession_number, primary_document),
                "retrieved_time": retrieved_time,
                "category": categorize_form(form),
                "company_name": company_name,
                "cik": normalized_cik,
            }
        )

    return filings, payload


def fetch_fred_series(series_id: str, series_name: str, limit: int = 60) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch and clean one public FRED time series.

    The official FRED series/observations endpoint returns observations as
    strings. Pandas makes the date/value cleanup easy to read and extend.
    """
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        raise ValueError("FRED_API_KEY is missing. FRED macro data was skipped.")

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    retrieved_time = utc_now_iso()

    frame = pd.DataFrame(payload.get("observations", []))
    if frame.empty:
        return [], payload

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["date", "value"]).sort_values("date")

    observations: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        published_date = row["date"].date().isoformat()
        observations.append(
            {
                "series_id": series_id,
                "series_name": series_name,
                "date": published_date,
                "value": float(row["value"]),
                "source": "FRED",
                "url": f"https://fred.stlouisfed.org/series/{series_id}",
                "published_time": published_date,
                "retrieved_time": retrieved_time,
            }
        )

    return observations, payload


def fetch_fred_macro_data(limit: int = 60) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """Fetch all configured FRED series without stopping the whole run on errors."""
    limitations: list[str] = []
    raw_payloads: dict[str, Any] = {}
    macro_data: list[dict[str, Any]] = []

    if not os.getenv("FRED_API_KEY", "").strip():
        message = "FRED_API_KEY is missing. FRED macro data was skipped."
        logging.warning(message)
        return macro_data, raw_payloads, [message]

    for series_id, series_name in FRED_SERIES.items():
        logging.info("Fetching FRED series %s", series_id)
        try:
            observations, payload = fetch_fred_series(series_id, series_name, limit=limit)
            macro_data.extend(observations)
            raw_payloads[series_id] = payload
            logging.info("Fetched %s cleaned FRED observations for %s", len(observations), series_id)
        except requests.RequestException as exc:
            message = f"{beginner_friendly_request_error('FRED', exc)} Series: {series_id}."
            logging.warning(message)
            limitations.append(message)
            raw_payloads[series_id] = {"error": message, "retrieved_time": utc_now_iso()}
        except Exception as exc:
            message = f"FRED fetch failed for {series_id}: {exc}"
            logging.warning(message)
            limitations.append(message)
            raw_payloads[series_id] = {"error": message, "retrieved_time": utc_now_iso()}

    return macro_data, raw_payloads, limitations


def fetch_all_sources(cik: str | None = None, sec_limit: int = 10, fred_limit: int = 60) -> dict[str, Any]:
    """Fetch SEC EDGAR and FRED data, returning payloads and limitations."""
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(SKILL_ROOT / ".env")
    limitations: list[str] = []
    raw_payloads: dict[str, Any] = {"sec": {}, "fred": {}}
    sec_items: list[dict[str, Any]] = []
    macro_data: list[dict[str, Any]] = []
    sec_error_message: str | None = None
    configured_cik = (cik or os.getenv("SEC_CIK") or "").strip()

    if not configured_cik:
        configured_cik = DEFAULT_CIK
        limitations.append(f"SEC_CIK is missing. Used default CIK {DEFAULT_CIK}.")
        logging.warning("SEC_CIK is missing. Using default CIK %s", DEFAULT_CIK)

    logging.info("Fetching SEC filings for CIK %s", configured_cik)
    try:
        sec_items, sec_payload = fetch_sec_recent_filings(cik=configured_cik, limit=sec_limit)
        raw_payloads["sec"][normalize_cik(configured_cik)] = sec_payload
        logging.info("Fetched %s SEC filings for CIK %s", len(sec_items), configured_cik)
    except ValueError as exc:
        sec_error_message = str(exc)
        logging.warning(sec_error_message)
    except requests.RequestException as exc:
        sec_error_message = beginner_friendly_request_error("SEC EDGAR", exc)
        logging.warning("%s CIK: %s.", sec_error_message, normalize_cik(configured_cik))
    except Exception as exc:
        sec_error_message = f"SEC EDGAR fetch failed for CIK {normalize_cik(configured_cik)}: {exc}"
        logging.warning(sec_error_message)

    if sec_error_message:
        limitations.append(sec_error_message)
        raw_payloads["sec"][normalize_cik(configured_cik)] = {
            "error": sec_error_message,
            "retrieved_time": utc_now_iso(),
        }

    macro_data, fred_payloads, fred_limitations = fetch_fred_macro_data(limit=fred_limit)
    raw_payloads["fred"] = fred_payloads
    limitations.extend(fred_limitations)

    return {
        "items": sec_items,
        "macro_data": macro_data,
        "raw_payloads": raw_payloads,
        "limitations": limitations,
        "cik": normalize_cik(configured_cik),
    }


def save_raw_payloads(raw_payloads: dict[str, Any], output_dir: Path) -> list[Path]:
    """Save raw SEC payloads under data/raw/YYYY-MM-DD/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    for source_name, payload_by_key in raw_payloads.items():
        for key, payload in payload_by_key.items():
            output_path = output_dir / f"{source_name}_{key}.json"
            output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            saved_paths.append(output_path)

    return saved_paths


def save_items(items: list[dict[str, Any]], output_dir: Path | None = None) -> Path:
    """Save normalized SEC filing items as JSON."""
    output_dir = output_dir or get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "normalized_items.json"
    output_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch public SEC EDGAR and FRED data.")
    parser.add_argument("--cik", default=None, help="Optional company CIK. Defaults to SEC_CIK in .env.")
    parser.add_argument("--sec-limit", type=int, default=10, help="Number of recent SEC filings to fetch.")
    parser.add_argument("--fred-limit", type=int, default=60, help="Number of observations per FRED series.")
    args = parser.parse_args()

    result = fetch_all_sources(cik=args.cik, sec_limit=args.sec_limit, fred_limit=args.fred_limit)
    output_dir = get_output_dir() / "raw" / datetime.now(timezone.utc).date().isoformat()
    paths = save_raw_payloads(result["raw_payloads"], output_dir)
    normalized_path = save_items(result["items"], output_dir)
    print(f"Saved {len(paths)} raw payload files to {output_dir}")
    print(f"Saved {len(result['items'])} normalized SEC filings to {normalized_path}")
