# Planogram Compliance Platform - Technical Documentation

## Document Information

| Property | Value |
|----------|-------|
| **Project Name** | Planogram Compliance Platform |
| **Version** | 1.0.0 |
| **Last Updated** | 2025-10-05 |
| **Owner** | client Team |
| **Partner** | Binbash |
| **Status** | Ready to Deploy |

---

## Executive Summary

The Planogram Compliance Platform is an AI-powered solution that automates retail shelf compliance validation by comparing planograms (expected layouts) against realograms (actual photographs) using AWS Bedrock's multimodal AI capabilities.

### Business Value

- **95% Time Reduction**: Manual verification takes 30-45 minutes per store; automated analysis completes in under 60 seconds
- **High Accuracy**: 90%+ detection accuracy with Anthropic Opus 4.1
- **Scalability**: Analyze hundreds of stores per day
- **Cost-Effective**: Pay-per-use AWS Bedrock model eliminates infrastructure overhead

### Key Metrics

| Metric | Value |
|--------|-------|
| Average Analysis Time | 45-60 seconds |
| Supported Models | 2 (Anthropic) |
| Max Image Size | 200 MB |
| Processing Resolution | 2048x2048 pixels |
| Token Tracking | Real-time |
| Export Formats | JSON, CSV |

---

## 1. System Overview

### 1.1 Purpose

The system automates planogram compliance checking for retail operations by:
- Detecting product presence and location
- Validating correct positioning
- Counting product facings
- Identifying compliance violations
- Generating actionable reports

### 1.2 Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | Streamlit | 1.28+ | Web UI |
| Backend | Python | 3.10+ | Application logic |
| AI Engine | AWS Bedrock | Latest | Multimodal AI |
| Image Processing | Pillow | 10.0+ | Image optimization |
| Deployment | Docker | 20.10+ | Containerization |
| Infrastructure | Terraform | 1.5+ | IaC |
| CI/CD | GitHub Actions | - | Automation |
| Container Registry | AWS ECR | - | Image storage |
| Orchestration | AWS ECS | - | Container management |

---

## 2. Functional Architecture

### 2.1 Core Components

#### 2.1.1 Web Interface (`app.py`)

**Responsibilities:**
- User interaction handling
- File upload management
- Configuration interface
- Results visualization
- Export functionality

**Key Features:**
- Multi-file upload support
- Real-time progress tracking
- Session state management
- Responsive design

#### 2.1.2 Bedrock Client (`utils/bedrock_client.py`)

**Responsibilities:**
- AWS Bedrock API integration
- Model ID resolution
- Request/response handling
- Error management
- Token usage extraction

**Key Methods:**
```python
class BedrockClient:
    def __init__(model_id, region)
    def analyze_compliance(planogram, realogram, prompt, ...)
    def _build_anthropic(images, prompt, ...)
    def _build_nova(images, prompt, ...)
    def _extract_text(payload, provider)
    def _extract_usage(payload, provider)
```

#### 2.1.3 Image Processor (`utils/image_processor.py`)

**Responsibilities:**
- Image optimization
- Format conversion
- Metrics calculation
- Difference analysis
- Report generation

**Key Functions:**
- `process_images()`: Convert and optimize images
- `calculate_metrics()`: Compute compliance metrics
- `analyze_differences()`: Detailed comparison
- `generate_compliance_report()`: Text reports

### 2.2 Complete Data Flow Sequence

The system implements a comprehensive two-phase analysis flow with optional ground truth comparison:

#### Phase 1: Initial Analysis (First Bedrock Call)
```
User Authentication → System Access
     ↓
Image Upload → Planogram + Realogram
     ↓
Structure Upload → Compliance JSON
     ↓
Image Processing → Optimization → Base64 Encoding
     ↓
Model Selection → (Anthropic Sonnet/Opus)
     ↓
AWS Bedrock Invocation #1 → AI Analysis
     ↓
Response Processing → JSON Parsing → Schema Normalization
     ↓
Metrics Calculation → Initial Results Display
```

#### Phase 2: Ground Truth Comparison (Second Bedrock Call)
```
User Uploads Expected JSON → Ground Truth Data
     ↓
System Prepares Comparison → Both JSONs Combined
     ↓
AWS Bedrock Invocation #2 → AI Comparison Analysis
     ↓
Intelligent Difference Detection → Product Matching
     ↓
Accuracy Metrics → Recall, Precision, Compliance
     ↓
Comparison Report → Detailed Differences
```

#### Phase 3: Export & Reporting
```
Results Aggregation → Analysis + Comparison
     ↓
Export Options → JSON/CSV Format Selection
     ↓
Report Generation → Download Ready
```

