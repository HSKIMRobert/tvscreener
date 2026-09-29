> For the full documentation index, see: https://massive.com/docs/llms.txt

# FLAT-FILES
## Stocks

### Day Aggregates

**Endpoint:** `S3 /stocks/day-aggregates`

**Description:**

Candlesticks with open, high, low, close, and volume at per-day granularity across all U.S. equities, made available as a daily downloadable S3 file.


## Columns

| Column | Type | Description |
|--------|------|-------------|
| `close` | number | The close price for the symbol in the given time period. |
| `high` | number | The highest price for the symbol in the given time period. |
| `low` | number | The lowest price for the symbol in the given time period. |
| `open` | number | The open price for the symbol in the given time period. |
| `ticker` | string | The exchange symbol that this item is traded under. |
| `transactions` | integer | The number of transactions in the aggregate window. |
| `volume` | number | The trading volume of the symbol in the given time period. |
| `window_start` | timestamp - integer | The Unix nanosecond timestamp for the start of the aggregate window. |


## Example Data

| ticker | volume | open | close | high | low | window_start | transactions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BCC | 248274 | 61.68 | 61.99 | 62.565 | 61.41 | 1680033600000000000 | 4073 |
| CLDX | 882958 | 35.03 | 34.78 | 35.81 | 34.39 | 1680033600000000000 | 9971 |
| TRND | 2084 | 26.73 | 26.7662 | 26.7662 | 26.7201 | 1680033600000000000 | 11 |
| BFS | 47818 | 37.15 | 37.25 | 37.68 | 36.885 | 1680033600000000000 | 962 |
| NHTC | 8284 | 4.9 | 4.85 | 4.92 | 4.85 | 1680033600000000000 | 107 |
| HIMS | 1830853 | 9.59 | 9.91 | 10.11 | 9.557 | 1680033600000000000 | 13748 |
| ETHO | 981 | 49.9 | 50.0959 | 50.0959 | 49.86 | 1680033600000000000 | 40 |
| FSBC | 37318 | 21.15 | 21.3 | 21.35 | 21 | 1680033600000000000 | 916 |
| IPAY | 19344 | 40.26 | 40.06 | 40.3 | 39.94 | 1680033600000000000 | 249 |
| STLD | 1168999 | 110.58 | 109.23 | 111.6801 | 108.91 | 1680033600000000000 | 20760 |


## Plan Access

**Plan Access:** Included in select Stocks plans

#### Individual Plans

| Plan | Access |
| --- | --- |
| Stocks Basic | Not included |
| Stocks Starter | Included |
| Stocks Developer | Included |
| Stocks Advanced | Included |

#### Business Plans

| Plan | Access |
| --- | --- |
| Stocks Business | Included |

## Plan Recency

**Plan Recency:** Updated at 11a ET to include the previous day

#### Individual Plans

| Plan | Recency |
| --- | --- |
| Stocks Basic | Not included |
| Stocks Starter | End-of-day |
| Stocks Developer | End-of-day |
| Stocks Advanced | End-of-day |

#### Business Plans

| Plan | Recency |
| --- | --- |
| Stocks Business | End-of-day |

## Plan History

**Plan History:** Records date back to September 10, 2003

#### Individual Plans

| Plan | History |
| --- | --- |
| Stocks Basic | Not included |
| Stocks Starter | 5 years |
| Stocks Developer | 10 years |
| Stocks Advanced | All history |

#### Business Plans

| Plan | History |
| --- | --- |
| Stocks Business | All history |
