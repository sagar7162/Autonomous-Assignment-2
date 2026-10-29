# IIT Jodhpur Academic Helpdesk

A local multi-agent academic helpdesk that answers questions using institutional documents, looks up course information, and drafts emails for student review. It uses Ollama for language models and embeddings, and Chroma for document retrieval.

## Features

- Academic policy, curriculum, registration and examination answers with citations.
- Policy, schedule and email roles coordinated by an orchestrator.
- CSV-based timetable and instructor lookups.
- Sick-leave and makeup-exam drafts for review, without sending email.
- Clarification requests and unanswered-question logging.
- Single-agent and multi-agent modes.
- PDF, HTML, Word and Excel support, including OCR sidecars for scanned PDFs.

## Setup

Install Python 3.11 and Ollama. Open PowerShell in this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
python helpdesk.py ingest
python helpdesk.py chat
```

Keep Ollama running. Included documents are sufficient for ingestion; downloading them again is optional. Ingestion generates the local vector index in `.chroma/`. The default chat configuration uses Qwen3 1.7B, temperature zero and a 2,048-token context.

## Usage

```powershell
python helpdesk.py ask "What is the attendance requirement to sit the major exam?"
python helpdesk.py ask "When did classes begin in the summer term of 2026?"
python helpdesk.py ask "Write an email to the CSL7570 instructor requesting two days of sick leave."
python helpdesk.py chat --mode single
python helpdesk.py chat --mode multi
```

Multi-agent mode is the default. The orchestrator delegates to policy, schedule or email roles in one Python process. Roles share the local chat model; schedule lookups use deterministic tools. Single-agent mode uses shared retrieval and tools with a common role prompt. Add `--quiet` to hide execution messages.

## Project structure

| File or directory | Purpose |
|---|---|
| `helpdesk.py` | Application, routing, retrieval and tools |
| `document_readers.py` | HTML, Word and Excel extraction |
| `collect.py`, `sources.json` | Source collection |
| `register_documents.py` | Register locally supplied files |
| `ocr_documents.py` | OCR support for scanned PDFs |
| `export_core.py` | Export the selected 30-document core |
| `documents/` | Source files, manifest and OCR sidecars |
| `data/` | Timetable, instructor and offerings records |
| `evaluation/` | Questions, responses, manual reviews and evaluation runner |
| `tests/` | Application and ingestion tests |
| `TEST_QUESTIONS.md` | The 25 evaluation questions |
| `report.tex` | LaTeX assignment report with findings |

The main corpus contains 54 source records. `documents/core_sources.json` identifies a 30-document core; `python export_core.py` exports it to `core_corpus/`. The main evaluation uses the full corpus. The separate model comparison uses a 30-source configuration, as explained in the report.

## Reproduce the evaluation

```powershell
python helpdesk.py ingest
python evaluation/run.py --runs 2 --mode multi --output reproduced-multi.jsonl
python evaluation/run.py --runs 2 --mode single --output reproduced-single.jsonl
```

To evaluate another model:

```powershell
ollama pull llama3.2:3b
python evaluation/run.py --model llama3.2:3b --runs 2 --output reproduced-llama.jsonl
```

Use a fresh output filename: the runner appends. Review responses against the documents for accuracy, citation support, correct refusals and changes between runs. Responses may vary even at temperature zero.

`evaluation/results.jsonl` and `evaluation/review.csv` contain the supplied two-run evaluation. `comparison-qwen.jsonl`, `comparison-llama.jsonl` and `comparison-review.csv` contain the separate model comparison. `review_comparison.py` reproduces fixed manual judgments for those exact files; it does not automatically score new responses.

## Tests

```powershell
python -m unittest discover -s tests -v
python -m pip check
```

## Limitations

Schedule and email tools read historical CSV records rather than importing the supplied semester spreadsheets automatically. A current course lookup can therefore fail even when its assignment appears in the document corpus. Lookups require the semester label used in the CSV.

Complete Humanities elective coverage has not been established. Policy misrouting can bypass the schedule counting guard and produce an unsupported count. Citation validation does not guarantee factual support or programme applicability. OCR text and important academic answers require source verification. Unanswered questions are written to `logs/unanswered.jsonl`; email drafts require student review.
