---
name: financial-daily-briefing
description: Generate a daily financial briefing from public SEC EDGAR filings and FRED macroeconomic data with optional Gmail OAuth delivery.
version: 0.1.0
platforms:
  - hermes
  - macos
  - linux
metadata:
  tags:
    - finance
    - sec-edgar
    - fred
    - macroeconomics
    - gmail-oauth
    - reporting
---

# financial-daily-briefing

Generate a daily financial briefing from public SEC EDGAR filings and public FRED macroeconomic time series.

This Hermes Agent Skill is a beginner-friendly MVP:

1. Fetch latest public SEC EDGAR filings for one company CIK.
2. Fetch selected FRED macroeconomic time series when `FRED_API_KEY` is configured.
3. Clean FRED observations with pandas.
4. Generate matplotlib line charts as PNG files.
5. Build a structured Markdown report.
6. Optionally send the report with Gmail API OAuth 2.0 only when explicitly requested.

## Safety Boundaries

- Use only public SEC EDGAR and FRED data.
- Do not use private, leaked, paywalled, login-gated, or non-public data.
- Do not bypass logins, CAPTCHAs, robots rules, paywalls, or access controls.
- Do not provide investment advice, trading signals, ratings, price targets, or buy/sell/hold recommendations.
- Do not use SMTP passwords, Gmail passwords, or app passwords for email sending.
- Preserve source metadata for every filing and macro observation.

## MVP Sources

- SEC EDGAR: public company filings and submission metadata from the U.S. Securities and Exchange Commission.
- FRED: public macroeconomic series observations from the Federal Reserve Bank of St. Louis.

SEC EDGAR does not require an API key, but automated requests must include `SEC_USER_AGENT`.
FRED macro data requires `FRED_API_KEY`. If it is missing, the report still builds and lists the limitation.

## Inputs

Environment variables are read from `.env`:

- `SEC_USER_AGENT`: Required for SEC EDGAR requests.
- `SEC_CIK`: Optional default CIK. Defaults to `0000320193` if missing.
- `FRED_API_KEY`: Optional. Required only to fetch FRED macro data.
- `DATA_OUTPUT_DIR`: Optional, defaults to `data`.
- `CHART_OUTPUT_DIR`: Optional, defaults to `charts`.
- `REPORT_OUTPUT_DIR`: Optional, defaults to `reports`.
- `LOG_OUTPUT_DIR`: Optional, defaults to `logs`.
- `SEND_EMAIL`: Optional, defaults to `false`.
- `GMAIL_CREDENTIALS_PATH`: Optional, defaults to `credentials.json`.
- `GMAIL_TOKEN_PATH`: Optional, defaults to `token.json`.
- `EMAIL_TO`: Required only when email sending is explicitly enabled.
- `EMAIL_FROM`: Optional for Gmail API, defaults to `me`.
- `EMAIL_SUBJECT`: Optional, defaults to `Daily Financial Briefing`.

## Optional Email

Email sending uses the Gmail API with OAuth 2.0 and the scope:

```text
https://www.googleapis.com/auth/gmail.send
```

Place the OAuth client secret at `credentials.json` inside this skill folder, or set `GMAIL_CREDENTIALS_PATH` to its location. The first explicit send opens the browser consent flow and stores a local OAuth token at `token.json`. Later sends reuse or refresh `token.json`.

Email sending stays optional:

- `SEND_EMAIL=false` skips email completely.
- `SEND_EMAIL=true` sends with Gmail OAuth only.
- Never use SMTP passwords, Gmail passwords, or app passwords.
- You can also send an existing report by running `scripts/send_email_gmail_oauth.py` directly.

## Outputs

- Raw payloads and cleaned JSON data in `data/raw/YYYY-MM-DD/`.
- Macro charts in `charts/YYYY-MM-DD/`.
- Markdown report in `reports/YYYY-MM-DD/`.
- Logs in `logs/YYYY-MM-DD/run.log`.

## Report Sections

- Executive Summary
- Macro Data Summary
- Macro Charts
- Latest SEC Filings
- Source Log
- Limitations

## Run

Generate a report from the repository root:

```bash
python skills/financial-daily-briefing/scripts/run_daily_briefing.py
```

Send an existing report with Gmail OAuth:

```bash
python skills/financial-daily-briefing/scripts/send_email_gmail_oauth.py reports/YYYY-MM-DD/financial_briefing_YYYY-MM-DD.md --to you@example.com
```
