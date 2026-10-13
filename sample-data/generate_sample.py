"""
generate_sample.py
------------------
Generates a sample pharmacogenomic CSV with 200 rows for testing EpiNet Visualizer.
Each gene column contains simulated continuous expression/activity values.
The phenotype column is a continuous drug-response score derived from gene interactions.

Usage:
    python generate_sample.py
Output:
    sample_pharmacogenomics.csv  (in the same directory)
"""

import random
import numpy as np
import pandas as pd

SEED = 42
N_ROWS = 200
GENES = ["CYP2D6", "CYP2C19", "CYP3A4", "CYP2C9",
         "VKORC1", "SLCO1B1", "TPMT", "DPYD", "UGT1A1", "ABCB1"]

rng = np.random.default_rng(SEED)

# Simulate correlated gene expression values
mean = rng.uniform(0.3, 0.7, len(GENES))
cov_base = rng.uniform(-0.2, 0.2, (len(GENES), len(GENES)))
cov = cov_base @ cov_base.T + np.eye(len(GENES)) * 0.5
gene_values = rng.multivariate_normal(mean, cov, size=N_ROWS)

# Clip to reasonable range [0, 1]
gene_values = np.clip(gene_values, 0.0, 1.0)

# Phenotype: weighted combination of gene interactions + noise (continuous drug response)
weights = rng.uniform(-1.0, 1.0, len(GENES))
phenotype = gene_values @ weights + rng.normal(0, 0.05, N_ROWS)

df = pd.DataFrame(gene_values, columns=GENES)
df.insert(0, "sample_id", [f"SAMPLE_{i+1:03d}" for i in range(N_ROWS)])
df["phenotype"] = phenotype

out_path = "sample_pharmacogenomics.csv"
df.to_csv(out_path, index=False, float_format="%.6f")
print(f"Generated {out_path}  ({N_ROWS} rows, {len(GENES)} gene columns, 1 phenotype column)")
