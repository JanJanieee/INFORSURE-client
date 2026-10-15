"""Gawing normalized vectors ang text para sa evidence search."""
from functools import lru_cache

import numpy as np

from .. import config


# I-load at i-cache ang embedding model sa GPU o CPU.
@lru_cache(maxsize=1)
def _model():
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer(config.EMBEDDING_MODEL, device=device)


# Gawing normalized vectors ang text para sa similarity search.
def embed(texts: list[str]) -> np.ndarray:
    vectors = _model().encode(
        list(texts), batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
    )
    return vectors.astype(np.float32)
