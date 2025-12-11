# RAG Evaluation Guide

This guide explains how to run RAG (Retrieval-Augmented Generation) evaluations using the evaluation pipeline.

## Quick Start

```bash
# Evaluate retrieval + generation quality
./scripts/run_evaluation.sh config/runs/rag_example.yaml --wait

# Evaluate retrieval quality only
./scripts/run_evaluation.sh config/runs/rag_retrieve_only_example.yaml --wait
```

---

## 1. Evaluation Types

| Type | Description | Use Case |
|------|-------------|----------|
| `RAG_RETRIEVE_AND_GENERATE` | Evaluates both retrieval and generation quality | Full RAG pipeline assessment |
| `RAG_RETRIEVE_ONLY` | Evaluates only retrieval quality | Testing retriever/embedding quality |
| `MODEL` | Evaluates LLM responses from CloudWatch logs | Agent response quality |

---

## 2. Available Metrics

### RAG_RETRIEVE_AND_GENERATE Metrics

| Metric | Description | Requires Ground Truth |
|--------|-------------|----------------------|
| `Builtin.Faithfulness` | Is the response grounded in retrieved chunks? (hallucination detection) | No |
| `Builtin.Correctness` | Factual accuracy of response | Yes (`referenceResponses`) |
| `Builtin.Completeness` | How thorough is the response | Yes (`referenceResponses`) |
| `Builtin.Helpfulness` | Overall usefulness | No |
| `Builtin.CitationPrecision` | Are citations accurate? | No (requires `citations` in output) |
| `Builtin.CitationCoverage` | Is response supported by citations? | No (requires `citations` in output) |

### RAG_RETRIEVE_ONLY Metrics

| Metric | Description | Requires Ground Truth |
|--------|-------------|----------------------|
| `Builtin.ContextRelevance` | Are retrieved chunks relevant to the query? | No |
| `Builtin.ContextCoverage` | Do chunks cover required information? | Yes (`referenceResponses`) |

**Note**: `ContextRelevance` and `ContextCoverage` are ONLY available for `RAG_RETRIEVE_ONLY`, not for `RAG_RETRIEVE_AND_GENERATE`.

---

## 3. Configuration Files

### RAG_RETRIEVE_AND_GENERATE Config

Create a YAML file in `config/runs/`:

```yaml
# config/runs/rag_example.yaml
agent_name: "finance_personal_assistant"
evaluation_type: "RAG_RETRIEVE_AND_GENERATE"
dataset_path: "config/datasets/rag_sample.jsonl"
limit: 10

metrics:
  - "Builtin.Faithfulness"
  - "Builtin.Correctness"
  - "Builtin.Completeness"
```

### RAG_RETRIEVE_ONLY Config

```yaml
# config/runs/rag_retrieve_only_example.yaml
agent_name: "finance_personal_assistant"
evaluation_type: "RAG_RETRIEVE_ONLY"
dataset_path: "config/datasets/rag_retrieve_only_sample.jsonl"
limit: 10

metrics:
  - "Builtin.ContextRelevance"
  - "Builtin.ContextCoverage"
```

---

## 4. Dataset Formats (JSONL)

Each line in the JSONL file must be a valid JSON object with the `conversationTurns` wrapper.

### RAG_RETRIEVE_AND_GENERATE Format

```json
{
  "conversationTurns": [
    {
      "prompt": {
        "content": [
          {"text": "What is a good monthly budget for someone earning $6000?"}
        ]
      },
      "referenceResponses": [
        {
          "content": [
            {"text": "Ground truth response for Correctness/Completeness metrics..."}
          ]
        }
      ],
      "output": {
        "text": "The generated response from your RAG system...",
        "knowledgeBaseIdentifier": "your_agent_name",
        "retrievedPassages": {
          "retrievalResults": [
            {
              "content": {"text": "Retrieved chunk 1 text..."},
              "metadata": {"source": "document.pdf", "page": "5"}
            },
            {
              "content": {"text": "Retrieved chunk 2 text..."},
              "metadata": {"source": "document.pdf", "page": "6"}
            }
          ]
        }
      }
    }
  ]
}
```

**Key fields:**
- `output.text` - **Required**: The generated response
- `output.retrievedPassages.retrievalResults` - **Required**: Retrieved chunks
- `output.knowledgeBaseIdentifier` - **Required**: Must match agent_name
- `referenceResponses` - Optional: Ground truth for Correctness/Completeness metrics

### RAG_RETRIEVE_ONLY Format

```json
{
  "conversationTurns": [
    {
      "prompt": {
        "content": [
          {"text": "What are the tax benefits of a 401(k)?"}
        ]
      },
      "referenceResponses": [
        {
          "content": [
            {"text": "Ground truth response for ContextCoverage metric..."}
          ]
        }
      ],
      "output": {
        "knowledgeBaseIdentifier": "your_agent_name",
        "retrievedResults": {
          "retrievalResults": [
            {
              "content": {"text": "Retrieved chunk 1..."},
              "metadata": {"source": "doc.pdf", "page": "1"}
            },
            {
              "content": {"text": "Retrieved chunk 2..."},
              "metadata": {"source": "doc.pdf", "page": "2"}
            }
          ]
        }
      }
    }
  ]
}
```

**Key differences from RETRIEVE_AND_GENERATE:**
- No `output.text` field (no generation to evaluate)
- Uses `retrievedResults` instead of `retrievedPassages`
- `referenceResponses` required for `ContextCoverage` metric

