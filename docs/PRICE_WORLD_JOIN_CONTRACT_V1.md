# Price-world join keys and dates

This read-only contract publishes the keys the SEC and Options pipelines can
target. It binds to the retained #203 cohort and its measured price world;
it does not establish missing historical ticker ownership or open scoring.

| File | Contents |
| --- | --- |
| [Join keys](../dictionary/PRICE_WORLD_JOIN_KEYS_V1.csv) | One row per retained price ticker: 8,439 rows, raw-source SHA256 and measured setup-row count, CIK candidate and identity evidence dates |
| [Trading sessions](../dictionary/PRICE_WORLD_SESSIONS_V1.csv) | All 9,271 dates from the authenticated frozen calendar, with previous/next session links |
| [Contract metadata](PRICE_WORLD_JOIN_CONTRACT_V1.json) | Source and output hashes, coverage, bounds and join restrictions |
| [Column clocks](PRICE_COLUMN_AVAILABILITY_V1.md) | Availability and source-candle end for all 22,968 produced price columns |

## Price primary key

The logical key is **(`price_ticker`, `setup_session_date`)**. Preserve the exact
case and punctuation of `price_ticker`; no implicit dot/dash, class-share, option
root, fund/issuer or renamed-symbol substitution is authorized. A CIK is an
issuer identifier, not a replacement stock key. Its CSV representation is a
zero-padded ten-character string; load it as text.

The setup date D is a date key for the session's buy/open. Each stock's usable
rows are the intersection of its authenticated source/setup membership and the
bound calendar, restricted to dates from 2020-01-01. The published per-stock
counts total **12,547,288**. Calendar membership alone does not create a setup
row for an IPO, suspension, source gap or other absent stock-date.

The session CSV is an exact date extraction from `market_sessions.parquet`
in release `native-price-inputs-v1-40336250454-1`, SHA256
`3904f3115c180d40f230e36facad6b585efed861f0e8af13225e4dfb8513d074`.
It spans **1990-01-02 through 2026-10-23**. Earlier dates supply indicator history;
the final date is a hard boundary of this frozen price version. Do not extrapolate
weekdays, holidays, future sessions, or session-open timestamps from this file.
A future price calendar requires a new bound version. Collectors may retain
newer source data independently; it is not joined into this frozen world.

## Ticker and CIK date evidence

The exact [archived identity map](SEC_RETAINED_IDENTITY_MAP_V1.md) supplies:

| Status | Retained names | Meaning |
| --- | ---: | --- |
| `UNIQUE_CIK` | 3,996 | One eligible archived issuer candidate with filed-dated shares associations; usable to target source retrieval |
| `NO_CIK` | 4,419 | Unresolved; candidate CIK remains blank |
| `QUARANTINED_ISSUER_PRODUCT_ALIAS` | 24 | Bank/product aliases excluded from equity issuer joins; candidate CIK remains blank |
| Formal ownership intervals | 0 | No historical `valid_from` / `valid_to_exclusive` ledger is available |

`observed_first_filed` and `observed_last_filed` are the first and last archived
shares-fact filing observations for that ticker/CIK association. **They are not
ownership interval endpoints.** A first observation cannot establish when the
symbol became valid, and a last observation cannot establish its expiry.

Accordingly, `valid_from` and `valid_to_exclusive` are blank for every row,
`historical_identity_status` is `NO_FORMAL_OWNERSHIP_INTERVAL`, and
`historical_join_allowed` is `false`. A blank endpoint means unknown, not an
unbounded interval. The contract explicitly publishes this missing coverage;
it does not silently backfill a present-day symbol map through history.

When independent ownership evidence is available, a new version can register
half-open intervals (`valid_from <= D < valid_to_exclusive`) and source citations.
Conflicting intervals must fail a join. Retain CIK1790169 and all product-alias
quarantines from the source map. Newly downloaded identity evidence must not
rewrite this historical contract in place.

## SEC and Options joins

SEC retrieval can use the eligible CIK candidates; downloading an issuer is not
proof that it owned a ticker on D. A production historical join additionally
requires independently established dated identity, and acceptance/filed date
**strictly before D**. Never substitute fiscal period end, transaction date,
reporting-quarter end, or a current-map retrieval date for filing availability.
Preserve the source acceptance/filed value and its precision. Date-only records
on D remain unavailable under this conservative session-level rule.

Options need an exact dated underlying-symbol mapping. An option root, OCC
contract symbol, or issuer CIK alone does not establish a price-ticker match.
Keep source session/observation date separate from publication availability;
join a value only after its availability is established before D's open.
Do not assume session D open interest was published before D's open. If the
publication clock or historical mapping is unknown, leave the joined value and
availability unknown and record the reason.

Missing identity, unmatched stock-date, unknown source availability, and a genuine
reported zero are distinct states. Joins must preserve unknowns and report match
counts by status. The existing world gate stays **NOT_PROVEN** and scoring
stays **CLOSED**.

## Reproduction and checks

`python -m ci.price_join_contract check` uses only the standard library to verify
the committed file hashes, complete retained identity set, evidence-date fields,
counts, unknown ownership bounds, and calendar order/links. The PR workflow runs
this check without installing dependencies.

To reproduce the files from already authenticated metadata, run
`python -m ci.price_join_contract build --plan <bound-plan.json> --calendar <bound-market_sessions.parquet>`.
Build checks the immutable plan and calendar hashes before decoding the session
list. It reads no OHLCV/indicator data and performs no market calculation.
The plan hash is `18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d`.
