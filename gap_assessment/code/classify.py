"""Classify every TradingView stock screener field against massive.com (ex-Polygon) data.

Input : tvscreener StockField enum (current repo version)
Output: gap_assessment/doc/tv_vs_massive_fields.csv  (one row per base field)
        gap_assessment/doc/summary_by_category.csv
        gap_assessment/doc/summary_by_status.csv

Status values:
  DIRECT      massive.com returns the value (name or exact definition may differ)
  COMPUTE     not returned, but can be computed from massive.com raw data (bars, statements, dividends)
  PARTNER     only via a paid partner add-on (Benzinga, ETF Global, TMX) on massive.com
  MISSING     no source found in massive.com docs (checked 29/09/2026)
  N/A         TradingView internal / display metadata, or non-stock asset field

Rules are ordered: first match wins. Timeframe variants (|1, |5, ... |1M) are collapsed to the base field.
"""
import csv
import re
from collections import Counter
from pathlib import Path

from tvscreener.field.stock import StockField

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "doc"

# (regex on field_name, category, status, massive source, note)
RULES = [
    # --- TradingView internal / metadata ---
    (r"^(pricescale|minmov|minmove2|fractional|update_mode|update-time|update_time|kind-delay|provider-id|source-logoid|"
     r"currency_id|currency_kind|base_currency_kind|rtc|is_blacklisted|has_ipo_details_visible|has_ipo_data|active_symbol|"
     r"time|time_business_day|last_bar_update_time|bars_count|indicators_bars_count|first_bar_time|index_priority|"
     r"cryptoasset-info\..*|sum_for_enterprise_value|kind|rates_.*|fundamental_currency_code|is_symbol_primary_listing|"
     r"postmarket_time|premarket_time|typespecs|submarket|market)$",
     "TV internal metadata", "N/A", "", "Display, currency conversion or session metadata of TradingView"),
    (r"^(maturity_date|coupon|days_to_maturity|expiration)$",
     "Bond / futures field", "N/A", "", "Not a stock field"),

    # --- Half-year periods ---
    (r"_fh(_h)?$", "Fundamentals: half-year period", "MISSING", "",
     "massive gives quarterly, annual, TTM only (US filers report quarterly)"),

    # --- Reported EPS (before the generic per_share rule) ---
    (r"^(earnings_per_share(_basic|_diluted)?(_fq|_fy|_ttm)(_h)?)$", "Fundamentals: income statement", "DIRECT",
     "Income Statements API (basic/diluted_earnings_per_share)", ""),

    # --- Candlestick patterns and TV ratings ---
    (r"^Candle\.|^candlestick$", "Technical: candlestick pattern", "COMPUTE", "Aggregates (OHLC bars)",
     "Pattern rules must be coded locally"),
    (r"^(Recommend\.|Rec\.)", "Technical: TV technical rating", "COMPUTE", "Aggregates + local indicators",
     "TradingView rating formula must be reproduced locally"),

    # --- Technical indicators ---
    (r"^(SMA\d+|EMA\d+)(\[\d\])?$", "Technical: moving average", "DIRECT", "Technical Indicators API (SMA/EMA)",
     "One ticker per call; any window and timespan. No screen-wide filter"),
    (r"^RSI\d*(\[\d\])?$", "Technical: oscillator", "DIRECT", "Technical Indicators API (RSI)",
     "One ticker per call; any window and timespan"),
    (r"^MACD\.", "Technical: oscillator", "DIRECT", "Technical Indicators API (MACD)",
     "One ticker per call"),
    (r"^(Stoch\.|ADX|AO|Mom|CCI20|BBPower|UO|W\.R|ROC|ChaikinMoneyFlow|MoneyFlow|Aroon\.)", "Technical: oscillator",
     "COMPUTE", "Aggregates (OHLCV bars)", "Not in massive indicator list (only SMA, EMA, RSI, MACD)"),
    (r"^(BB\.|KltChnl\.|DonchCh20\.|Ichimoku\.|HullMA|VWMA|P\.SAR|Pivot\.)", "Technical: bands / trend / pivots",
     "COMPUTE", "Aggregates (OHLCV bars)", "Not in massive indicator list"),
    (r"^(ATR|ATRP|ADR|ADRP|Volatility\.[DWM])$", "Technical: volatility", "COMPUTE", "Aggregates (OHLCV bars)", ""),
    (r"^beta_\d_year$", "Technical: volatility", "COMPUTE", "Aggregates (stock + index/ETF bars)", "Needs benchmark series"),

    # --- Price / volume ---
    (r"^(open|high|low|close|volume|change|change_abs|VWAP)$", "Price & volume: current bar", "DIRECT",
     "Snapshot (day, min, prevDay, todaysChange)", "Full-market snapshot gives all US tickers in one call"),
    (r"^(change|change_abs)\.\w+$", "Price & volume: change over N min/period", "COMPUTE", "Aggregates / snapshot min bars", ""),
    (r"^(change_from_open|change_from_open_abs|gap|gap_up|gap_down|gap_up_abs|gap_down_abs|volume_change|volume_change_abs|Value\.Traded)$",
     "Price & volume: current bar", "COMPUTE", "Snapshot (day + prevDay)", "Simple arithmetic on snapshot values"),
    (r"^(premarket_|postmarket_|pre_change|post_change)", "Price & volume: extended hours", "COMPUTE",
     "Minute aggregates (include extended hours); Daily Ticker Summary (preMarket, afterHours price)",
     "Only pre/after-hours single price is direct"),
    (r"^(average_volume.*|AvgValue\.Traded_\d+d|relative_volume.*)$", "Price & volume: averages", "COMPUTE",
     "Aggregates; Ratios.average_volume (30 day, EOD)", "30-day average volume is direct in Ratios"),
    (r"^Perf\.\w+\.MarketCap$", "Performance: market cap change", "COMPUTE", "Aggregates + shares outstanding history", ""),
    (r"^Perf\.", "Performance: price change", "COMPUTE", "Aggregates (daily bars)", ""),
    (r"^(High|Low|Open)\.", "Price & volume: period high/low", "COMPUTE", "Aggregates (daily bars)", "Includes dates of high/low"),
    (r"^(price_52_week_.*|all_time_.*|low_after_high_all_change.*)$", "Price & volume: period high/low", "COMPUTE",
     "Aggregates (daily bars)", "History from 10/09/2003 only, so all-time values are limited to that start"),

    # --- Analyst / estimates (partner) ---
    (r"^(earnings_per_share_forecast.*|revenue_forecast.*|eps_surprise.*|revenue_surprise.*)$", "Analyst: estimates & surprises",
     "PARTNER", "Benzinga Earnings (estimated_eps, estimated_revenue, eps_surprise, revenue_surprise)", "Paid add-on"),
    (r"^(price_target_.*|recommendation_(buy|sell|hold|over|under|total|mark))$", "Analyst: ratings & targets",
     "PARTNER", "Benzinga Consensus Ratings / Analyst Ratings", "Paid add-on"),
    (r"^(price_earnings_forward_fy|non_gaap_price_to_earnings_per_share_forecast_next_fy)$", "Analyst: forward valuation",
     "PARTNER", "Benzinga Earnings estimates + price", "Compute ratio from partner estimate"),
    (r"^(earnings_release_.*|earnings_publication_type.*)$", "Events: earnings date", "PARTNER",
     "Benzinga Earnings (date, time, date_status) or TMX Corporate Events", "Paid add-on"),

    # --- IPO ---
    (r"^ipo_(offer_price_usd|offered_shares|shares_outstanding|price_range_usd_min|price_range_usd_max|deal_amount_usd|announcement_date|offer_date)$",
     "Events: IPO", "DIRECT", "IPOs API (final_issue_price, max_shares_offered, lowest/highest_offer_price, total_offer_size, announced_date, listing_date, shares_outstanding)", ""),
    (r"^ipo_market_cap_usd$", "Events: IPO", "COMPUTE", "IPOs API (final_issue_price x shares_outstanding)", ""),
    (r"^ipo_", "Events: IPO", "MISSING", "", "Primary/secondary split, SPAC flag, offer time not in IPOs API"),

    # --- ETF fields (partner) ---
    (r"^(aum|aum_perf\..*|nav|nav_perf\..*|nav_total_return\..*|nav_discount_premium|fund_flows\..*)$", "ETF: NAV, AUM, flows",
     "PARTNER", "ETF Global Fund Flows / Profiles (nav, fund_flow, aum, discount_premium)", "Paid add-on; perf values computed from history"),
    (r"^(expense_ratio|etf_holdings_count|issuer|index_provider|brand|focus|niche|category|strategy|asset_class|weighting_scheme|"
     r"selection_criteria|leveraged_flag|leverage|leverage_ratio|inverse_flag|actively_managed|launch_date|holds_derivatives_flag|"
     r"currency_hedged_flag|holdings_region|etf_fund_currency|country_code_fund|dividend_treatment|transparent_holding_flag)$",
     "ETF: profile", "PARTNER", "ETF Global Profiles & Exposure / Taxonomies", "Paid add-on"),
    (r"^weight_top_\d+$", "ETF: profile", "PARTNER", "ETF Global Constituents", "Compute top-N weight from holdings"),
    (r"^ucits_compliant_flag$", "ETF: profile", "MISSING", "", "European fund status; massive ETF data is US"),

    # --- Dividends ---
    (r"^(ex_dividend_date.*|dividend_ex_date.*|payment_date.*|dividend_payment_date.*|dividend_amount.*|amount_(recent|upcoming)|"
     r"frequency_.*|dividend_frequency.*|dividends_frequency|next_dividend_date)$",
     "Dividends: events", "DIRECT", "Dividends API (ex_dividend_date, pay_date, cash_amount, frequency)", ""),
    (r"^(dividends_yield.*|dividend_yield.*|yield_(recent|upcoming))$", "Dividends: yield", "DIRECT",
     "Ratios.dividend_yield (EOD)", "Recent/upcoming variants computed from Dividends API"),
    (r"^(dps_common_stock_prim_issue.*|dividends_per_share_fq|expected_annual_dividends|indicated_annual_dividend)$",
     "Dividends: per share", "COMPUTE", "Dividends API (sum cash_amount by period)", ""),
    (r"^(continuous_dividend_.*|dividend_payout_ratio.*|cash_dividend_coverage.*)$", "Dividends: ratios", "COMPUTE",
     "Dividends API + income / cash flow statements", ""),
    (r"^(dividends_paid|total_cash_dividends_paid.*|neg_total_cash_dividends_paid.*|preferred_dividends)$", "Fundamentals: cash flow",
     "DIRECT", "Cash Flow (dividends) / Income (preferred_stock_dividends_declared)", "Half-year (_fh) not provided"),

    # --- Shares / float ---
    (r"^(float_shares_outstanding.*|float_shares_percent_current)$", "Shares & float", "DIRECT", "Float API (free_float, free_float_percent)",
     "Latest value only; definition may differ"),
    (r"^(total_shares_outstanding.*|shares_outstanding|diluted_shares_outstanding_fq)$", "Shares & float", "DIRECT",
     "Ticker Overview (share_class / weighted_shares_outstanding); Income (diluted_shares_outstanding)", ""),
    (r"^(market_cap_basic|market_cap_calc)$", "Valuation: market cap", "DIRECT", "Ticker Overview.market_cap; Ratios.market_cap", ""),
    (r"^(number_of_employees.*)$", "Company: employees", "DIRECT", "Ticker Overview.total_employees", "Current value only, no FY history"),
    (r"^(number_of_shareholders.*)$", "Company: shareholders", "MISSING", "", ""),

    # --- Reference data ---
    (r"^(name|description|exchange|type|currency|logoid|subtype)$", "Reference", "DIRECT",
     "Ticker Overview (name, primary_exchange, type, currency_name, branding)", "subtype mapped to ticker type"),
    (r"^(sector|industry)$", "Reference: classification", "MISSING", "Ticker Overview (sic_code, sic_description)",
     "Only SEC SIC code; no sector/industry taxonomy like TradingView"),
    (r"^country$", "Reference", "COMPUTE", "Ticker Overview.address", "US HQ address only"),
    (r"^(isin|cusip)$", "Reference: identifiers", "MISSING", "Ticker Overview (cik, composite_figi, share_class_figi)",
     "ISIN only in IPO records; FIGI and CIK available instead"),
    (r"^(indexes)$", "Reference: index membership", "MISSING", "", "No S&P / Nasdaq index membership lists"),
    (r"^(is_primary|is_shariah_compliant|k1_form|top_revenue_country_code)$", "Reference", "MISSING", "", ""),
    (r"^(current_session)$", "Reference", "DIRECT", "Market Status API", ""),
    (r"^(fiscal_period_.*|most_recent_quarter_date|last_report_frequency)$", "Fundamentals: period info", "DIRECT",
     "Statements (fiscal_year, fiscal_quarter, period_end, timeframe)", ""),

    # --- Valuation ratios direct in Ratios endpoint ---
    (r"^(price_earnings_ttm|price_earnings_current|price_book_ratio|price_book_fq|price_book_current|price_sales_ratio|price_sales|"
     r"price_sales_current|price_revenue_ttm|price_free_cash_flow_ttm|price_free_cash_flow_current|price_to_cash_f_operating_activities_ttm|"
     r"price_cash_flow_current|enterprise_value_ebitda_ttm|enterprise_value_ebitda_current|enterprise_value_fq|enterprise_value_current|"
     r"enterprise_value_to_revenue_ttm)$",
     "Valuation ratios", "DIRECT", "Ratios API (price_to_earnings, price_to_book, price_to_sales, price_to_free_cash_flow, "
     "price_to_cash_flow, ev_to_ebitda, ev_to_sales, enterprise_value)", "EOD; server-side .gt/.lt filters available"),
    (r"^(current_ratio.*|quick_ratio.*|cash_ratio|debt_to_equity.*|return_on_assets.*|return_on_equity(_fq|_fy)?)$",
     "Liquidity / leverage / return ratios", "DIRECT", "Ratios API (current, quick, cash, debt_to_equity, return_on_assets, return_on_equity)",
     "Ratios API is latest TTM-based; FQ/FY variants computed from statements"),
    (r"^(price_annual_book|price_annual_sales|price_earnings_growth_ttm|price_to_cash_ratio|price_to_working_capital_fq|earnings_yield|"
     r"enterprise_value_to_.*)$", "Valuation ratios", "COMPUTE", "Statements + price", ""),


    # --- Growth and margins ---
    (r"(_growth|_cagr_5y|_5y_growth|growth_percent)", "Fundamentals: growth", "COMPUTE", "Statements history (since 29/03/2009)", ""),
    (r"(margin|_ratio_fy$|_ratio_ttm$)", "Fundamentals: margins", "COMPUTE", "Income statement", ""),

    # --- Other computed fundamental ratios / scores ---
    (r"(per_share|_per_employee|turnover|interst_cover|return_on_|return_of_|debt_to_|_to_total_|_to_capital|_to_equity|_to_assets|"
     r"_to_ebitda|_to_revenue|altman|piotroski|sloan|zmijewski|graham|tobin|ncavps|buyback|sustainable_growth|effective_interest|"
     r"shrhldrs_equity_to_total_assets|debt_to_assets|revenue_per_employee)", "Fundamentals: derived ratios & scores", "COMPUTE",
     "Balance sheet + income + cash flow + price (+ Ticker Overview.total_employees)", "Per-employee uses current headcount only"),

    # --- Raw statement lines ---
    (r"^(total_revenue|revenue|gross_profit|net_income|ebitda|oper_income|research_and_dev|neg_research_and_dev|sell_gen_admin_exp_other|"
     r"earnings_per_share_basic|earnings_per_share_diluted|earnings_per_share|basic_eps_net_income|last_annual_eps|last_annual_revenue|"
     r"net_income_bef_disc_oper|ebit_ttm)", "Fundamentals: income statement", "DIRECT",
     "Income Statements API (quarterly, annual, TTM)", "EBIT computed; _h history suffix = time series"),
    (r"^(total_assets|total_current_assets|total_liabilities|total_current_liabilities|total_equity|shrhldrs_equity|goodwill|"
     r"cash_n_equivalents|long_term_debt|short_term_debt)", "Fundamentals: balance sheet", "DIRECT",
     "Balance Sheets API (quarterly, annual)", ""),
    (r"^(total_debt|net_debt|working_capital|cash_n_short_term_invest|total_capital|long_term_capital)", "Fundamentals: balance sheet",
     "COMPUTE", "Balance Sheets API (sum of lines)", ""),
    (r"^(cash_f_operating_activities|cash_f_investing_activities|cash_f_financing_activities|capital_expenditures|neg_capital_expenditures|"
     r"free_cash_flow)", "Fundamentals: cash flow", "DIRECT",
     "Cash Flow Statements API; Ratios.free_cash_flow", "Capex = purchase_of_property_plant_and_equipment"),
    (r"^issuance_of_stock_net", "Fundamentals: cash flow", "MISSING", "", "Only other_financing_activities (mixed)"),
]