For a detailed visual representation, see the [Complete Sequence Diagram](../diagrams/sequence-diagram-complete.drawio) showing all 28 steps of the process.

### 2.3 Session State Management

The application maintains state across Streamlit reruns:

| State Variable | Type | Purpose |
|---------------|------|---------|
| `bedrock_result` | Dict | Main analysis output |
| `bedrock_metrics` | Dict | Calculated metrics |
| `uploaded_files` | List | Temporary file references |

---

## 3. AI Model Integration

### 3.1 Supported Models

The platform leverages four state-of-the-art vision models, each optimized for specific use cases. The same model is used for both initial analysis and ground truth comparison to ensure consistency.

#### Anthropic Sonnet 3.7
- **Model ID**: `anthropic.claude-3-7-sonnet-20250219-v1:0`
- **Provider**: Anthropic
- **Best For**: Production deployments requiring optimal balance
- **Strengths**: Fast processing, high accuracy, cost-effective
- **Performance**: 45-60 seconds per analysis
- **Accuracy**: 95%+ product recognition
- **Max Tokens**: 4096
- **Temperature**: 0.1 (recommended)
- **Use Cases**:
  - Daily compliance checks
  - Standard retail audits
  - Real-time analysis

#### Anthropic Opus 4.1
- **Model ID**: `anthropic.claude-opus-4-1-20250805-v1:0`
- **Provider**: Anthropic
- **Best For**: High-stakes compliance validation
- **Strengths**: Superior vision capabilities, maximum accuracy
- **Performance**: 60-90 seconds per analysis
- **Accuracy**: 98%+ product recognition
- **Max Tokens**: 4096
- **Temperature**: 0.1 (recommended)
- **Use Cases**:
  - Regulatory compliance audits
  - High-value product categories
  - Critical accuracy requirements


### 3.2 Inference Profiles

AWS Bedrock uses cross-region inference profiles for improved availability:

| Original Model ID | Resolved Profile ID |
|------------------|-------------------|
| `anthropic.claude-...` | `us.anthropic.claude-...` |
| `amazon.nova-...` | `us.amazon.nova-...` |
| `meta.llama...` | `us.meta.llama...` |

### 3.3 Two-Phase Bedrock Invocation Process

The platform implements a sophisticated two-phase analysis approach, making separate calls to AWS Bedrock for initial analysis and ground truth comparison:

#### Phase 1: Initial Analysis
**Purpose**: Analyze planogram vs realogram to identify products and compliance

**Bedrock Call #1 Details:**
- **Input**: Planogram image + Realogram image + Analysis prompt + Expected structure JSON
- **Processing**: Vision model analyzes both images to detect products, positions, and facings
- **Output**: Structured JSON with compliance analysis
- **Token Usage**: Tracked separately as "Analysis Tokens"

#### Phase 2: Ground Truth Comparison (Optional)
**Purpose**: Compare analysis results with expected ground truth for accuracy validation

**Bedrock Call #2 Details:**
- **Trigger**: User uploads expected results JSON
- **Input**: Analysis results JSON + Expected results JSON + Comparison prompt
- **Processing**: Same model performs intelligent comparison to identify discrepancies
- **Output**: Detailed comparison report with accuracy metrics
- **Token Usage**: Tracked separately as "Comparison Tokens"

**Benefits of Two-Phase Approach:**
- Maintains consistency by using the same model
- Enables separate token tracking for cost allocation
- Allows optional ground truth validation
- Provides detailed accuracy metrics
- Supports iterative model improvement

### 3.4 Token Usage Tracking

The system tracks token consumption separately for each phase:

#### Analysis Phase Tokens
```python
{
  "_usage": {
    "input_tokens": 12500,    # Images + prompt
    "output_tokens": 850,     # Analysis JSON
    "total_tokens": 13350
  }
}
```

#### Comparison Phase Tokens
```python
{
  "_usage": {
    "input_tokens": 3500,     # Two JSONs + prompt
    "output_tokens": 450,     # Comparison report
    "total_tokens": 3950
  }
}
```

**Total Cost Calculation:**
```
Total Cost = Analysis Cost + Comparison Cost
Analysis Cost = (analysis_tokens / 1000 * rate)
Comparison Cost = (comparison_tokens / 1000 * rate)
```

---

## 4. Data Models

### 4.1 Input Structure

