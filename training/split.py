"""Train / validation / test split (thesis section 13.3).

Rows are assigned to splits by *group*, so near-identical items cannot land on both sides:
- group = value of `group_column` (e.g. url) when present, otherwise the normalized text.
- Each group gets its majority label; groups are shuffled per label and cut by the ratios,
  which keeps the class balance in every split.
Only exact-after-normalization duplicates are caught. Paraphrases and reposts that differ in
wording need a `group` column filled in at collection time.
"""
import numpy as np
import pandas as pd

from training.prepare.clean import dedupe_key

SPLITS = ("train", "val", "test")


def _group_ids(df: pd.DataFrame, group_column: str | None) -> pd.Series:
    keys = df["text"].map(dedupe_key)
    if group_column and group_column in df.columns:
        given = df[group_column].where(df[group_column].notna() & (df[group_column] != ""))
        return given.fillna(keys).astype(str)
    return keys


def split_dataset(
    df: pd.DataFrame, ratios: dict[str, float], seed: int, group_column: str | None = None
) -> dict[str, pd.DataFrame]:
    if abs(sum(ratios[s] for s in SPLITS) - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1")
    df = df.reset_index(drop=True).copy()
    df["_group"] = _group_ids(df, group_column)
    group_label = df.groupby("_group")["label"].agg(lambda s: s.value_counts().sort_index().idxmax())

    rng = np.random.RandomState(seed)
    assignment: dict[str, str] = {}
    for label, groups in group_label.groupby(group_label):
        ids = sorted(groups.index)
        rng.shuffle(ids)
        n = len(ids)
        if n < 3:
            raise ValueError(f"class '{label}' has only {n} group(s); need at least 3 to fill train/val/test")
        n_val = max(1, round(n * ratios["val"]))
        n_test = max(1, round(n * ratios["test"]))
        for i, gid in enumerate(ids):
            assignment[gid] = "val" if i < n_val else "test" if i < n_val + n_test else "train"

    df["_split"] = df["_group"].map(assignment)
    out = {s: df[df["_split"] == s].drop(columns=["_group", "_split"]).reset_index(drop=True) for s in SPLITS}
    for name, part in out.items():
        missing = set(df["label"]) - set(part["label"])
        if missing:
            raise ValueError(f"split '{name}' has no examples of {sorted(missing)}")
    return out
