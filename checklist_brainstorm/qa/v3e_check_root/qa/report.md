# Checklist QA report — PRELIMINARY

Checks: a source, b history_start, c numeric/exact definition, d direction, e known_before_open=Yes, f cross-owner near-dup (>=88%), g BUT twin, h fetch-proven series (qa/src/fetch_proof_*.csv; missing/no_source=FAIL, save_nightly=WARN untestable until ~30 fires), i known_at <= 09:25 ET test day (registry col known_at, was published_at; format D-n HH:MM ET; revised=yes needs first_release_source), j no SEC/EDGAR/filing-derived source (exempt: Finviz export/snapshot, Fed/NYSE/Cboe).

| owner | rows | a | b | c | d | e | f | g | h | i | j | h WARN | rows w/ issues | variants | variants w/ gaps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| grok-bot-finviz | 1654 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1008 | 0 | 60 | 48 |
| grok-bot-ratings | 64 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 12 |
| grok-bot-vix-term | 156 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| manager-bot-numeric-v3 | 336 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 84 | 0 | 4 | 0 |
| new-bot-v4.4g | 650 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 162 | 0 | 31 | 18 |
| theme-radar | 13188 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8234 | 0 | 149 | 4 |
| trading-bot-taskforce | 43326 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 116 | 0 | 116 | 365 | 23 |
| trading-bot-taskforce-timeframes | 224 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 48 | 48 |

Cross-owner near-duplicate pairs: 0


## Variants with coverage gaps

