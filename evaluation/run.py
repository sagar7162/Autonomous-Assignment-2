"""Record repeated model responses for subsequent independent human scoring."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from helpdesk import answer

parser = argparse.ArgumentParser()
parser.add_argument('--model', default='qwen3:1.7b')
parser.add_argument('--runs', type=int, default=2)
parser.add_argument('--mode', choices=['multi', 'single'], default='multi')
parser.add_argument('--output', default='results.jsonl', help='Output filename in evaluation directory')
args = parser.parse_args()
questions = json.loads((ROOT / 'evaluation/questions.json').read_text(encoding='utf-8'))
output = ROOT / 'evaluation' / Path(args.output).name
with output.open('a', encoding='utf-8') as f:
    for run in range(1, args.runs + 1):
        for item in questions:
            started = time.perf_counter()
            try:
                result = answer(item['question'], args.model, args.mode)
                error = None
            except Exception as exc:
                result, error = None, str(exc)
            record = {'timestamp': datetime.now(timezone.utc).isoformat(), 'model': args.model, 'mode': args.mode, 'run': run, **item, 'response': result, 'error': error, 'elapsed_seconds': round(time.perf_counter() - started, 3), 'accuracy': None, 'groundedness': None, 'correct_refusal': None}
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
            f.flush()
            print(run, item['id'], 'ERROR' if error else 'OK', flush=True)