def classify(field_name: str):
    for pattern, category, status, source, note in RULES:
        if re.search(pattern, field_name):
            return category, status, source, note
    return "Unclassified", "MISSING", "", "No rule matched"


def main():
    base = {}
    variants = Counter()
    for f in StockField:
        key = f.field_name.split("|")[0]
        variants[key] += 1
        base.setdefault(key, f.label)

    rows = []
    for key, label in base.items():
        category, status, source, note = classify(key)
        rows.append({"tv_field": key, "tv_label": label, "timeframe_variants": variants[key],
                     "category": category, "massive_status": status, "massive_source": source, "note": note})

    DOC.mkdir(parents=True, exist_ok=True)
    with open(DOC / "tv_vs_massive_fields.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    statuses = ["DIRECT", "COMPUTE", "PARTNER", "MISSING", "N/A"]
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["category"], Counter())[r["massive_status"]] += 1
    with open(DOC / "summary_by_category.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["category", "total", *statuses])
        for cat in sorted(by_cat, key=lambda c: -sum(by_cat[c].values())):
            c = by_cat[cat]
            w.writerow([cat, sum(c.values()), *[c[s] for s in statuses]])

    tot = Counter(r["massive_status"] for r in rows)
    with open(DOC / "summary_by_status.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["massive_status", "base_fields", "pct"])
        for s in statuses:
            w.writerow([s, tot[s], round(100 * tot[s] / len(rows), 1)])
    print(f"StockField members: {sum(variants.values())}, base fields: {len(rows)}")
    print(dict(tot))
    print("Unclassified:", [r["tv_field"] for r in rows if r["category"] == "Unclassified"])


if __name__ == "__main__":
    main()
