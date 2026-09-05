from __future__ import annotations

import hashlib
import importlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .pipeline import (
    build_context_bundle,
    build_submission,
    resolve_model_version,
    score_if_available,
    validate_packages,
)


REQUIRED_CONFIG_KEYS = {
    "schema_version",
    "model_version",
    "model_key",
    "input_json",
    "output_root",
    "top_k",
    "seed",
    "limit",
    "prompt_mode",
    "decoding_mode",
    "enable_quality_retry",
    "adapter",
}


def _resolve_path(production_root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (production_root / path).resolve()


def load_config(
    config_path: str | Path,
    *,
    workspace_root: str | Path,
) -> dict[str, Any]:
    path = Path(config_path).resolve()
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("Production config phải là object JSON")
    missing = REQUIRED_CONFIG_KEYS - set(config)
    if missing:
        raise ValueError(f"Production config thiếu khóa: {sorted(missing)}")
    if config["schema_version"] != 1:
        raise ValueError("Chỉ hỗ trợ production config schema_version=1")
    if type(config["top_k"]) is not int or config["top_k"] <= 0:
        raise ValueError("top_k phải là số nguyên dương")
    if type(config["seed"]) is not int or config["seed"] < 0:
        raise ValueError("seed phải là số nguyên không âm")
    if config["limit"] is not None and (
        type(config["limit"]) is not int or config["limit"] <= 0
    ):
        raise ValueError("limit phải là null hoặc số nguyên dương")
    adapter = config["adapter"]
    if not isinstance(adapter, dict) or not {
        "local_path",
        "kaggle_slug",
    }.issubset(adapter):
        raise ValueError("adapter phải có local_path và kaggle_slug")
    resolve_model_version(workspace_root, str(config["model_version"]))
    return config


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def _mean_flag(details: list[dict[str, Any]], key: str) -> float:
    return statistics.fmean(bool(item["generation"].get(key)) for item in details)


def execute_run(
    config_path: str | Path,
    *,
    workspace_root: str | Path,
    generator_factory: Callable[..., Any] | None = None,
    run_id: str | None = None,
    input_json: str | Path | None = None,
    output_root: str | Path | None = None,
    top_k: int | None = None,
    limit: int | None = None,
    seed: int | None = None,
    adapter_path: str | Path | None = None,
) -> Path:
    workspace = Path(workspace_root).resolve()
    production_root = workspace
    config = load_config(config_path, workspace_root=workspace)
    version_root = resolve_model_version(workspace, str(config["model_version"]))
    source_root = version_root / "src"
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))

    blocks = importlib.import_module("legalqa_baseline.blocks")
    scoring = importlib.import_module("legalqa_baseline.scoring")
    generation_module = importlib.import_module("legalqa_baseline.generation")

    selected_input = Path(input_json).resolve() if input_json else _resolve_path(
        production_root, str(config["input_json"])
    )
    selected_output = Path(output_root).resolve() if output_root else _resolve_path(
        production_root, str(config["output_root"])
    )
    selected_top_k = top_k if top_k is not None else int(config["top_k"])
    selected_limit = limit if limit is not None else config["limit"]
    selected_seed = seed if seed is not None else int(config["seed"])
    selected_adapter = (
        Path(adapter_path).resolve()
        if adapter_path
        else _resolve_path(production_root, str(config["adapter"]["local_path"]))
    )
    if not selected_input.is_file():
        raise FileNotFoundError(f"Không tìm thấy input JSON: {selected_input}")

    rows = validate_packages(
        json.loads(selected_input.read_text(encoding="utf-8-sig"))
    )
    if selected_limit is not None:
        rows = rows[: int(selected_limit)]
    if not rows:
        raise ValueError("Không có mẫu để sinh đáp án")

    models = json.loads(
        (version_root / "configs" / "models.json").read_text(encoding="utf-8")
    )
    model_key = str(config["model_key"])
    if model_key not in models:
        raise KeyError(f"model_key không tồn tại trong phiên bản: {model_key}")
    model_config = models[model_key]
    if generator_factory is None:
        if not selected_adapter.is_dir():
            raise FileNotFoundError(f"Không tìm thấy adapter QLoRA: {selected_adapter}")
        generator_factory = generation_module.QwenGenerator
    generator = generator_factory(
        config=model_config,
        cache_dir=version_root / ".cache" / "huggingface",
        adapter_path=selected_adapter,
        prompt_mode=str(config["prompt_mode"]),
        decoding_mode=str(config["decoding_mode"]),
        enable_quality_retry=bool(config["enable_quality_retry"]),
    )

    started = datetime.now(timezone.utc)
    identifier = run_id or started.strftime("%Y%m%dT%H%M%SZ")
    run_dir = selected_output / identifier
    if run_dir.exists():
        raise FileExistsError(f"Run directory đã tồn tại: {run_dir}")
    results: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        context = build_context_bundle(row, top_k=selected_top_k)
        generated = generator.generate(
            row["question"],
            context["text"],
            context["citation_metadata"],
            seed=selected_seed + index,
            fewshot_examples=[],
        )
        answer = blocks.assemble_answer(
            generated["lead"],
            context["text"],
            generated["conclusion"],
        )
        results.append({"id": str(row["id"]), "answer": answer})
        details.append(
            {
                "id": str(row["id"]),
                "question": row["question"],
                "context": context,
                "generation": generated,
                "answer": answer,
                "has_reference": bool(row.get("reference_answer")),
            }
        )
        print(
            f"[{index + 1}/{len(rows)}] id={row['id']} "
            f"valid={generated.get('format_valid')} "
            f"retry={generated.get('retry_used')}",
            flush=True,
        )

    submission = build_submission(results)
    scores = score_if_available(
        submission,
        rows,
        scorer=scoring.score_submission,
    )
    finished = datetime.now(timezone.utc)
    manifest = json.loads(
        (version_root / "version.json").read_text(encoding="utf-8")
    )
    metrics = {
        "schema_version": 1,
        "run_id": identifier,
        "status": "completed",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "elapsed_seconds": round((finished - started).total_seconds(), 3),
        "input_json": str(selected_input),
        "input_sha256": _sha256(selected_input),
        "output_answers": str(run_dir / "answers.json"),
        "model_version": config["model_version"],
        "version_manifest": manifest,
        "model_key": model_key,
        "model_id": model_config["model_id"],
        "adapter_path": str(getattr(generator, "adapter_path", selected_adapter)),
        "parameter_count": getattr(generator, "parameter_count", None),
        "prompt_mode": config["prompt_mode"],
        "decoding_mode": config["decoding_mode"],
        "quality_retry_enabled": config["enable_quality_retry"],
        "top_k": selected_top_k,
        "seed": selected_seed,
        "sample_count": len(rows),
        "format_valid_rate": _mean_flag(details, "format_valid"),
        "answer_complete_rate": _mean_flag(details, "answer_complete"),
        "retry_rate": _mean_flag(details, "retry_used"),
        "quality_retry_rate": _mean_flag(details, "quality_retry_used"),
        "quality_retry_acceptance_rate": _mean_flag(
            details, "quality_retry_accepted"
        ),
        "token_limit_retry_rate": _mean_flag(details, "token_limit_retry_used"),
        **scores,
    }
    _write_json(run_dir / "answers.json", submission)
    _write_json(run_dir / "run_metrics.json", metrics)
    _write_jsonl(run_dir / "details.jsonl", details)
    return run_dir
