# Approved Sources

This MVP allows only public, first-party SEC EDGAR and FRED data.

## FRED

- Name: Federal Reserve Economic Data
- Publisher: Federal Reserve Bank of St. Louis
- Base URL: https://fred.stlouisfed.org/
- API URL: https://api.stlouisfed.org/fred/series/observations
- Use case: Public macroeconomic time series.
- Access rule: Use the official FRED API with `FRED_API_KEY`.
- Metadata requirement: Keep series ID, source, URL, published time, and retrieved time for every observation.

## SEC EDGAR

- Name: SEC EDGAR
- Publisher: U.S. Securities and Exchange Commission
- Base URL: https://www.sec.gov/edgar
- Data URL: https://data.sec.gov/
- Use case: Public company filings and submission metadata.
- Access rule: Use SEC public endpoints with a descriptive User-Agent. Do not scrape around access controls.
- Metadata requirement: Keep form, filing date, accession number, primary document, source, URL, retrieved time, and category for every filing.

## Not Approved In MVP

- Social media posts
- Forums or anonymous commentary
- Paywalled news articles
- Broker research
- Private datasets
- Screenscraped pages that require login or CAPTCHA
- Any source whose terms prohibit automated retrieval
