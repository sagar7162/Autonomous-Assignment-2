"""Download public IIT Jodhpur sources; failures are recorded, never silently substituted."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import requests
import truststore

truststore.inject_into_ssl()

root = Path(__file__).resolve().parent
out = root / 'documents'
out.mkdir(exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--only', nargs='+', help='Download only these source IDs, preserving other manifest entries')
args = parser.parse_args()
sources = json.loads((root / 'sources.json').read_text(encoding='utf-8'))
if args.only:
    unknown = set(args.only) - {s['id'] for s in sources}
    if unknown:
        parser.error('Unknown source IDs: ' + ', '.join(sorted(unknown)))
    manifest_path = out / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    manifest = [s for s in manifest if s['id'] not in args.only]
    manifest.extend(s for s in sources if s['id'] in args.only)
else:
    manifest_path = out / 'manifest.json'
    existing = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    manifest = sources + [s for s in existing if s.get('origin') == 'user-supplied' and s['id'] not in {item['id'] for item in sources}]
calendar = root / 'data' / 'Academic-Calendar-AY-2026-27-639178076336417495.pdf'
if calendar.exists() and not args.only:
    manifest.append({'id': 'calendar-2026-27-user', 'title': 'Academic Calendar AY 2026–27 (user supplied)', 'url': 'https://www.iitj.ac.in/office-of-academics/en/academic-calendar', 'file': str(calendar.relative_to(root)), 'status': 'downloaded', 'retrieved_at': 'user-supplied'})
for source in manifest:
    if args.only and source['id'] not in args.only:
        continue
    if source.get('status') == 'downloaded':
        print(source['id'], 'user-supplied')
        continue
    try:
        response = requests.get(source['url'], timeout=60, headers={'User-Agent': 'AcademicHelpdeskAssignment/1.0'})
        response.raise_for_status()
        pdf = response.content.startswith(b'%PDF')
        path = out / (source['id'] + ('.pdf' if pdf else '.html'))
        path.write_bytes(response.content)
        source.update(file=str(path.relative_to(root)), retrieved_at=datetime.now(timezone.utc).isoformat(), status='downloaded')
        print(source['id'], len(response.content))
    except Exception as exc:
        source.update(status='failed', error=str(exc))
        print(source['id'], 'FAILED', exc)
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
