"""Keep denominators and baselines independent of dashboard filters."""
import pandas as pd

METRICS = {
    'Share within company (%)': ('PERCENT_OF_COMPANY_YEAR', 'Share of company-year device records (%)'),
    'Device record counts': ('DEVICE_RECORD_COUNT', 'Device records'),
    'Change since 2021': ('INDEX_2021_100', 'Device record count index (2021 = 100)'),
}

def trend_grid(data, pairs, years):
    """Absent rows and excluded years remain gaps, never invented zeros."""
    frames = []
    for company, device in sorted(pairs):
        part = data.loc[data.ANALYSIS_COMPANY.eq(company) & data.GENERIC_DEVICE_TYPE.eq(device)].set_index('YEAR')
        part = part.reindex(range(2021, 2026))
        part['ANALYSIS_COMPANY'] = company
        part['GENERIC_DEVICE_TYPE'] = device
        part['YEAR_INCLUDED'] = part.index.isin(years)
        for column, _ in METRICS.values():
            part.loc[~part.YEAR_INCLUDED, column] = float('nan')
        frames.append(part.reset_index())
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
