# Ladder semantic review V1

Historical first-batch proof. See [the second batch](BINARY_LADDER_SEMANTIC_REVIEW_V2.md)
for the current cumulative review counts and additional explicit scalar aliases.

The source remains all2,680 rows of BINARY_LADDERS_V1.csv. A raw-text key
reported zero duplicates, but four repeated predicates have different default
annotations. Text uniqueness does not prove unique computed meaning.

The first reviewed rule covers only atomic daily dictionary-default RSI values
for I024/6, I025/12, I026/14 and I027/24. These two feature spellings refer to
the same scalar at the same completed native candle:

- `RSI(14) [default: dictionary default] value on D-1 1d candle`
- `RSI(14) [default] value on D-1 1d candle`

The dictionary defines I026 as RSI14 with n=14. Both duplicate rows use `>70`,
the same missingness text and the same setup-open availability rule. Thus both
answer NO at exactly70, YES above70 and have identical unknown masks. The
different annotation and viewport wording do not create a different predicate.
The same argument applies to the registered RSI6/12/24 items.

| Alias source ID | Canonical source ID | Predicate |
| --- | --- | --- |
| I024-L05 | I024-L02 | Last completed daily RSI6 >70 |
| I025-L05 | I025-L02 | Last completed daily RSI12 >70 |
| I026-L05 | I026-L02 | Last completed daily RSI14 >70 |
| I027-L05 | I027-L02 | Last completed daily RSI24 >70 |

The canonical ID is the smallest source ID for the reviewed meaning, so
reordering source rows cannot change it. All original source rows and IDs stay
in the unchanged ladder CSV. The master emits2,676 canonical add-on rows plus
an explicit4-row alias map. BINARY_MASTER_LADDER_REVIEW_V1.csv maps every one
of the2,680 source IDs to its retained canonical row. No BOUND definition changes.

Twenty source level predicates have reviewed signatures; four are aliases and
sixteen remain canonical. The other2,660 source declarations are retained as
KEEP_UNREVIEWED. The report now states PARTIAL_SEMANTIC_REVIEW and remaining
semantic dedupe NOT_PROVEN. This does not certify the rest of the ladders or
complete the assigned ladder-versus-BOUND-master review.

The rule does not fold changes, other timeframes, other settings, other
comparators, percentile thresholds, or different missingness/availability
policies. An unreviewed same-name or even same-text placeholder is preserved.
Examples still needing concrete expansion include sector membership as a
numeric rank, the multi-output alternative-bar item, earnings date/timing,
the selected FRED series/vintage and CBOE group/field. Their presence is not
permission to compute a generic numeric value or count missing data as NO.

Tests check the exact four aliases, stable IDs, all-source coverage, predicate
boundaries and policy distinctions. An authenticated comparison with the prior
65,556-row package requires the new65,552-row export to equal every prior row
except the four declared aliases; all62,876 BOUND rows stay identical. CI also
uploads the alias and full review maps with the packaged master. Existing
DEFINE/CHART/DERIVE/mining gates remain in force; add-ons stay LADDER_ADDON.
