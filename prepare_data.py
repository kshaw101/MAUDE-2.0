"""Reproducible preparation for the supplied MAUDE summary files."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

KEY = ['YEAR', 'ANALYSIS_COMPANY']
DEVICE = 'GENERIC_DEVICE_TYPE'
COUNT = 'DEVICE_RECORD_COUNT'

def prepare(device_path, company_path):
    # Preserve literal NA/N/A values until we intentionally label them.
    d = pd.read_csv(device_path, encoding='utf-8-sig', keep_default_na=False)
    c = pd.read_csv(company_path, encoding='utf-8-sig', keep_default_na=False)
    for frame, required in [(d, KEY + [DEVICE, COUNT]), (c, KEY + [COUNT])]:
        missing = set(required) - set(frame.columns)
        if missing:
            raise ValueError(f'Missing required columns: {sorted(missing)}')
        for col in ['YEAR', COUNT]:
            frame[col] = pd.to_numeric(frame[col], errors='raise')
            if not np.isfinite(frame[col]).all() or (frame[col] % 1 != 0).any():
                raise ValueError(f'{col} must contain finite integers.')
            frame[col] = frame[col].astype('int64')
        if (frame[COUNT] < 0).any():
            raise ValueError('Counts cannot be negative.')
        frame['ANALYSIS_COMPANY'] = frame['ANALYSIS_COMPANY'].str.strip()
        if frame['ANALYSIS_COMPANY'].eq('').any():
            raise ValueError('Company names cannot be empty.')
        if not frame.YEAR.isin(range(2021, 2026)).all():
            raise ValueError('This dashboard expects years 2021–2025.')
    if c.duplicated(KEY).any():
        raise ValueError('Company/year totals must be unique.')
    if d.duplicated(KEY + [DEVICE]).any():
        raise ValueError('Duplicate source company/year/device keys; inspect before combining.')
    joined = d.merge(c[KEY + [COUNT]].rename(columns={COUNT:'COMPANY_YEAR_TOTAL'}),
                     on=KEY, how='left', validate='many_to_one')
    if joined.COMPANY_YEAR_TOTAL.isna().any():
        raise ValueError('Some device rows have no company/year denominator.')
    expected = joined[COUNT].div(joined.COMPANY_YEAR_TOTAL.replace(0, np.nan)).mul(100)
    original_error = None
    if 'PERCENT_OF_COMPANY_YEAR' in joined:
        supplied = pd.to_numeric(joined.PERCENT_OF_COMPANY_YEAR, errors='raise')
        original_error = float((supplied - expected).abs().max())
        if not np.allclose(supplied, expected, atol=0.000051, rtol=0, equal_nan=True):
            raise ValueError('Source percentages do not match company/year denominators.')
    d[DEVICE] = d[DEVICE].str.strip()
    unknown = d[DEVICE].str.upper().isin(['', 'NA', 'N/A', 'NAN', 'NULL'])
    unknown_rows, unknown_records = int(unknown.sum()), int(d.loc[unknown, COUNT].sum())
    d.loc[unknown, DEVICE] = 'Unknown / not specified'
    # Aggregate only exact matching labels after whitespace/missing-label cleaning.
    grouped = d.groupby(KEY + [DEVICE], as_index=False)[COUNT].sum()
    totals = grouped.groupby(KEY)[COUNT].sum().sort_index()
    control = c.set_index(KEY)[COUNT].sort_index()
    if not totals.index.equals(control.index) or not totals.equals(control):
        raise ValueError('Device totals do not reconcile with company/year totals.')
    out = grouped.merge(c[KEY + [COUNT]].rename(columns={COUNT:'COMPANY_YEAR_TOTAL'}),
                        on=KEY, validate='many_to_one')
    out['PERCENT_OF_COMPANY_YEAR'] = out[COUNT].div(out.COMPANY_YEAR_TOTAL.replace(0, np.nan)).mul(100)
    baseline = out.loc[out.YEAR.eq(2021), ['ANALYSIS_COMPANY', DEVICE, COUNT]].rename(columns={COUNT:'BASELINE_2021_COUNT'})
    out = out.merge(baseline, on=['ANALYSIS_COMPANY', DEVICE], how='left', validate='many_to_one')
    out['INDEX_2021_100'] = out[COUNT].div(out.BASELINE_2021_COUNT.replace(0, np.nan)).mul(100)
    if 'SOURCE_URL' in c:
        out = out.merge(c[KEY + ['SOURCE_URL']], on=KEY, validate='many_to_one')
    summary = {
        'source_device_rows': len(d), 'prepared_device_rows': len(out),
        'company_year_rows': len(c), 'companies': int(c.ANALYSIS_COMPANY.nunique()),
        'years': sorted(c.YEAR.unique().tolist()), 'total_device_records': int(c[COUNT].sum()),
        'unknown_label_source_rows': unknown_rows, 'unknown_label_device_records': unknown_records,
        'max_source_percentage_rounding_difference': original_error,
        'all_company_year_totals_reconcile': True,
        'year_coverage': 'Year labels verified; extraction date, year basis, and full-year coverage unverified.',
        'unit': 'Device records; unique reports/events cannot be recovered from these summaries.'
    }
    return out.sort_values(KEY + [DEVICE]).reset_index(drop=True), c, summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--devices', required=True)
    parser.add_argument('--companies', required=True)
    parser.add_argument('--output', default='data')
    args = parser.parse_args()
    out, companies, summary = prepare(args.devices, args.companies)
    dest = Path(args.output); dest.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest / 'device_trends.csv', index=False)
    companies.to_csv(dest / 'company_year.csv', index=False)
    (dest / 'validation.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
