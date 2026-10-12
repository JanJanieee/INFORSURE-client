"""Sentence embeddings (thesis section 5; model per TECH_STACK.md).

`embed` returns L2-normalized float32 vectors, so cosine similarity is a plain dot product.
Tests replace `embed` with a small deterministic function instead of downloading the model.
"""
from functools import lru_cache

import numpy as np

from .. import config


@lru_cache(maxsize=1)
def _model():
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer(config.EMBEDDING_MODEL, device=device)


def embed(texts: list[str]) -> np.ndarray:
    vectors = _model().encode(
        list(texts), batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )
    return vectors.astype(np.float32)
