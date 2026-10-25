#!/usr/bin/env python3
"""Fetch SEC XBRL companyfacts for the universe (Block H, METHODOLOGY 0b).

Source: https://data.sec.gov/api/xbrl/companyfacts/CIK{10d}.json (keyless,
SEC fair-access: declared User-Agent required). Point-in-time key = filed date;
every row carries filed_date, so a value is used only when filed_date < D.

Extracts a curated tag set (enough for Altman Z / Piotroski F / Beneish M plus
growth + quality), unit USD/shares/EPS only, forms 10-K/10-Q/10-KT/10-QT.

Usage: fetch_xbrl.py --shard N --shards 8 --universe universe.parquet --out dir
"""
import os, sys, json, time, argparse, urllib.request, urllib.error

UA = {'User-Agent': 'checklist-engine/1.0 (https://github.com/SRoyaltyy/checklist-engine)'}

TAGS = {  # us-gaap tags kept (taxonomy prefix stripped on match)
 'Assets','AssetsCurrent','Liabilities','LiabilitiesCurrent','StockholdersEquity',
 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
 'NetIncomeLoss','ProfitLoss','OperatingIncomeLoss','Revenues','RevenueFromContractWithCustomerExcludingAssessedTax',
 'SalesRevenueNet','CostOfRevenue','CostOfGoodsAndServicesSold','GrossProfit',
 'NetCashProvidedByUsedInOperatingActivities','NetCashProvidedByUsedInInvestingActivities',
 'NetCashProvidedByUsedInFinancingActivities','CashAndCashEquivalentsAtCarryingValue',
 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents','LongTermDebtNoncurrent','LongTermDebt',
 'DebtCurrent','AccountsReceivableNetCurrent','InventoryNet','PropertyPlantAndEquipmentNet',
 'Goodwill','IntangibleAssetsNetExcludingGoodwill','ResearchAndDevelopmentExpense',
 'SellingGeneralAndAdministrativeExpense','InterestExpense','IncomeTaxExpenseBenefit',
 'EarningsPerShareBasic','EarningsPerShareDiluted','WeightedAverageNumberOfSharesOutstandingBasic',
 'WeightedAverageNumberOfDilutedSharesOutstanding','CommonStockSharesOutstanding','CommonStockSharesIssued',
 'NetIncomeLossAvailableToCommonStockholdersBasic','OtherComprehensiveIncomeLossComprehensiveIncomeNetOfTax',
 'InvestmentIncomeInterest','DepreciationDepletionAndAmortization','ShareBasedCompensation',
 'OperatingLeaseCost','FinanceLeasePrincipalPayments','PaymentsToAcquirePropertyPlantAndEquipment',
 'PaymentsOfDividendsCommonStock','PaymentsForRepurchaseOfCommonStock','ComprehensiveIncomeNetOfTax',
}

def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            if e.code == 429:
                time.sleep(5 * (k + 1)); continue
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shard', type=int, default=0); ap.add_argument('--shards', type=int, default=8)
    ap.add_argument('--universe', required=True); ap.add_argument('--out', default='xbrl_out')
    a = ap.parse_args()

    import pandas as pd
    u = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(u.ticker.unique())
    mine = tickers[a.shard::a.shards]
    print(f'xbrl shard {a.shard}/{a.shards}: {len(mine)} tickers', flush=True)

    raw = get('https://www.sec.gov/files/company_tickers.json')
    m = json.loads(raw)
    cik_of = {}
    for v in m.values():
        t = v['ticker'].upper().replace('-', '.')
        cik_of[t] = int(v['cik_str'])
    rows, fail = [], []
    for i, t in enumerate(mine):
        cik = cik_of.get(t.upper().replace('-', '.'))
        if cik is None:
            fail.append((t, 'no-cik')); continue
        blob = get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json')
        if blob is None:
            fail.append((t, 'no-facts')); continue
        try:
            f = json.loads(blob)
        except Exception:
            fail.append((t, 'bad-json')); continue
        facts = f.get('facts', {}).get('us-gaap', {})
        for tag, units in facts.items():
            if tag not in TAGS:
                continue
            for unit, items in units.get('units', {}).items():
                if unit not in ('USD', 'shares', 'USD/shares'):
                    continue
                for it in items:
                    if it.get('form') not in ('10-K', '10-Q', '10-KT', '10-QT'):
                        continue
                    rows.append((t, cik, tag, unit, it.get('end'), it.get('fy'), it.get('fp'),
                                 it.get('filed'), it.get('val')))
        time.sleep(0.12)          # SEC fair access: <= 10 req/s
        if i % 200 == 199:
            print(f'{i+1}/{len(mine)} tickers, {len(rows)} rows', flush=True)
    os.makedirs(a.out, exist_ok=True)
    df = pd.DataFrame(rows, columns=['ticker', 'cik', 'tag', 'unit', 'end', 'fy', 'fp', 'filed', 'val'])
    fn = os.path.join(a.out, f'xbrl_shard_{a.shard:03d}.parquet')
    df.to_parquet(fn, index=False)
    meta = {'shard': a.shard, 'shards': a.shards, 'tickers': len(mine), 'rows': len(df),
            'fail_count': len(fail), 'fail_sample': fail[:20],
            'pit': 'use only rows with filed_date < D', 'tags': sorted(TAGS)}
    json.dump(meta, open(fn.replace('.parquet', '.json'), 'w'), indent=1)
    print('wrote', fn, len(df), 'rows,', len(fail), 'failures')

if __name__ == '__main__':
    main()
