"""Create page-level OCR sidecars for image-only PDFs listed in the manifest."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pymupdf
from pypdf import PdfReader
from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('source_ids', nargs='+')
args = parser.parse_args()
manifest = json.loads((ROOT / 'documents/manifest.json').read_text(encoding='utf-8'))
sources = {s['id']: s for s in manifest if s.get('status') == 'downloaded'}
missing = set(args.source_ids) - set(sources)
if missing:
    parser.error('Unknown or unavailable sources: ' + ', '.join(sorted(missing)))
output = ROOT / 'documents/ocr'
output.mkdir(exist_ok=True)
engine = RapidOCR()
for source_id in args.source_ids:
    path = ROOT / sources[source_id]['file']
    if path.suffix.lower() != '.pdf':
        raise ValueError(f'{source_id} is not a PDF')
    native = PdfReader(str(path))
    pages = {}
    with pymupdf.open(str(path)) as pdf:
        for index, page in enumerate(pdf):
            if len((native.pages[index].extract_text() or '').strip()) >= 80:
                continue
            pix = page.get_pixmap(dpi=150, alpha=False)
            raster = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            result, _ = engine(raster)
            text = '\n'.join(item[1] for item in (result or []) if len(item) >= 2)
            pages[str(index + 1)] = text
            print(source_id, 'page', index + 1, 'OCR characters:', len(text), flush=True)
    sidecar = {'source_id': source_id, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'method': 'RapidOCR ONNX, 150 dpi', 'pages': pages}
    (output / (source_id + '.json')).write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding='utf-8')
