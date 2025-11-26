# PRD - Evaluation Pipeline

**Version**: 3.0 | **Status**: Complete | **Last Updated**: 2025-11-25

> Quick reference: See [CLAUDE.md](CLAUDE.md) for deployment commands and architecture overview.

## Problem

AgentCore agents in production need systematic quality evaluation using LLM-as-a-judge metrics without modifying agent code.

## Solution

Automated pipeline that:
1. Captures Bedrock invocation logs via CloudWatch → Firehose → S3
2. Transforms logs to Parquet with PII scrubbing
3. Runs on-demand evaluations via Step Functions → Bedrock Evaluation API

## Components

| Component | Purpose | Runtime |
|-----------|---------|---------|
| Transform Lambda | Firehose → Parquet | Python 3.13, 512MB, 3min |
| Filter Lambda | Parquet → JSONL | Python 3.13 Docker, 512MB, 5min |
| Evaluation Job Lambda | CreateEvaluationJob API | Python 3.13, 256MB, 1min |
| Poll Status Lambda | Job status polling | Python 3.13, 256MB, 1min |
| Process Results Lambda | Metrics aggregation | Python 3.13, 512MB, 5min |
| Step Functions | Orchestration | 7 states, ~8min execution |
| Web UI | Trigger interface | Next.js 15 |

## Cost Estimate

Weekly evaluation (100 questions):
- CloudWatch + Firehose + Lambda + S3: ~$0.01
- Bedrock Evaluation: ~$0.04
- **Total: ~$0.05/week**

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Parquet for staging | Columnar format, 3-5x compression, Athena-ready |
| CloudWatch 7-day retention | GDPR compliance, cost optimization |
| Agent name from identity.arn | Accurate AgentCore Runtime identification |
| Nova Pro as judge | Cost-effective, good accuracy |

## References

- [CLAUDE.md](CLAUDE.md) - Quick start and commands
- [SCHEMAS.md](SCHEMAS.md) - Data format specifications
- [cdk/README.md](cdk/README.md) - Infrastructure deployment
- [ui/README.md](ui/README.md) - Web UI setup
