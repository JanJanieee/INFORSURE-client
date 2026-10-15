"""Deploy, list, and undeploy classifier versions (thesis sections 13.7, 13.8, 14).

A model becomes the live model only if it passed its acceptance gate. At most one model is Deployed at a time
(enforced by a unique index); deploying a new one retires the previous one.

Usage (py -m backend.app.deploy ...):
    list
    deploy VERSION [--allow-dev-model]
    undeploy

`--allow-dev-model` is the explicit, visible override for models trained with a disabled gate (training/configs/dev.json).
A model that FAILS a real gate can never be deployed.
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path

from . import config, db
from .pipeline.model_store import ModelNotAvailable, check_supported, read_metadata, validate_artifacts


def list_models(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT model_version, deployment_status, dataset_version, trained_at FROM model_versions "
        "ORDER BY created_at, model_version"
    ).fetchall()


def _is_disabled_gate(gate: dict) -> bool:
    return gate.get("min_macro_f1", 0) <= 0 and gate.get("min_per_class_recall", 0) <= 0


def deploy(conn: sqlite3.Connection, version: str, models_dir: Path | None = None, allow_dev_model: bool = False) -> str:
    """Make `version` the live model. Returns a short message; raises ValueError when it must not be deployed."""
    from training.evaluate import check_gate

    row = conn.execute("SELECT deployment_status FROM model_versions WHERE model_version = ?", (version,)).fetchone()
    if row is None:
        raise ValueError(f"model '{version}' is not registered (run training first)")
    model_dir = os.path.join(str(models_dir or config.MODELS_DIR), version)
    try:
        metadata = read_metadata(model_dir)
        check_supported(metadata)
        validate_artifacts(model_dir, metadata)
    except ModelNotAvailable as exc:
        raise ValueError(str(exc)) from exc
    gate, metrics = metadata.get("acceptance_gate"), metadata.get("metrics")
    if not gate or not metrics:
        raise ValueError("metadata has no acceptance gate or metrics; refusing to deploy")
    passed, failures = check_gate(metrics, gate)
    if not passed:
        raise ValueError("model fails its acceptance gate: " + "; ".join(failures))
    note = ""
    if _is_disabled_gate(gate):
        if not allow_dev_model:
            raise ValueError(
                "model was trained with a disabled acceptance gate (dev). "
                "Pass --allow-dev-model to deploy it anyway; never do this for real results."
            )
        note = " WARNING: dev model deployed with a disabled gate; do not report its results."

    with conn:
        conn.execute("UPDATE model_versions SET deployment_status = 'Retired' WHERE deployment_status = 'Deployed'")
        conn.execute("UPDATE model_versions SET deployment_status = 'Deployed' WHERE model_version = ?", (version,))
    return f"deployed {version}." + note


def undeploy(conn: sqlite3.Connection) -> int:
    with conn:
        return conn.execute(
            "UPDATE model_versions SET deployment_status = 'Retired' WHERE deployment_status = 'Deployed'"
        ).rowcount


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("deploy")
    d.add_argument("version")
    d.add_argument("--allow-dev-model", action="store_true")
    sub.add_parser("undeploy")
    args = p.parse_args(argv)

    db.init_db()
    try:
        with db.connect() as conn:
            if args.cmd == "list":
                for r in list_models(conn):
                    print(f"{r['model_version']:<20} {r['deployment_status']:<10} dataset={r['dataset_version']} trained={r['trained_at']}")
            elif args.cmd == "deploy":
                print(deploy(conn, args.version, allow_dev_model=args.allow_dev_model))
            else:
                print(f"{undeploy(conn)} model(s) retired")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
