"""Save manual judgments for the exact measured comparison output files."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'qwen3:1.7b': ('comparison-qwen.jsonl', '1cf2e49d543421adf1ec5a7e36151b44bddf4d4494f4bfc2672220f6cf798706'),
    'llama3.2:3b': ('comparison-llama.jsonl', 'e998e1324c82acf8a110345d9e15ce4442f99b8d6322719c6edf6b66ed161cca'),
}
QWEN_CITED = {1, 2, 4, 5, 6, 7, 21, 23, 24}
LLAMA_FAILURES = {1, 2, 3, 4, 5, 6, 7, 14, 21, 22, 23, 25}

results = []
for model, (filename, digest) in SOURCES.items():
    file = ROOT / filename
    if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
        raise ValueError(f'{filename} changed; the existing manual review no longer applies.')
    rows = [json.loads(line) for line in file.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 50 and {(r['run'], r['id']) for r in rows} == {(run, i) for run in (1, 2) for i in range(1, 26)}
    for row in rows:
        run, number = row['run'], row['id']
        if model == 'qwen3:1.7b':
            failures = {3, 22, 25} | ({24} if run == 1 else set())
            grounded = (number != 24 or run != 1) if number in QWEN_CITED else None
            note = 'Wrong fee deadline; source says 13 May' if number == 24 and run == 1 else ('Refused an answerable question' if number in failures else '')
        else:
            failures = LLAMA_FAILURES
            grounded = True if number == 24 else None
            note = ('Invented treatment and recovery details' if number == 14 else 'Refused an answerable question') if number in failures else ''
        results.append({'model': model, 'run': run, 'id': number, 'type': row['type'], 'accurate': number not in failures, 'citation_grounded': grounded, 'correct_refusal': True if row['type'] == 'refusal' else None, 'elapsed_seconds': row['elapsed_seconds'], 'note': note})

with (ROOT / 'comparison-review.csv').open('w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)

for model in SOURCES:
    rows = [r for r in results if r['model'] == model]
    citations = [r for r in rows if r['citation_grounded'] is not None]
    print(model, 'accuracy', sum(r['accurate'] for r in rows), '/', len(rows),
          'grounded', sum(r['citation_grounded'] for r in citations), '/', len(citations),
          'refusals', sum(r['correct_refusal'] is True for r in rows), '/ 10',
          'median seconds', round(statistics.median(r['elapsed_seconds'] for r in rows), 2))
