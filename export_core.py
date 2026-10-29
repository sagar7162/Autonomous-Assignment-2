"""Copy the 30-source assignment corpus to a new, separate directory."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
target = ROOT / 'core_corpus'
if target.exists():
    raise SystemExit('core_corpus already exists; choose another location for it before exporting again.')
selected = json.loads((ROOT / 'documents/core_sources.json').read_text(encoding='utf-8'))['source_ids']
manifest = json.loads((ROOT / 'documents/manifest.json').read_text(encoding='utf-8'))
by_id = {entry['id']: entry for entry in manifest if entry.get('status') == 'downloaded'}
if len(selected) != 30 or len(set(selected)) != 30 or not set(selected) <= set(by_id):
    raise SystemExit('The core list must contain 30 unique downloaded sources.')
for source_id in selected:
    item = by_id[source_id]
    source = ROOT / item['file']
    destination = target / item['file']
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    sidecar = ROOT / 'documents/ocr' / (source_id + '.json')
    if sidecar.exists():
        output = target / 'documents/ocr' / sidecar.name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sidecar, output)
manifest_dir = target / 'documents'
manifest_dir.mkdir(parents=True, exist_ok=True)
(manifest_dir / 'manifest.json').write_text(json.dumps([by_id[i] for i in selected], indent=2, ensure_ascii=False), encoding='utf-8')
shutil.copy2(ROOT / 'documents/core_sources.json', manifest_dir / 'core_sources.json')
print('Exported 30 source records to', target)
