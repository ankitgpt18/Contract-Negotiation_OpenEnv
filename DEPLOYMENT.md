# Deployment Guide (Docker + Hugging Face)

## 1) Local Docker validation

Build image:

```bash
docker build -t contract-neg-openenv:latest .
```

Run container:

```bash
docker run --rm contract-neg-openenv:latest
```

## 2) GitHub checklist

- Push full source code.
- Include `README.md`, `SUBMISSION.md`, `RESULTS.md`, and this file.
- Include generated benchmark artifact in `artifacts/`.

## 3) Hugging Face packaging checklist

- Create a new repository (Space or code repo as required by submission workflow).
- Add:
  - source code
  - Dockerfile
  - benchmark artifact
  - reproducibility instructions
- Add a short demo GIF/video and benchmark summary table.

## 4) What judges should be able to do in under 5 minutes

- Install dependencies.
- Run tests.
- Run benchmark report.
- Execute one sample episode (`showcase_run.py`).

Suggested command:

```bash
python run_all.py
```
