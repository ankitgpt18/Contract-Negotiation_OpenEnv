# Round-1 Submission Brief

## Project

**Title:** Contract Negotiation Arena (OpenEnv)  
**Theme fit:** Multi-step LLM-native RL environment with hidden risks, structured negotiation, and strategic resolution.

## Problem statement

Current agent benchmarks often over-index on short-horizon tasks. Real-world assistant value requires sustained decision-making under uncertainty: read dense language, identify hidden risk, negotiate edits, and decide whether to walk away.

This environment models that challenge directly through adversarial contract negotiation.

## What is novel

- Contract law-style trap discovery and remediation rather than common game/grid tasks.
- Dynamic counterparty that can partially concede or inject new traps.
- Hybrid evaluation:
  - Programmatic reward with five axes.
  - Transcript-level LLM-style quality evaluation.
- Scenario curriculum (`cooperative_bootcamp` -> `adversarial_finals`) for robustness testing.

## OpenEnv alignment

- Environment/action/observation/state architecture follows OpenEnv-style patterns.
- Deterministic seeding supported for reproducible episodes.
- Dockerized execution included for consistent evaluation runtime.

## Environment design

### Action space

- `read_clause`
- `assess_risk`
- `propose_change`
- `counter_offer`
- `accept_terms`
- `reject_terms`
- `walk_away`

### Observation space

- Full clause list (agent-visible fields only)
- phase (`analysis`, `negotiation`, `resolution`)
- risk report + counterparty response
- analysis and negotiation budgets
- final score breakdown at terminal step

### Hidden state

- Trap metadata (type, severity, fair rewrite)
- Counterparty style and concession budget
- Detected/fixed progression per trap

## Reward and grading

Five weighted axes:

1. Trap detection
2. Amendment quality
3. Negotiation efficiency
4. Final fairness
5. Walk-away accuracy

Additional reward shaping:

- severe penalty for blind acceptance
- unresolved severity penalty
- all-traps-fixed bonus

## Scenarios

- `baseline`
- `cooperative_bootcamp`
- `adversarial_finals`
- `procurement_redteam`

## Reproducibility artifacts

- Unit tests in `tests/`
- Benchmark generator in `benchmark_report.py`
- One-command pipeline in `run_all.py`
- Showcase trajectory runner in `showcase_run.py`
- Output artifact: `artifacts/benchmark_report.md`

## How to run

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python run_all.py
```

## Why this is submission-ready

- Clear task definition and multi-step interaction loop.
- Explicit grader/reward logic with deterministic testing.
- Programmatic + LLM-style scoring fit to Round-1 expectations.
- Docker + documentation for evaluator reproducibility.
