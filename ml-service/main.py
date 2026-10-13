"""
EpiNet Visualizer - ML Microservice
------------------------------------
This service simulates an attention-based epistasis (gene-gene interaction) detector.
It is a DEMO: no trained model is used. The interaction matrix is derived from
pairwise correlations + seeded random noise, normalized to resemble attention weights.

Architecture note: Replace the `_simulate_attention_matrix()` function with a
real trained attention/transformer model to convert this into a production pipeline.
"""

import hashlib
import io
import logging
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EpiNet ML Microservice",
    description="Simulated attention-based gene-gene interaction scorer (DEMO only).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The 10 pharmacogenomic genes this service expects
EXPECTED_GENES = [
    "CYP2D6", "CYP2C19", "CYP3A4", "CYP2C9",
    "VKORC1", "SLCO1B1", "TPMT", "DPYD", "UGT1A1", "ABCB1",
]
TOP_PAIRS_COUNT = 15


def _file_seed(content: bytes) -> int:
    """Derive a reproducible integer seed from file content hash."""
    return int(hashlib.sha256(content).hexdigest()[:8], 16)


def _simulate_attention_matrix(gene_df: pd.DataFrame, phenotype: pd.Series, seed: int) -> np.ndarray:
    """
    Stand-in for a trained attention model.

    Computes pseudo-attention weights by:
    1. Calculating absolute pairwise Pearson correlations between gene columns.
    2. Computing each gene's absolute correlation with the phenotype.
    3. Combining them with seeded random noise (scaled down to 15%).
    4. Applying row-wise softmax-style normalization to mimic attention weights.
    5. Symmetrizing and zeroing the diagonal.
    6. Min-max scaling to [0, 1].

    In a real pipeline this function would run a forward pass through a trained
    graph-attention or transformer model and return its learned attention matrix.
    """
    rng = np.random.default_rng(seed)
    n = len(EXPECTED_GENES)

    # Step 1: absolute pairwise correlations
    corr = gene_df[EXPECTED_GENES].corr().abs().values  # shape (n, n)

    # Step 2: phenotype correlations per gene
    pheno_corr = np.array([
        abs(gene_df[g].corr(phenotype)) for g in EXPECTED_GENES
    ])
    pheno_outer = np.outer(pheno_corr, pheno_corr)

    # Step 3: combine with noise
    noise = rng.random((n, n)) * 0.15
    raw = 0.60 * corr + 0.25 * pheno_outer + noise

    # Step 4: softmax-style row normalization
    exp_raw = np.exp(raw - raw.max(axis=1, keepdims=True))
    attention = exp_raw / exp_raw.sum(axis=1, keepdims=True)

    # Step 5: symmetrize and zero diagonal
    attention = (attention + attention.T) / 2.0
    np.fill_diagonal(attention, 0.0)

    # Step 6: scale to [0, 1]
    flat = attention.flatten().reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(flat).reshape(n, n)
    np.fill_diagonal(scaled, 0.0)

    return scaled


def _validate_and_load(content: bytes) -> tuple[pd.DataFrame, pd.Series, int]:
    """Parse CSV, validate columns, return (gene_df, phenotype, rows_processed)."""
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot parse CSV: {exc}")

    df.columns = df.columns.str.strip()
    missing_genes = [g for g in EXPECTED_GENES if g not in df.columns]
    if missing_genes:
        raise HTTPException(
            status_code=400,
            detail=f"Missing gene columns: {missing_genes}. "
                   f"Expected: {EXPECTED_GENES}",
        )
    if "sample_id" not in df.columns:
        raise HTTPException(status_code=400, detail="Missing required column: sample_id")
    if "phenotype" not in df.columns:
        raise HTTPException(status_code=400, detail="Missing required column: phenotype")

    gene_df = df[EXPECTED_GENES].apply(pd.to_numeric, errors="coerce")
    phenotype = pd.to_numeric(df["phenotype"], errors="coerce")

    if gene_df.isnull().all().any():
        raise HTTPException(status_code=400, detail="One or more gene columns are entirely non-numeric.")

    gene_df = gene_df.fillna(gene_df.mean())
    phenotype = phenotype.fillna(phenotype.mean())

    return gene_df, phenotype, len(df)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> dict[str, Any]:
    """
    Accept a pharmacogenomic CSV, run the simulated attention pipeline,
    and return an epistasis interaction matrix plus top pair scores.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    seed = _file_seed(content)
    gene_df, phenotype, rows_processed = _validate_and_load(content)

    logger.info("Analyzing %d rows, seed=%d", rows_processed, seed)
    matrix = _simulate_attention_matrix(gene_df, phenotype, seed)

    # Build top pairs list
    pairs: list[dict] = []
    n = len(EXPECTED_GENES)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append({
                "gene_a": EXPECTED_GENES[i],
                "gene_b": EXPECTED_GENES[j],
                "score": round(float(matrix[i, j]), 4),
            })
    top_pairs = sorted(pairs, key=lambda x: x["score"], reverse=True)[:TOP_PAIRS_COUNT]

    return {
        "genes": EXPECTED_GENES,
        "matrix": [[round(float(v), 4) for v in row] for row in matrix],
        "top_pairs": top_pairs,
        "meta": {
            "rows_processed": rows_processed,
            "simulated": True,
            "model": "mock-attention-v1",
        },
    }
