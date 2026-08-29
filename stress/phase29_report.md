# Phase 29 -- Unified Engine Stress Report

_Generated 2026-08-29T21:50:13_

## Linear

| Layer | Passed | Total |
|-------|--------|-------|
| engine (parse->dispatch->solve) | 97 | 97 |
| api adapter (_run_pipeline) | 97 | 97 |
| reasoning engine (demo /predict) | 97 | 97 |
| FastAPI TestClient POST /solve | 97 | 97 |

_No failures._

## Quadratic

| Layer | Passed | Total |
|-------|--------|-------|
| engine (parse->dispatch->solve) | 99 | 99 |
| api adapter (_run_pipeline) | 99 | 99 |
| reasoning engine (demo /predict) | 99 | 99 |
| FastAPI TestClient POST /solve | 99 | 99 |

_No failures._

## Differentiation

| Layer | Passed | Total |
|-------|--------|-------|
| engine (parse->dispatch->solve) | 100 | 100 |
| api adapter (_run_pipeline) | 100 | 100 |
| reasoning engine (demo /predict) | n/a (no reasoner registered) | 100 |
| FastAPI TestClient POST /solve | 100 | 100 |

_No failures._

## Juxtaposition (parser fix)

| Layer | Passed | Total |
|-------|--------|-------|
| engine (parse->dispatch->solve) | 8 | 8 |
| api adapter (_run_pipeline) | 8 | 8 |
| reasoning engine (demo /predict) | n/a (no reasoner registered) | 8 |
| FastAPI TestClient POST /solve | 8 | 8 |

_No failures._
