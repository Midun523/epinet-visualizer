# LinkedIn Post — EpiNet Visualizer

---

**Why does the same drug work brilliantly for one patient and fail another — even when both carry the "right" variant?**

Because no single gene tells the whole story. Drug metabolism is a network phenomenon. The moment you start modeling gene-gene interactions (epistasis), the picture changes entirely.

That's what drove me to build **EpiNet Visualizer** — a full-stack pharmacogenomics dashboard that takes a CSV of gene expression data, runs it through a simulated attention-based scoring pipeline, and returns an interactive gene network showing which pairs interact most strongly to influence drug response.

Here's what's under the hood:

**☕ Spring Boot (Java 21)**
- Async REST API — upload returns immediately (202), frontend polls every 2 s
- Spring Data JPA + MySQL 8 for run persistence
- Global exception handler, file validation (type, size, required columns), CORS config

**⚛️ React 18 + Vite + Tailwind CSS 3**
- Force-directed gene interaction network (react-force-graph-2d) — edge thickness scales with score, threshold slider, click-to-highlight
- Sortable, filterable biomarker pairs table + Recharts score bar chart
- Full analysis history — reload any past result

**🐍 Python + FastAPI (ML microservice)**
- POST /analyze accepts the CSV and returns a symmetric 10×10 interaction matrix
- Simulated attention weights: pairwise correlations + phenotype signal + seeded noise, softmax-normalized
- 13 pytest tests covering shape, symmetry, determinism, and all error paths

**Important transparency note:** the ML component uses simulated attention weights — not a trained model. This is intentional. The architecture is built to accept a real pharmacogenomic attention or graph-transformer model with a single function swap. Honesty in demo projects matters.

🔗 **[REPO LINK]** | 📸 **[SCREENSHOT/GIF]**

I'd love feedback from anyone working at the intersection of bioinformatics, AI drug discovery, and clinical informatics — this is the space I want to build in.

#Bioinformatics #ComputationalBiology #SpringBoot #React #AIDrugDiscovery #Pharmacogenomics
