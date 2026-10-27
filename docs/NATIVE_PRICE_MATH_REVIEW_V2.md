# Separately versioned native math review

This draft addresses James's six PR13 review items in the 08:25 HKT entry. It is kept off main while the old frozen native recovery, compact recovery and stitch are pending. Their recipe fingerprint remains `0738f12902e29f1272d06f30fdd56d6f80e200bc25f825cf9a737404acdffcc4`; corrected calculations cannot accept those checkpoints under a new input manifest. A successful three-entity budget probe will not constitute full-universe acceptance or permission to mix recipes.

| Review item | Draft change and evidence |
|---|---|
| Fixed column dtype | TA-Lib numeric indicators use float64 for every ticker; normalized TA-Lib patterns use float32, including NaN warmup. A cross-stock test changes numeric range without changing the dtype policy. |
| McGinley after NaN | SMA seed requires the configured count of consecutive finite observations. Missing/undefined updates reset the seed; a two-regime hand fixture and prefix checks cover restart after a gap. |
| Moving-average overflow | Named averages, configured/channel means, price-scaled TV aliases, native OHLCV and other candle numeric families retain float64 before storage. A `1e39` fixture verifies finite means and aliases survive the casts. This does not prevent mathematically undefined or float64-overflowing computations from remaining undefined. |
| Own box 1.08 hand test | Buy date D sees `(2+4+8+16+32)/5 = 12.4`; altering D and later bars, or removing them, leaves that result unchanged. |
| Hull rounding | Half-period uses floor; root uses nearest integer `floor(sqrt(n)+0.5)`, following James's registered convention. Period 8 distinguishes this from floor-root: a linear input yields `x - 1/3`. This is an analytic test, not a claim of external bar-by-bar parity. |
| Storage and runner budget | The runner measures both frozen and corrected recipes on three deterministic real entities from one verified compact part, across all 22 timeframes. Results remain pending until the job completes. |

The budget selects maximum observed history, maximum reference close and median reference close from the bounded source part, without looking at trade outcomes. It verifies input/calendar/archive/member hashes and recreates baseline source files from the exact frozen commit. Separate processes prevent module-cache and peak-memory contamination between recipes. It records library versions, columns and dtype/schema hashes, compressed Parquet bytes, elapsed seconds and peak RSS.

The report projects storage using the largest measured entity times the full accepted entity count with a 25% margin. Runtime uses the slowest entity times the largest existing shard count, with 25% plus 30 minutes for I/O. Scratch includes a 1.9 GB archive bound, part/output staging, 512 MB input allowance and 7 GB reserve. The sample must fit 70% of runner RAM and the existing 350-minute native timeout. Failing a bound preserves the measurements and requires a different execution/storage plan; it does not weaken the threshold or approve a full rebuild. Sampling one part is a material limitation and is recorded.

Actual measurements are saved as Actions artifacts and a separate immutable proof release, including when a completed measurement fails the budget. No request-only proof is published. This workflow fetches no vendor or SEC data, starts no full-universe rebuild and does not change the live recovery routes. Thirty focused local math/settings/statistics tests passed; Linux alignment/checkpoint tests precede the runner measurement. No local dependency installation.
