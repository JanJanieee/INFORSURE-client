"""I-validate, i-train, i-evaluate at i-package ang selected model."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from backend.app import config as backend_config
from training import classical
from training.evaluate import LABELS, check_gate, evaluate
from training.package import package_model
from training.split import SPLITS, split_dataset

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("configs") / "default.json"


# Basahin ang CSV at i-check ang text at labels.
def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    missing = {"text", "label"} - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    bad = set(df["label"].dropna()) - set(LABELS)
    if bad or df["label"].isna().any() or df["text"].isna().any():
        raise ValueError(f"dataset must be cleaned first (training.prepare.clean); bad labels: {sorted(bad)}")
    return df


# Tanggapin lang ang approved language at source origins.
def validate_language(df: pd.DataFrame, cfg: dict) -> None:
    language = cfg.get("training_language")
    if not language:
        return
    if "origin" in df and df["origin"].fillna("").str.startswith("translated/").any():
        raise ValueError("translated rows are excluded from this run")
    origin_languages = cfg.get("language_by_origin")
    if origin_languages:
        # May English rows na mali ang automatic language tag.
        # Declared source ang basis para buo ang original corpus.
        if "origin" not in df or not df["origin"].map(origin_languages).eq(language).all():
            raise ValueError(f"this run accepts only declared {language} source origins")
    elif "language" not in df or not df["language"].eq(language).all():
        raise ValueError(f"this run accepts only language={language}; translated/mixed data is excluded")


# I-run ang split, training, validation selection, test at packaging.
def run(args: argparse.Namespace) -> int:
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    dataset_path = Path(args.dataset)
    dataset_version = args.dataset_version or dataset_path.stem
    df = load_dataset(dataset_path)
    if (Path(args.models_dir) / args.version).exists():
        raise FileExistsError(f"model {args.version} already exists; pick a new version")
    validate_language(df, cfg)

    # Split muna bago training para hiwalay ang evaluation data.
    splits = split_dataset(df, cfg["split"], cfg["seed"], cfg["split"].get("group_column"))
    split_dir = Path(args.splits_dir) / dataset_version
    split_dir.mkdir(parents=True, exist_ok=True)
    for name in SPLITS:
        splits[name].to_csv(split_dir / f"{name}.csv", index=False, encoding="utf-8")
    sizes = {n: len(splits[n]) for n in SPLITS}
    print(f"split sizes: {sizes}")

    train, val, test = splits["train"], splits["val"], splits["test"]
    fitted, val_metrics = {}, {}
    candidates = cfg.get("candidates", list(classical.CANDIDATES))
    if cfg["transformer"]["enabled"] and "transformer" not in candidates:
        candidates.append("transformer")
    run_dir = Path(args.runs_dir) / args.version
    run_dir.mkdir(parents=True, exist_ok=True)

    # Kunin ang class labels ayon sa model type.
    def predict(name, model, texts):
        if name == "transformer":
            logits = model.logits(list(texts), batch_size=cfg["transformer"].get("eval_batch_size", 4))
            return [LABELS[i] for i in logits.argmax(axis=1)]
        return classical.predict_with_confidence(model, texts)[0]

    for name in candidates:
        if name == "transformer":
            from training.transformer import train_transformer

            pipe = train_transformer(train, val, cfg, save_dir=run_dir / "checkpoint")
        else:
            pipe = classical.CANDIDATES[name](cfg).fit(train["text"], train["label"])
        pred = predict(name, pipe, val["text"])
        fitted[name] = pipe
        val_metrics[name] = evaluate(list(val["label"]), pred, list(val["text"]))
        print(f"  {name}: val macro_f1={val_metrics[name]['macro_f1']:.3f}")

    metric = cfg["selection_metric"]
    # Validation score ang pipili ng candidate, hindi test score.
    best = max(val_metrics, key=lambda n: val_metrics[n][metric])
    print(f"selected on validation ({metric}): {best}")

    # I-evaluate lang ang selected candidate sa test split.
    pred = predict(best, fitted[best], test["text"])
    test_metrics = evaluate(list(test["label"]), pred, list(test["text"]))
    passed, failures = check_gate(test_metrics, cfg["acceptance_gate"])

    report = {
        "version": args.version, "dataset_version": dataset_version, "split_sizes": sizes,
        "selected": best, "validation": val_metrics, "test": test_metrics,
        "gate_passed": passed, "gate_failures": failures,
        "training_language": cfg.get("training_language"),
        "sources": df["source"].value_counts().to_dict() if "source" in df else {},
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"test macro_f1={test_metrics['macro_f1']:.3f} accuracy={test_metrics['accuracy']:.3f}; "
          f"report: {run_dir / 'report.json'}")

    # Failed model: package lang kung explicit ang --save-candidate.
    if not passed and not getattr(args, "save_candidate", False):
        print("ACCEPTANCE GATE FAILED, nothing packaged:", *failures, sep="\n  ")
        return 2
    out = package_model(
        fitted[best], version=args.version, model_type=best, cfg=cfg, metrics=test_metrics,
        dataset_path=dataset_path, dataset_version=dataset_version,
        models_dir=Path(args.models_dir), db_path=Path(args.db) if args.db else None,
    )
    print(f"packaged {out} (registered as Candidate; deploying is a separate step)")
    if not passed:
        print("Candidate saved for explicit development testing only; deployment gate FAILED:", *failures, sep="\n  ")
    return 0 if passed else 2


# Basahin ang CLI options at simulan ang training workflow.
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Train, evaluate, gate and package a classifier.")
    p.add_argument("dataset", type=Path)
    p.add_argument("--version", required=True, help="model version, e.g. v0.1")
    p.add_argument("--dataset-version", help="defaults to the dataset file name")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--models-dir", type=Path, default=backend_config.MODELS_DIR)
    p.add_argument("--runs-dir", type=Path, default=ROOT / "training" / "runs")
    p.add_argument("--splits-dir", type=Path, default=ROOT / "data" / "training" / "splits")
    p.add_argument("--db", type=Path, help="SQLite path (defaults to backend config)")
    p.add_argument("--save-candidate", action="store_true", help="save a failed-gate candidate for explicit development testing; never marks it Deployed")
    try:
        return run(p.parse_args(argv))
    except (ValueError, FileExistsError, RuntimeError, NotImplementedError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
