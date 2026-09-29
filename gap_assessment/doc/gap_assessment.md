# TradingView screener vs massive.com: data gap assessment

Date: 29/09/2026
Scope: US stocks. TradingView side = `StockField` enum of this repo (v0.5.2). massive.com side = public docs (`https://massive.com/docs/llms.txt` and the endpoint `.md` pages, copied in `../code/massive_docs/`).

## Method

- `StockField` has 3,526 members. 2,512 of them are timeframe variants (`|1`, `|5`, `|15`, `|30`, `|60`, `|120`, `|240`, `|1W`, `|1M`) of 279 base fields. After collapsing variants: **1,014 base fields**.
- Each base field is classified by ordered regex rules in `../code/classify.py`.
- Status values:
  - **DIRECT**: massive.com returns the value (name or exact definition can differ).
  - **COMPUTE**: not returned, but can be computed from massive.com raw data (bars, statements, dividends).
  - **PARTNER**: available only through a paid partner add-on on massive.com (Benzinga, ETF Global, TMX).
  - **MISSING**: no source found in massive.com docs.
  - **N/A**: TradingView internal metadata, or bond/futures field.
- Definitions were not compared value by value. A DIRECT field can still differ in formula (example: massive `Ratios.earnings_per_share` uses point-in-time shares, not weighted shares).

Full table: `tv_vs_massive_fields.csv`. Counts: `summary_by_status.csv`, `summary_by_category.csv`.

## Result by status (1,014 base fields)

| Status | Fields | % |
|---|---:|---:|
| DIRECT | 309 | 30.5 |
| COMPUTE | 507 | 50.0 |
| PARTNER | 93 | 9.2 |
| MISSING | 52 | 5.1 |
| N/A | 53 | 5.2 |

## Result by group

| Group | Fields | DIRECT | COMPUTE | PARTNER | MISSING |
|---|---:|---:|---:|---:|---:|
| Technical indicators (MA, oscillators, bands, pivots, volatility, patterns, TV rating) | 255 | 87 | 168 | 0 | 0 |
| Price, volume, performance | 119 | 8 | 111 | 0 | 0 |
| Fundamentals: statement lines (income, balance, cash flow, period info) | 137 | 123 | 13 | 0 | 1 |
| Fundamentals: ratios, margins, growth, scores | 233 | 36 | 197 | 0 | 0 |
| Fundamentals: half-year (`_fh`) | 35 | 0 | 0 | 0 | 35 |
| Dividends | 42 | 26 | 16 | 0 | 0 |
| Shares, float, market cap, employees | 15 | 13 | 0 | 0 | 2 |
| Analyst estimates, ratings, targets, earnings dates | 37 | 0 | 0 | 37 | 0 |
| ETF data | 57 | 0 | 0 | 56 | 1 |
| IPO | 13 | 8 | 1 | 0 | 4 |
| Reference (name, sector, identifiers, index membership) | 18 | 8 | 1 | 0 | 9 |

## Structural gaps (not field-level)

| Topic | TradingView screener | massive.com |
|---|---|---|
| Screening model | Server-side filter and sort on ~3,500 fields for the whole market in one request | No general screener. Full Market Snapshot (all US tickers, price/volume only). Ratios API has server-side `.gt/.lt` filters on ~25 EOD ratios. Everything else: download per ticker and compute locally |
| Markets | 66 markets (`Market` enum) | US stocks (+ OTC with `include_otc`) |
| Intraday indicator timeframes | 9 intraday/weekly/monthly variants per indicator, precomputed for every ticker | Technical Indicators API: SMA, EMA, RSI, MACD only, one ticker per call, any timespan. Other indicators must be computed from bars |
| History | Current values only | Full history: bars since 10/09/2003, statements since 29/03/2009, short interest since 29/12/2017, short volume since 06/02/2024 |
| Fundamentals update | Not documented in this repo | Statements and Ratios: end-of-day. Ratios API returns latest value only (no history) |
| Plan requirements | Free (unofficial API) | Statements and Ratios: Stocks Advanced or Financials & Ratios Expansion. Snapshot: Starter and above. Float, short interest, dividends, IPOs, ticker overview: all Stocks plans. Benzinga, ETF Global, TMX: separate paid add-ons |

## MISSING fields (52)

- Classification: `sector`, `industry`. massive gives SEC `sic_code` / `sic_description` only.
- Identifiers: `isin`, `cusip`. massive gives `cik`, `composite_figi`, `share_class_figi` (ISIN only in IPO records).
- Index membership: `indexes`.
- Shareholders: `number_of_shareholders`, `number_of_shareholders_fy`.
- Half-year fundamentals (35 `_fh` fields). massive gives quarterly, annual and TTM.
- IPO details: primary/secondary offered shares, blank check (SPAC) flag, offer time.
- Other: `is_primary`, `is_shariah_compliant`, `k1_form`, `top_revenue_country_code`, `issuance_of_stock_net_ttm`, `ucits_compliant_flag`.

## PARTNER fields (93)

| Add-on | TradingView fields covered |
|---|---|
| Benzinga Earnings | EPS and revenue forecasts, surprises, earnings release date and time, forward P/E |
| Benzinga Analyst Ratings / Consensus | `recommendation_*` counts, `price_target_*` |
| TMX Corporate Events | Earnings dates (alternative source) |
| ETF Global (Profiles, Fund Flows, Constituents) | AUM, NAV, fund flows, expense ratio, issuer, focus, leverage, holdings count, top-N weights |

Note: ETF Global Analytics is "available to existing subscribers only".

## massive.com data not present in TradingView `StockField`

- Short interest (FINRA, bi-weekly) and days to cover.
- Daily short volume and short volume ratio (FINRA off-exchange).
- Tick-level trades and NBBO quotes (REST, WebSocket, flat files).
- Second and minute aggregates via WebSocket.
- Net Order Imbalance, LULD bands, Fair Market Value (Business plan) via WebSocket.
- SEC filings: Form 3, Form 4 (insiders), 13-F holdings, 8-K text and categories, 10-K sections, risk factors.
- News (with sentiment), Benzinga news, related tickers, bulls/bears summaries, corporate guidance.
- Full split and dividend history with adjustment factors.

## Lookahead note for fundamentals

massive statements have a `filing_date`, but the docs state it is "the date of the most recent SEC filing that included this period's data", not the original filing date. A point-in-time backtest needs the original date from the SEC EDGAR Index endpoint.

## My interpretation

- About 80% of TradingView stock fields (DIRECT + COMPUTE) can be obtained or rebuilt from massive.com for US stocks. Half of them need local computation.
- The main gap is not the list of fields. It is the screening model: TradingView filters the full market server-side, massive.com mostly delivers raw data per ticker. Replacing the screener with massive.com means building a local pipeline (daily bars + statements for all tickers, then local indicator and ratio computation).
- Fields that cannot be rebuilt without extra cost: analyst estimates, ratings, price targets and earnings dates (Benzinga add-ons), and ETF data (ETF Global add-ons).
- Fields with no massive.com source: sector/industry taxonomy, ISIN/CUSIP, index membership, shareholder count.
- massive.com gives data that TradingView screener does not: history, short interest, short volume, ticks, insider and institutional filings. These are useful for backtests where the TradingView screener only gives current values.
