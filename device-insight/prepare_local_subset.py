"""Bounded streaming join of existing local MAUDE ZIPs. Run from any directory."""
import csv
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / 'data' / '530Final'


def records(path):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith('.txt')]
        if len(names) != 1:
            raise ValueError(f'Expected one text table in {path.name}')
        with z.open(names[0]) as raw:
            stream = io.TextIOWrapper(raw, encoding='latin1')
            headers = stream.readline().strip().split('|')
            # Bulk tables occasionally contain enormous/malformed physical rows.
            # Discard overlong rows in bounded chunks rather than materializing them.
            for _ in range(150000):
                line = stream.readline(100000)
                if not line:
                    break
                if not line.endswith('\n') and len(line) == 100000:
                    while line and not line.endswith('\n'):
                        line = stream.readline(100000)
                    continue
                parts = line.rstrip('\r\n').split('|', len(headers) - 1)
                if len(parts) == len(headers):
                    yield dict(zip(headers, parts))


def main():
    metadata, out, seen = {}, [], set()
    for i, row in enumerate(records(INPUT / 'device2025.zip')):
        if i >= 15000:
            break
        key = row.get('MDR_REPORT_KEY', '').strip()
        if key and key not in metadata:
            metadata[key] = {
                'device': (row.get('GENERIC_NAME') or row.get('BRAND_NAME') or 'Unspecified device').strip() or 'Unspecified device',
                'manufacturer': (row.get('MANUFACTURER_D_NAME') or 'Unspecified manufacturer').strip() or 'Unspecified manufacturer'}
    scanned = 0
    for row in records(INPUT / 'foitext2025.zip'):
        scanned += 1
        if scanned > 100000:
            break
        key = row.get('MDR_REPORT_KEY', '').strip()
        text = row.get('FOI_TEXT', '').strip()
        if key not in metadata or key in seen or not 30 <= len(text) <= 20000:
            continue
        out.append(dict(report_id=key, **metadata[key],
                        event_type='Not loaded (narrative sample)', narrative=text))
        seen.add(key)
        if len(out) >= 300:
            break
    if len(out) < 4:
        raise ValueError('Too few joined records in the bounded scan; use demo data or a prepared CSV instead.')
    with (ROOT / 'local-reports.csv').open('w', newline='', encoding='utf8') as f:
        writer = csv.DictWriter(f, fieldnames=['report_id', 'device', 'manufacturer', 'event_type', 'narrative'])
        writer.writeheader()
        writer.writerows(out)
    manifest = {'source_files': ['device2025.zip', 'foitext2025.zip'],
                'join_key': 'MDR_REPORT_KEY', 'report_count': len(out),
                'metadata_keys': len(metadata), 'narrative_rows_scanned': scanned,
                'selection': 'First up to 15000 device rows; first up to 100000 narrative rows; first eligible narrative per key; up to 300 joined reports.',
                'limitations': 'Convenience subset. Malformed/overlong physical rows skipped. Additional devices/narratives per key omitted. No master event type loaded. Local ZIP provenance unverified; not a representative sample.'}
    (ROOT / 'local-subset-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