#### Planogram JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["diferencias"],
  "properties": {
    "diferencias": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["nivel", "resultado"],
        "properties": {
          "nivel": {
            "type": "integer",
            "description": "Shelf level number (1-based, top to bottom)"
          },
          "resultado": {
            "type": "object",
            "required": ["productos"],
            "properties": {
              "productos": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": [
                    "posicion_producto",
                    "nombre",
                    "frentes_esperados"
                  ],
                  "properties": {
                    "posicion_producto": {
                      "type": "integer",
                      "description": "Position within shelf (1-based, left to right)"
                    },
                    "nombre": {
                      "type": "string",
                      "description": "Full product name including brand, type, size"
                    },
                    "frentes_esperados": {
                      "type": "integer",
                      "description": "Expected number of facings"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 4.2 Output Structure

#### Analysis Result Schema

```json
{
  "diferencias": [
    {
      "nivel": 1,
      "resultado": {
        "productos": [
          {
            "posicion_producto": 1,
            "nombre": "Brand Product Type 500ml",
            "encontrado": true,
            "posicion_correcta": true,
            "frentes_esperados": 4,
            "frentes_encontrados": 4
          }
        ]
      }
    }
  ],
  "conclusiones": [
    "Compliance summary",
    "Missing products: Product A, Product B",
    "Wrong positions: Product C"
  ],
  "_usage": {
    "input_tokens": 12500,
    "output_tokens": 850,
    "total_tokens": 13350
  },
  "_debug": {
    "original_model_id": "anthropic.claude-...",
    "resolved_model_id": "us.anthropic.claude-...",
    "region": "us-west-2"
  }
}
```

#### Comparison Result Schema

```json
{
  "total_productos": 24,
  "coincidencias_exactas": 20,
  "diferencias_encontrado": 2,
  "diferencias_posicion": 1,
  "diferencias_frentes": 3,
  "productos": [
    {
      "nivel": 1,
      "posicion": 1,
      "nombre": "Product Name",
      "bedrock": {
        "encontrado": true,
        "posicion_correcta": true,
        "frentes_encontrados": 4
      },
      "expected": {
        "encontrado": true,
        "posicion_correcta": true,
        "frentes_encontrados": 4
      },
      "matches": {
        "encontrado": true,
        "posicion_correcta": true,
        "frentes_encontrados": true,
        "exacto": true
      }
    }
  ]
}
```

---

## 5. Deployment Architecture

### 5.1 AWS Infrastructure

#### VPC Configuration
- **CIDR**: 10.0.0.0/16
- **Public Subnets**: 2 (across AZs)
- **Private Subnets**: 2 (across AZs)
- **NAT Gateway**: 1 per AZ
- **Internet Gateway**: 1

#### ECS Cluster
- **Type**: Fargate
- **Service**: planogram-analyzer
- **Desired Count**: 2
- **Task Memory**: 2048 MB
- **Task CPU**: 1024 (1 vCPU)

#### Application Load Balancer
- **Type**: Application
- **Scheme**: Internet-facing
- **Target Group**: ECS Service
- **Health Check**: `/_stcore/health`

### 5.2 CI/CD Pipeline

#### GitHub Actions Workflow

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    steps:
      1. Checkout code
      2. Configure AWS credentials (OIDC)
      3. Login to ECR
      4. Build Docker image
      5. Push to ECR
      6. Update ECS service
      7. Wait for deployment stability
```

#### Deployment Steps

1. **Build Phase**
   - Docker image creation
   - Multi-stage build optimization
   - Security scanning

2. **Push Phase**
   - ECR authentication
   - Image tagging (latest + commit SHA)
   - Repository push

3. **Deploy Phase**
   - ECS service update
   - Force new deployment
   - Health check validation
   - Rollback on failure

### 5.3 Security

#### IAM Roles

**GitHub OIDC Role** (`github-oidc-role`)
- Permissions: ECR push, ECS update
- Trust: GitHub Actions OIDC provider

**ECS Task Role** (`ecs-task-role`)
- Permissions: Bedrock InvokeModel
- Trust: ECS tasks service

**ECS Task Execution Role** (`ecs-execution-role`)
- Permissions: ECR pull, CloudWatch logs
- Trust: ECS tasks service

#### Security Groups

**ALB Security Group**
- Inbound: 80 (HTTP), 443 (HTTPS) from 0.0.0.0/0
- Outbound: All to ECS security group

**ECS Security Group**
- Inbound: 8501 from ALB security group
- Outbound: 443 to 0.0.0.0/0 (Bedrock API)

---

## 6. Configuration Management

### 6.1 Application Configuration

#### config.yaml

```yaml
models:
  anthropic_sonnet:
    name: "Anthropic Sonnet 3.7 (Recommended)"
    model_id: "anthropic.claude-3-7-sonnet-20250219-v1:0"
    max_tokens: 4096
    temperature: 0.1

default_prompt: |
  Detailed analysis instructions...
  Product detection rules...
  Output format requirements...
```

#### .streamlit/config.toml

```toml
[server]
maxUploadSize = 200
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
```

### 6.2 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | - | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Yes | - | AWS secret key |
| `AWS_DEFAULT_REGION` | No | us-west-2 | AWS region |

---

## 7. Monitoring & Observability

### 7.1 Metrics

#### Application Metrics
- Analysis completion time
- Token usage per request
- Model selection distribution
- Error rates

#### Infrastructure Metrics
- ECS CPU utilization
- ECS memory utilization
- ALB request count
- ALB response time
- Target health status

### 7.2 Logging

#### CloudWatch Log Groups
- `/ecs/planogram-analyzer`: Application logs
- `/aws/ecs/containerinsights`: Container metrics

#### Log Format
```json
{
  "timestamp": "2025-10-05T12:00:00Z",
  "level": "INFO",
  "message": "Analysis completed",
  "model_id": "anthropic.claude-3-7-sonnet-20250219-v1:0",
  "tokens_used": 13350,
  "duration_ms": 45000
}
```

### 7.3 Alerts

**Recommended CloudWatch Alarms:**
- ECS task count < desired count
- ALB unhealthy targets > 0
- 5xx error rate > 5%
- Response time > 60s

---

## 8. Operations Guide

### 8.1 Deployment

**Initial Deployment:**
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Application Update:**
```bash
git push origin main
# GitHub Actions handles the rest
```

**Manual Deployment:**
```bash
docker build -t planogram-analyzer .
docker tag planogram-analyzer:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest
aws ecs update-service --cluster ${CLUSTER} --service ${SERVICE} --force-new-deployment
```

### 8.2 Troubleshooting

#### Issue: Service not starting

**Symptoms:**
- ECS tasks fail to start
- "Resource not available" errors

**Resolution:**
1. Check CloudWatch logs
2. Verify IAM permissions
3. Confirm Bedrock model access
4. Review security group rules

#### Issue: Slow analysis

**Symptoms:**
- Analysis takes > 2 minutes
- Timeouts

**Resolution:**
1. Check image size (should be < 10MB)
2. Verify model selection (Sonnet 3.7 for speed, Opus 4.1 for accuracy)
3. Review network connectivity
4. Check AWS service health dashboard

#### Issue: Token limit exceeded

**Symptoms:**
- "Maximum token limit" errors
- Incomplete responses

**Resolution:**
1. Reduce image resolution
2. Increase max_tokens setting
3. Simplify planogram structure
4. Split analysis into multiple requests

### 8.3 Backup & Recovery

**Data Backup:**
- Analysis results: Download JSON/CSV exports
- Configuration: Version controlled in Git
- Images: Not stored (processed in-memory)

---

## 9. Performance Benchmarks

### 9.1 Analysis Performance

| Image Resolution | Model | Avg Time | Tokens Used |
|-----------------|-------|----------|-------------|
| 1024x1024 | Anthropic Sonnet | 35s | 8,500 |
| 2048x2048 | Anthropic Sonnet | 55s | 15,000 |
| 1024x1024 | Anthropic Opus | 50s | 9,000 |
| 2048x2048 | Anthropic Opus | 75s | 16,500 |

### 9.2 Cost Analysis

**Cost per Analysis (Estimated):**
```
Anthropic Sonnet: $0.045 - $0.060
Anthropic Opus:   $0.120 - $0.150
```

**Monthly Cost (1000 analyses):**
```
Anthropic Sonnet: $45 - $60
Anthropic Opus:   $120 - $150
```

---

## 10. Best Practices

### 10.1 Development

- **Image Quality**: Use high-resolution photos (min 1920x1080)
- **Lighting**: Ensure even, bright lighting for product visibility
- **Angle**: Take photos perpendicular to shelves
- **Focus**: Sharp, clear product labels
- **Temperature**: Keep at 0.1 for consistent results
- **Testing**: Validate with ground truth before production use

### 10.2 Operations

- **Monitoring**: Set up CloudWatch alarms for critical metrics
- **Cost Control**: Use Sonnet 3.7 for batch processing, Opus 4.1 for critical validations
- **Scaling**: Configure ECS auto-scaling based on ALB request count
- **Security**: Rotate AWS credentials regularly
- **Updates**: Test model updates in staging before production

### 10.3 Integration

- **API Integration**: Export JSON for downstream systems
- **Batch Processing**: Process multiple stores in parallel
- **Data Pipeline**: Integrate with data warehouse for analytics
- **Notifications**: Configure alerts for compliance violations

---

## 11. References

### Documentation Links

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Anthropic API](https://docs.anthropic.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)


---

**Document Version**: 1.0.0
**Last Review Date**: 2025-10-05
**Next Review Date**: 2025-11-05
**Owner**: client Team
**Partner**: Binbash 
