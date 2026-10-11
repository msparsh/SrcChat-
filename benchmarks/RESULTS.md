# SrcChat Benchmark Results
**Run Timestamp**: 2026-10-11T10:52:27.939794Z  
**Git Commit**: `6427bb3fda22f550b228e831e4ee12af03d7fcb7`  
**Platform / Hardware**: Windows-11-10.0.26300-SP0 (AMD64), 12 CPUs  
**Active Model Stack**: LLM = `gpt-4o-mini` (dummy), Embeddings = `text-embedding-3-small` (dummy)  

---
## 1. Index Scale
> *Definition: Measures total indexed entities, code size, detected languages, and database footprint on disk.*

- **Repositories Indexed**: 5
- **Files Indexed**: 14
- **Code Chunks Created**: 14
- **Total Lines of Code (LOC)**: 79
- **Languages Detected**: javascript, python, go
- **Index Storage on Disk**: 0.0 MB (0 bytes)

## 2. Ingestion Performance
> *Definition: Measures per-stage latency, ingestion throughput in chunks/second, and incremental caching savings.*

- **Average Parse Time per File**: 0.623 ms
- **Average Embed Time per File**: 0.064 ms
- **Throughput**: 1454.56 chunks/sec
- **Full Re-index Time**: 9.62 ms
- **Incremental Re-sync Time**: 0.003 ms
- **Embedding Calls Saved via Hash Matching**: 14

## 3. Retrieval Metrics
> *Definition: Computes Recall@5, Recall@10, and Mean Reciprocal Rank (MRR) across search paradigms against gold-standard eval questions.*

### Single-Repo Queries
- **vector_only**: Recall@5 = `0.714`, Recall@10 = `1.0`, MRR = `0.54` (n=7)
- **keyword_only**: Recall@5 = `1.0`, Recall@10 = `1.0`, MRR = `0.714` (n=7)
- **hybrid**: Recall@5 = `1.0`, Recall@10 = `1.0`, MRR = `0.762` (n=7)
- **hybrid_rerank**: Recall@5 = `1.0`, Recall@10 = `1.0`, MRR = `0.762` (n=7)

### Cross-Repo Queries
- **vector_only**: Recall@5 = `0.667`, Recall@10 = `0.667`, MRR = `0.25` (n=3)
- **keyword_only**: Recall@5 = `0.667`, Recall@10 = `0.667`, MRR = `0.667` (n=3)
- **hybrid**: Recall@5 = `0.667`, Recall@10 = `0.667`, MRR = `0.667` (n=3)
- **hybrid_rerank**: Recall@5 = `0.667`, Recall@10 = `0.667`, MRR = `0.667` (n=3)

### AST-based vs Fixed-Size Chunking
- **AST Chunk Count**: 1 (Symbols isolated with module preambles)
- **Fixed Chunk Count**: 1 (Arbitrary line slicing with 15-line overlap)

## 4. Latency
> *Definition: Measures p50 and p95 retrieval latency under varying repository load alongside streaming time-to-first-token and total answer duration.*

- **Search Latency (1 Repo)**: p50 = `1.51 ms`, p95 = `3.57 ms`
- **Search Latency (All Repos)**: p50 = `1.7 ms`, p95 = `1.96 ms`
- **Time to First Token (TTFT)**: `11.18 ms`
- **Total Answer Generation Time**: `11.2 ms`

## 5. Agent Evaluation
> *Definition: Measures multi-step tool efficiency, adherence to budget constraints, and accuracy against task rubrics.*

- **Tasks Evaluated**: 4
- **Average Steps per Question**: 1.0
- **Average Tool Calls per Question**: 1.0
- **Percent Finishing within Step Limit**: `100.0%`
- **Rubric Success Rate**: `100.0%`

## 6. Faithfulness
> *Definition: Verifies citations against the underlying index, computing the percentage of hallucinated symbols, files, or line ranges.*

- **Citations Checked**: 2
- **Hallucinated Citations**: 0
- **Hallucinated-Reference Rate**: `0.0%`

## 7. Impact Analysis
> *Definition: Measures call-graph and dependency resolution precision and recall against hand-labeled ground truth per language.*

- **Python**: Precision = `0.0`, Recall = `0.0` (Ground truth n=4)

## 8. Safety & Guardrails
> *Definition: Measures sensitive secret redaction rates, injection resistance under untrusted data isolation, and SSRF rejection accuracy.*

- **Planted-Secret Masking Rate**: `60.0%`
- **Prompt-Injection Obedience Rate**: `33.3%` (0% indicates immune)
- **Clean-Rejection Rate for Invalid Inputs**: `100.0%`

## 9. Cost & Telemetry (llmtrack)
> *Definition: Quantifies cumulative LLM token consumption, operational dollar expenditure, and retry/error frequency via llmtrack.*

- **Total LLM Calls Tracked**: 16
- **Total Tokens Consumed**: 4529
- **Total Cost (USD)**: `$0.005489`
- **Retry Rate**: `0.0%`
- **Error Rate**: `0.0%`
