# materials-investigator

A runnable MVP for long-running AI-driven investigations in materials science.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
investigator run --calls 60
```

Artifacts and full provenance logs are stored in `runs/events.db`.
