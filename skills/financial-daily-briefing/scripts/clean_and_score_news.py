"""Clean and score normalized source items."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


APPROVED_SOURCES = {"SEC EDGAR"}
REQUIRED_FIELDS = (
    "form",
    "filing_date",
    "accession_number",
    "primary_document",
    "source",
    "url",
    "retrieved_time",
    "category",
)


def score_item(item: dict[str, Any]) -> int:
    """Return a simple source quality score from 0 to 100."""
    score = 100

    if item.get("source") not in APPROVED_SOURCES:
        score -= 50
    if not item.get("filing_date"):
        score -= 20
    if not item.get("url"):
        score -= 20
    if not item.get("form"):
        score -= 10
    if not item.get("accession_number"):
        score -= 10

    return max(score, 0)


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    """Ensure required metadata fields exist before scoring."""
    normalized = dict(item)
    for field in REQUIRED_FIELDS:
        normalized.setdefault(field, None)
    normalized["quality_score"] = score_item(normalized)
    normalized["include_in_report"] = normalized["quality_score"] >= 70 and not normalized.get("error")
    return normalized


def clean_and_score_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize and score a list of source items."""
    return [normalize_item(item) for item in items]


def load_items(path: Path) -> list[dict[str, Any]]:
    """Load source items from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def save_items(items: list[dict[str, Any]], path: Path) -> Path:
    """Save cleaned items to JSON."""
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Clean and score source items.")
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    cleaned_items = clean_and_score_items(load_items(args.input_json))
    save_items(cleaned_items, args.output_json)
    print(f"Saved {len(cleaned_items)} cleaned items to {args.output_json}")
