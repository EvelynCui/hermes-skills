# Source Quality Rules

Each SEC filing receives a simple quality score from 0 to 100.

## Required Metadata

Every item must include:

- `form`
- `filing_date`
- `accession_number`
- `primary_document`
- `source`
- `url`
- `retrieved_time`
- `category`

If a field is unknown, use `null` and keep the item only when the source is approved.

## Scoring

Start with 100 points for approved public SEC EDGAR filings.

Subtract:

- 20 points if `filing_date` is missing.
- 20 points if `url` is missing.
- 10 points if `form` is missing.
- 10 points if `accession_number` is missing.
- 50 points if the source is not in the approved MVP list.

## Minimum Bar

- Keep items scoring 70 or above.
- Items below 70 can be saved for debugging but should not appear in the daily report.

## Reporting Rules

- Clearly separate facts from interpretation.
- Do not produce investment recommendations.
- Do not say that a security is cheap, expensive, a buy, a sell, or a hold.
- Mention limitations when data is missing or stale.