**Important**: Do NOT include `referenceContexts` field - it causes validation errors with built-in metrics.

---

## 5. Running Evaluations

### Basic Usage

```bash
# Run and wait for completion
./scripts/run_evaluation.sh config/runs/rag_example.yaml --wait

# Run without waiting (check status later)
./scripts/run_evaluation.sh config/runs/rag_example.yaml
```

### What Happens

1. Script uploads your local JSONL dataset to S3
2. Triggers Step Functions evaluation pipeline
3. Creates Bedrock evaluation job
4. Polls until completion (~8 minutes)
5. Returns results with metric scores

### Example Output

```json
{
  "status": "SUCCEEDED",
  "evaluation_type": "RAG_RETRIEVE_AND_GENERATE",
  "metrics": ["Builtin.Faithfulness", "Builtin.Correctness", "Builtin.Completeness"],
  "eval_job": {
    "status": "Completed",
    "job_arn": "arn:aws:bedrock:us-west-2:123456789:evaluation-job/abc123"
  }
}
```

---

## 6. Viewing Results

Results are stored in S3. Download and view:

```bash
# Find the output file path from the execution output
aws s3 cp "s3://eval-pipeline-{account}-{region}/evaluation-results/{agent}/{timestamp}/.../output.jsonl" results.jsonl

# Pretty print
cat results.jsonl | python3 -c "import json,sys; [print(json.dumps(json.loads(l),indent=2)) for l in sys.stdin]"
```

### Result Structure

Each record includes metric scores with explanations:

```json
{
  "conversationTurns": [
    {
      "inputRecord": { "prompt": {...}, "referenceResponses": [...] },
      "output": { "text": "...", "retrievedPassages": {...} },
      "results": [
        {
          "metricName": "Builtin.Faithfulness",
          "result": 0.667,
          "evaluatorDetails": [
            {
              "modelIdentifier": "us.amazon.nova-pro-v1:0",
              "explanation": "Detailed explanation of the score..."
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 7. Sample Datasets

### Included Examples

| File | Type | Description |
|------|------|-------------|
| `config/datasets/rag_sample.jsonl` | RETRIEVE_AND_GENERATE | Budget allocation with relevant chunks |
| `config/datasets/rag_retrieve_only_sample.jsonl` | RETRIEVE_ONLY | 2 examples: high/low relevance chunks |

### Creating Test Data for Different Scores

**High scores (relevant chunks):**
- Chunks directly answer the question
- Content matches ground truth

**Low scores (irrelevant chunks):**
- Chunks about unrelated topics
- Content doesn't help answer the question

Example from `rag_retrieve_only_sample.jsonl`:

```
Question: "How do I set up automatic bill payments?"
Chunks: Mediterranean diet, gardening tips, car maintenance
Result: ContextRelevance = 0.0, ContextCoverage = 0.0
```

---

## 8. Metric Interpretation

| Score Range | Interpretation |
|-------------|----------------|
| 0.0 - 0.3 | Poor - significant issues |
| 0.3 - 0.6 | Fair - room for improvement |
| 0.6 - 0.8 | Good - minor issues |
| 0.8 - 1.0 | Excellent - meets expectations |

### Metric-Specific Guidance

**Faithfulness = 0.0**
- Response contains information not in the retrieved chunks
- Action: Improve prompt to constrain LLM to only use provided context

**ContextRelevance < 0.5**
- Retrieved chunks are not relevant to the query
- Action: Improve embedding model, chunking strategy, or retrieval parameters

**ContextCoverage < 0.5**
- Chunks don't contain information needed to answer
- Action: Add more relevant documents to knowledge base, improve indexing

---

## 9. Troubleshooting

### Common Errors

**"dataset entry prompt is not in the expected format"**
- Check JSONL structure matches the format above
- Ensure `conversationTurns` wrapper is present
- Verify all required fields exist

**"includes both reference contexts and reference responses"**
- Remove `referenceContexts` field for built-in metrics
- This field is only for custom metrics

**"metric is not available for RAG retrieveAndGenerate evaluations"**
- `ContextRelevance` and `ContextCoverage` are only for `RAG_RETRIEVE_ONLY`
- Use `Faithfulness`, `Correctness`, `Completeness` for `RAG_RETRIEVE_AND_GENERATE`

**"retrieveOnlySourceConfig is unknown"**
- The correct parameter name is `retrieveSourceConfig` (not `retrieveOnlySourceConfig`)
- This is handled automatically by the pipeline

---

## 10. Best Practices

1. **Start with sample datasets** - Use included examples before creating custom data
2. **Test one metric at a time** - Easier to debug issues
3. **Include ground truth** - Required for Correctness, Completeness, ContextCoverage
4. **Use descriptive agent names** - Helps organize results in S3
5. **Keep datasets small initially** - Faster iteration (limit: 10)

---

## 11. References

- [AWS Docs: RAG Evaluation Overview](https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation.html)
- [AWS Docs: Retrieve-Only Dataset Format](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-prompt-retrieve.html)
- [AWS Docs: Retrieve-and-Generate Dataset Format](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-evaluation-prompt-retrieve-generate.html)
- [AWS Blog: RAG Evaluation GA](https://aws.amazon.com/blogs/machine-learning/evaluate-models-or-rag-systems-using-amazon-bedrock-evaluations-now-generally-available/)
