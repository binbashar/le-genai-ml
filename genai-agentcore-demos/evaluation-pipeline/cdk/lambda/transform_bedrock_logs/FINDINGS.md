# Lambda Deployment - Resolution

## Issue: Container Image → Zip Deployment Migration
Container image deployment failed with `Runtime.InvalidEntrypoint`. Migrated to zip with CDK bundling.

## Solution: Architecture-Aligned Bundling
```python
lambda_.Function(
    architecture=lambda_.Architecture.X86_64,  # Runtime architecture
    code=lambda_.Code.from_asset(
        "lambda/transform_bedrock_logs",
        bundling=BundlingOptions(
            platform="linux/amd64",  # Force x86_64 for PyArrow wheels
            command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"]
        )
    )
)
```

## Critical: Platform Mismatch Prevention
- **PyArrow requires architecture-specific binaries** (ARM64 vs x86_64)
- Set `architecture=X86_64` + `platform="linux/amd64"` together
- CDK bundling auto-selects correct wheel (`manylinux_2_28_x86_64`)

## Result
✅ Lambda transformation working
✅ Parquet files in S3: `staging/agent_name=*/date=*/part-*.parquet`
✅ Pipeline: Bedrock → CloudWatch → Firehose → Lambda → S3
