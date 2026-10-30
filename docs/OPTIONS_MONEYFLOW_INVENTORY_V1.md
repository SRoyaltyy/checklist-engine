# Options and money-flow inventory

Authority: James/Cyrus00:27/00:41 tier-1/family instructions and c8d6e8f09:20
inventory freeze. The258 existing items remain fixed; no new item or data kind
is introduced here. New question families describe the already approved source
components. Missing source/schema/PIT work is explicit and is never answered NO.

| Existing items | Classification and limits |
|---|---|
|I201 CBOE market-wide options|Primary options item: market/group put/call volume and OI, VIX term context. DATA_READY source access is reinstated; it does not establish a full stock-level chain or a verified answer panel.|
|I202 single-stock options|Primary stock-options item. Full-universe historical OI/strike/expiry/IV source and publication lineage remain incomplete; the old dictionary GAP text is historical, not permission to drop the hunt.|
|I178 VIX level|Options-derived market volatility context; not a single-stock order-flow measurement.|
|C22; I079–I096; I222|OHLCV activity/price-volume proxies: volume, RVOL, dollar volume, OBV, A/D, MFI, up/down volume, anchored VWAP, volume profile, CMF, Chaikin oscillator, EOM, EFI, Klinger, NVI/PVI, signed volume, PVO, PVT and Twiggs MF. None establishes broker net capital flow or aggressor-classified large/small orders.|
|I187 Form4|Reported insider P/S transactions and disclosed dollar/share amounts. Use acceptance/publication availability; these are reported trades, not total market capital flow.|
|I188 short interest|Settlement-date position with publication-date availability; not daily short trade flow.|
|I189 short volume|Gross FINRA short-marked activity ratio; not net short-position growth or capital outflow.|
|I199 13F holdings|Reported positions and position changes, available after filing; changes alone do not identify cash inflow/outflow.|
|I203 checklist score path|Depends on the future checklist score. It is not an options item.|

I220 Chaikin Volatility uses high/low ranges; its name does not make it a
volume-flow source. Likewise volume-profile levels are trading activity rather
than a historical ETF creation/redemption ledger.

## Required question/source components under the frozen inventory

| Question family | Required fields before real answers |
|---|---|
|Options put/call volume/OI|Underlying or explicit market group, session, call/put volume and OI, publication timestamp/calendar, source era. Zero-call handling and ratio precision must be explicit.|
|IV level, own percentile, term structure, skew|Dated underlying/contract identity, expiry, strike, call/put side, IV with calculation convention and snapshot/publication time; fixed tenor/delta selection and interpolation contract.|
|Unusual options volume|Contract/underlying volume, a complete declared prior baseline, comparable contract lifecycle and PIT availability.|
|Max pain and OI walls|Complete dated strike×expiry×side OI panel, contract multiplier, expiry selection and tie rules; no substitute from market-group OI.|
|Net flow and large/small orders|Signed notional or independently classified buy/sell amounts, units/currency, classification thresholds/method, timestamps, corrections and publication availability. OHLCV proxies do not fill these fields.|
|Block/dark-pool activity|Stock/date or print identity, size/notional, venue, trade/report/publication timestamps, corrections and aggregation rules. Weekly ATS summaries do not become a daily print panel by forward-filling.|
|ETF flows|Dated creations/redemptions or independently reported fund flows, shares/NAV units, split/corporate-action basis and publication timing; AUM changes alone are insufficient.|
|Short-volume questions|FINRA venue-level short/total volume, complete venue coverage, trading session and publication time; retain the gross-activity interpretation.|

These families are WAITING_ON_DATA or WAITING_ON_PIT_BINDING until their actual
required components are authenticated. Keep definitions/lenses under review
now; source availability does not automatically pass DEFINE→CHART/PANEL/CONCRETE
→DERIVE→MINE or Step6b. Kimi owns the source hunts in PR#165 and viewport#163;
this inventory does not duplicate those fetches or assume paid/authenticated
vendor access.

CBOE JSON-era CSVs are now on main with volume/OI fields. Their
`available_from_not_before` is only a next-weekday lower bound; actual session
alignment is still required. Derive ratios from the raw counts at declared
precision, not only the six-decimal convenience column. Preserve the2019-10-07
exchange/group definition break and the post2022 0DTE flag; equity-only ratios
remain preferred. Dolt IV/chains do not imply OI exists. Tier-1 options/money-flow
source work is never capped or dropped; the authorized price v1 and later
options/money-flow v2 are versioned separately.
