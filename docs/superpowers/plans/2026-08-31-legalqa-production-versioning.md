# LegalQA Production Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Version the V8.3 Full Hard code and build a configurable production inference/Kaggle workflow for member-B retrieval JSON.

**Architecture:** Shared datasets stay at `legalqa_baseline/data`; executable model code lives under a named version. `model_production` dynamically resolves that version and reuses its generator, answer assembly, and official scorer without duplicating model logic.

**Tech Stack:** Python 3.14 local tooling, PyTorch/Transformers/PEFT on Kaggle, unittest, Kaggle CLI.

**Spec:** `docs/superpowers/specs/2026-08-31-legalqa-production-versioning-design.md`

## Global Constraints

- Keep the experiment kernel distinct from the production kernel.
- Keep `legalqa_baseline/data` shared and outside version directories.
- Preserve the V8.3 Full Hard generation behavior byte-for-byte where possible.
- Use the existing `legalqa_baseline.scoring.score_submission` implementation.
- Official inputs without references must report null scores, never fabricated scores.

---

### Task 1: Version the existing model code

**Files:** Move current config/source/script/test/docs into `legalqa_baseline/v8_3_full_hard`; modify path constants and `.kaggle/manage.py`.

- [ ] Verify exact source and destination paths.
- [ ] Move directories without moving shared `data`.
- [ ] Update scripts so `DATA_ROOT = VERSION_ROOT.parent / "data"`.
- [ ] Update experiment bundling to source the named version and retain runtime layout.
- [ ] Run the existing 62-test suite.

### Task 2: Production input and output core (TDD)

**Files:** Create `model_production/src/model_production/pipeline.py` and `model_production/tests/test_pipeline.py`.

- [ ] Write failing tests for schema validation, top-k context/citations, answer schema, and reference detection.
- [ ] Run tests and confirm failures are caused by missing production functions.
- [ ] Implement minimal pure functions and rerun tests.
- [ ] Add scoring tests that call the versioned scorer; verify reference-free null behavior.

### Task 3: Production runner and configuration (TDD)

**Files:** Create `model_production/scripts/run_inference.py`, `model_production/configs/production.json`, version manifest, and copied dated input.

- [ ] Write failing tests for version/config/path resolution.
- [ ] Implement CLI overrides for input, output, top-k, limit, seed, and adapter.
- [ ] Write timestamped `answers.json`, `run_metrics.json`, and `details.jsonl`.
- [ ] Verify with a fake generator so tests do not require loading model weights.

### Task 4: Separate Kaggle production build (TDD)

**Files:** Create `model_production/kaggle/settings.json`, `build.py`, kernel template, and tests.

- [ ] Write failing metadata/bundle tests.
- [ ] Build a private input dataset from the configured JSON.
- [ ] Build a GPU kernel referencing input and adapter datasets.
- [ ] Verify generated source bundle contains the selected model version and production runner.

### Task 5: Artifact and documentation

**Files:** Update top-level/version/production README files and download V8.3 Full Hard outputs.

- [ ] Download kernel outputs to `.kaggle/qlora-v83full-downloads`.
- [ ] Verify adapter presence, size, and config.
- [ ] Document local inference, input selection, output formats, dataset build, kernel build/push, and scoring semantics.
- [ ] Run all unit tests, syntax checks, settings validation, and both kernel builds.
