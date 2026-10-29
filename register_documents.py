"""Register user-added local documents; retain existing provenance and skip duplicates."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from document_readers import SUPPORTED

ROOT = Path(__file__).resolve().parent


def register(root=ROOT):
    root = Path(root).resolve()
    path = root / 'documents/manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    known_paths = {str((root / s['file']).resolve()).casefold() for s in manifest if s.get('file')}
    hashes = {hashlib.sha256((root / s['file']).read_bytes()).hexdigest(): s['id'] for s in manifest if s.get('status') == 'downloaded'}
    ids = {s['id'] for s in manifest}
    added, duplicates = [], []
    for source in sorted((root / 'documents').iterdir()):
        if not source.is_file() or source.suffix.lower() not in SUPPORTED or str(source.resolve()).casefold() in known_paths:
            continue
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest in hashes:
            duplicates.append({'file': source.relative_to(root).as_posix(), 'duplicate_of': hashes[digest]})
            continue
        source_id = 'local-' + digest[:16]
        if source_id in ids:
            raise ValueError(f'Source ID collision: {source.name}')
        manifest.append({'id': source_id, 'title': source.stem + ' (user supplied)', 'url': source.resolve().as_uri(), 'file': source.relative_to(root).as_posix(), 'status': 'downloaded', 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'origin': 'user-supplied', 'sha256': digest})
        hashes[digest] = source_id
        ids.add(source_id)
        added.append(source_id)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = {'added_source_ids': added, 'duplicates': duplicates, 'manifest_sources': len(manifest)}
    (root / 'documents/local_registration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    print(json.dumps(register(), indent=2, ensure_ascii=True))
