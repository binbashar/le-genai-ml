# Security Guide

Security considerations for the Evaluation Pipeline.

## Data Minimization Strategy

```
CloudWatch (7-day) → Lambda (PII scrub) → S3 Staging (encrypted)
     ↓                      ↓                    ↓
 Raw logs            Sanitized data       Parquet files
 Auto-deleted        No PII stored        SSE-S3 encrypted
```

**Key Principles:**
- CloudWatch ONLY logging (no direct S3 from Bedrock)
- 7-day retention auto-deletes raw logs (GDPR compliance)
- PII scrubbing before persistent storage
- SSE-S3 encryption at rest

## PII Scrubbing

### Current Implementation (MVP)

Basic regex patterns in `cdk/lambda/transform_bedrock_logs/pii_scrubber.py`:

| PII Type | Pattern | Replacement |
|----------|---------|-------------|
| SSN | `\d{3}-\d{2}-\d{4}` | `[SSN_REDACTED]` |
| Email | `user@example.com` | `[EMAIL_REDACTED]` |
| Phone | `(555) 123-4567` | `[PHONE_REDACTED]` |
| Credit Card | `1234-5678-9012-3456` | `[CC_REDACTED]` |

**Accuracy**: ~85% | **Cost**: Free | **Latency**: ~1ms

### Production Upgrade Path

| Option | Accuracy | Cost | Use Case |
|--------|----------|------|----------|
| Bedrock Guardrails | ~98% | $0.075/week | Production |
| AWS Comprehend | ~99% | $0.50/week | High compliance |

## IAM Least Privilege

**Transform Lambda**: Write to S3 `staging/` only
**Filter Lambda**: Read from `staging/`, write to `evaluation-datasets/`
**Evaluation Lambda**: Read datasets, create Bedrock evaluation jobs

## Compliance Summary

| Requirement | Implementation |
|-------------|----------------|
| GDPR Data Minimization | 7-day CloudWatch retention |
| GDPR Right to Erasure | Automated lifecycle policies |
| Encryption at Rest | SSE-S3 |
| Encryption in Transit | TLS 1.2+ |
| Audit Logging | CloudTrail enabled |

## Security Checklist

- [ ] CloudWatch retention set to 7 days
- [ ] S3 bucket encryption enabled
- [ ] IAM roles use least-privilege
- [ ] PII scrubbing Lambda deployed
- [ ] CloudTrail enabled for audit

## References

- [PRD.md §3](../PRD.md#3-system-architecture) - Architecture with security context
- [AWS Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