- **grok-bot-finviz** / 6e asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / 6e commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / 6e leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / 6j asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / 6j commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / 6j leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / btc asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / btc commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / btc leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / cl large spec (non-commercial) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / cl managed money net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / cl producer/merchant (commercials) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / dx asset managers net (4 rows): tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / dx commercials net (4 rows): tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / dx leveraged funds net (12 rows): tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / es asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / es commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / es leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / gc large spec (non-commercial) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / gc managed money net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / gc producer/merchant (commercials) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / hg large spec (non-commercial) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / hg managed money net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / hg producer/merchant (commercials) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / ng large spec (non-commercial) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / ng managed money net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / ng producer/merchant (commercials) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / nq asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / nq commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / nq leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / rty asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / rty commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / rty leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / vx asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / vx commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / vx leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / zb asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zb commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zb leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / zc large spec (non-commercial) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zc managed money net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / zc producer/merchant (commercials) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zn asset managers net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zn commercials net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zn leveraged funds net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / zs large spec (non-commercial) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-finviz** / zs managed money net (12 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/rank
- **grok-bot-finviz** / zs producer/merchant (commercials) net (4 rows): others; tf:1d/3d/5d/10d/20d/60d; method:level/cross/streak/divergence/rank
- **grok-bot-ratings** / 3+ actions in a week (2 rows): self; others; tf:1d/3d/10d/20d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / any initiation in window (8 rows): self; others; tf:10d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / any upgrade in window (8 rows): others; tf:10d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / buy to hold move (6 rows): self; tf:3d/10d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / cluster of actions (2 rows): others; tf:1d/3d/10d/20d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / initiated at buy vs sell (6 rows): self; others; tf:3d/10d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / reiterated after target cut (6 rows): self; others; tf:3d/10d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / same-day target cuts (2 rows): self; others; tf:3d/5d/10d/20d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-ratings** / sell label move (6 rows): others; tf:3d/10d/60d; method:level/change/cross/streak/divergence/rank
- **grok-bot-ratings** / target change vs price (6 rows): others; tf:1d/3d/10d; method:extreme/change/streak/divergence/rank
- **grok-bot-ratings** / target crosses price (6 rows): others; tf:3d/10d/60d; method:level/change/cross/streak/divergence/rank
- **grok-bot-ratings** / upgrade to buy label (6 rows): others; tf:3d/10d/60d; method:level/change/cross/streak/divergence/rank
- **grok-bot-vix-term** / mac_vix term structure (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **grok-bot-vix-term** / vix > 30term in backwardation rising (1 rows): self; others; tf:3d/5d/10d/20d/60d; method:level/extreme/change/cross/streak/divergence/rank
- **grok-bot-vix-term** / vix term slope (vix3m - vix, pts) (44 rows): tf:60d
- **grok-bot-vix-term** / vix/vix3m ratio (19 rows): others; tf:60d; method:cross/divergence
- **grok-bot-vix-term** / vix3m (44 rows): tf:60d
- **grok-bot-vix-term** / vix9d (44 rows): tf:60d
- **new-bot-v4.4g** / $1 compliance regained (12 rows): method:level/change/cross/divergence
- **new-bot-v4.4g** / $1 compliance risk (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / ah first 30 min outlier move (60 rows): others; tf:3d/60d; method:level/change/cross/streak/divergence/rank
- **new-bot-v4.4g** / day-2 after 20% spike (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / ex-dividend date (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / inside day after big move (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / ipo priced date (days since ipo) (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / luld/news halt (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / monthly options expiry (3rd friday) (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / outlier earnings-day candle (60 rows): others; tf:3d/60d; method:level/change/cross/streak/divergence/rank
- **new-bot-v4.4g** / quad witching (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / reg sho threshold list (12 rows): method:change/cross/streak/divergence
- **new-bot-v4.4g** / share count jump (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / special dividend declared (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / ssr triggered (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / tiny float (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / up on spy down day (12 rows): method:level/change/cross/streak/divergence
- **new-bot-v4.4g** / weekly options expiry (friday) (12 rows): method:level/change/cross/streak/divergence
- **theme-radar** / index membership change: djia (6 rows): tf:3d/10d/60d; method:level/extreme/streak/divergence/rank
- **theme-radar** / index membership change: ndx (6 rows): tf:3d/10d/60d; method:level/extreme/streak/divergence/rank
- **theme-radar** / index membership change: rut (6 rows): tf:3d/10d/60d; method:level/extreme/streak/divergence/rank
- **theme-radar** / index membership change: s&p 500 (6 rows): tf:3d/10d/60d; method:level/extreme/streak/divergence/rank
- **trading-bot-taskforce** / bollinger(20,2) squeeze: bandwidth in own-1y bottom 10% (2 rows): others; tf:3d/5d/10d/20d/60d; method:level/change/cross/streak/divergence
- **trading-bot-taskforce** / d-1 close vs green outlier candle (88 rows): others; tf:3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / d-1 close vs red outlier candle (88 rows): others; tf:3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / days since last green outlier (110 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / days since last red outlier (110 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / down streak + red outlier closing near low (26 rows): tf:3d/5d/10d/20d/60d; method:level/change/cross/divergence/rank
- **trading-bot-taskforce** / down streak, no outlier, shrinking volume (26 rows): tf:3d/5d/10d/20d/60d; method:level/change/cross/divergence/rank
- **trading-bot-taskforce** / green outlier cluster (88 rows): others; tf:1d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / green outlier follow-through share (88 rows): others; tf:1d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / green outlier gap unfilled (22 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / green outlier level retested (66 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / green outlier within last n days (132 rows): others; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / red outlier cluster (88 rows): others; tf:1d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / red outlier follow-through share (88 rows): others; tf:1d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / red outlier gap unfilled (22 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / red outlier level retested (66 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / red outlier within last n days (132 rows): others; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / stretch >3 atr + recent up-outlier (26 rows): tf:3d/5d/10d/20d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / up streak + up-outlier on rising volume (26 rows): tf:3d/5d/10d/20d/60d; method:level/change/cross/divergence/rank
- **trading-bot-taskforce** / up streak, no outlier, shrinking bodies (26 rows): tf:3d/5d/10d/20d/60d; method:level/change/cross/divergence/rank
- **trading-bot-taskforce** / up streak, no outlier, shrinking volume (26 rows): tf:3d/5d/10d/20d/60d; method:level/change/cross/divergence/rank
- **trading-bot-taskforce** / volume since green outlier vs outlier volume (44 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce** / volume since red outlier vs outlier volume (44 rows): others; tf:1d/3d/5d/10d/60d; method:level/change/cross/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [2-day bars, completed] (4 rows): tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [2-day bars, period-to-date partial] (4 rows): tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [3-day bars, completed] (4 rows): tf:5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [3-day bars, period-to-date partial] (4 rows): tf:5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [monthly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [monthly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [weekly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / bollinger %b(20,2) [weekly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [2-day bars, completed] (4 rows): tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [2-day bars, period-to-date partial] (4 rows): tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [3-day bars, completed] (4 rows): tf:5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [3-day bars, period-to-date partial] (4 rows): tf:5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [monthly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [monthly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [weekly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma20 [weekly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [2-day bars, completed] (4 rows): tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [2-day bars, period-to-date partial] (4 rows): tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [3-day bars, completed] (4 rows): tf:5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [3-day bars, period-to-date partial] (4 rows): tf:5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [monthly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [monthly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [weekly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / close vs sma50 [weekly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [2-day bars, completed] (6 rows): tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [2-day bars, period-to-date partial] (6 rows): tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [3-day bars, completed] (6 rows): tf:5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [3-day bars, period-to-date partial] (6 rows): tf:5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [monthly bars, completed] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [monthly bars, period-to-date partial] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [weekly bars, completed] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / macd histogram (12,26,9) [weekly bars, period-to-date partial] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [2-day bars, completed] (6 rows): tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [2-day bars, period-to-date partial] (6 rows): tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [3-day bars, completed] (6 rows): tf:5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [3-day bars, period-to-date partial] (6 rows): tf:5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [monthly bars, completed] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [monthly bars, period-to-date partial] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [weekly bars, completed] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / rsi14 [weekly bars, period-to-date partial] (6 rows): others; tf:3d/5d/10d/20d/60d; method:streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [2-day bars, completed] (4 rows): tf:3d/5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [2-day bars, period-to-date partial] (4 rows): tf:3d/5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [3-day bars, completed] (4 rows): tf:5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [3-day bars, period-to-date partial] (4 rows): tf:5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [monthly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [monthly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [weekly bars, completed] (4 rows): others; tf:3d/5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
- **trading-bot-taskforce-timeframes** / sma20 vs sma50 [weekly bars, period-to-date partial] (4 rows): others; tf:3d/5d/10d/20d/60d; method:extreme/change/streak/divergence/rank
