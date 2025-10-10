# Planogram Compliance Platform

> AI-powered visual compliance analysis for retail planogram validation using AWS Bedrock

[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-orange)](https://aws.amazon.com/bedrock/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [AI Models](#ai-models)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🎯 Overview

The Planogram Compliance Platform is an enterprise-grade solution that leverages AWS Bedrock's multimodal AI capabilities to automatically analyze and validate retail product placement against planogram specifications. The system compares expected shelf layouts (planograms) with actual in-store photographs (realograms) to identify compliance issues.

### Key Capabilities

- **Visual AI Analysis**: Uses Anthropic models via AWS Bedrock
- **Multi-Product Detection**: Identifies products, positions, and facings count
- **Compliance Validation**: Compares actual vs. expected product placement
- **Ground Truth Comparison**: AI-powered intelligent comparison with expected results
- **Token Usage Tracking**: Real-time monitoring of API consumption
- **Export Capabilities**: JSON, CSV, and PDF report generation

## ✨ Features

### Core Features

- 🤖 **Multi-Model AI Support**
  - Anthropic Sonnet 3.7 (Recommended)
  - Anthropic Opus 4.1 (Most Accurate)

- 📊 **Comprehensive Analysis**
  - Product presence detection
  - Position accuracy verification
  - Facings count validation
  - Missing products identification
  - Wrong placement detection

- 📈 **Intelligent Comparison**
  - AI-powered ground truth validation
  - Product matching by name and position
  - Detailed difference reporting
  - Accuracy metrics calculation

- 💾 **Data Export**
  - JSON structured output
  - CSV tabular format
  - Compliance reports
  - Token usage metrics

- 🔧 **Advanced Configuration**
  - Custom prompts support
  - Adjustable temperature settings
  - Token limit configuration
  - Model selection

## 🏗 Architecture

### System Architecture

The platform uses a multi-layered architecture deployed on AWS with high availability and scalability.

#### AWS Infrastructure
![AWS Architecture](docs/diagrams/architecture.drawio)

The infrastructure includes:
- **VPC** with public/private subnets across multiple AZs
- **Application Load Balancer** for traffic distribution
- **ECS Fargate** for serverless container orchestration
- **NAT Gateways** for secure outbound internet access
- **ECR** for container image storage
- **CloudWatch** for monitoring and logging
- **Secrets Manager** for credential management
- **AWS Bedrock** for AI model inference

#### Application Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│                    (Streamlit Web UI)                        │
├─────────────────────────────────────────────────────────────┤
│  • File Upload Manager                                       │
│  • Configuration Interface                                   │
│  • Results Visualization                                     │
│  • Export Generator                                          │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│                       (app.py)                               │
├─────────────────────────────────────────────────────────────┤
│  • Session State Management                                  │
│  • Business Logic Orchestration                              │
│  • Data Validation & Processing                              │
│  • Metrics Calculation Engine                                │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
├───────────────────────┬───────────────────────────────────────┤
│  BedrockClient        │  ImageProcessor                       │
│  • Model Resolution   │  • Image Optimization                 │
│  • API Communication  │  • Format Conversion                  │
│  • Token Tracking     │  • Base64 Encoding                   │
│  • Error Handling     │  • Quality Enhancement                │
└───────────────────────┴───────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                         │
│                  (AWS SDK - Boto3)                           │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│                    AWS Bedrock Runtime                       │
├─────────────────────────────────────────────────────────────┤
│  • Anthropic Models (Sonnet 3.7, Opus 4.1)                  │
│  • Cross-Region Inference Profiles                           │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

![Complete Sequence Diagram](docs/diagrams/sequence-diagram-complete.drawio)

The complete analysis and comparison flow consists of five main phases:

#### Phase 1: Initial Setup
- User authentication
- Upload planogram and realogram images
- Upload compliance structure JSON
- Configure analysis parameters
- Select AI model (Anthropic Sonnet or Opus)

#### Phase 2: Image Processing
- Image optimization and resizing (max 2048x2048)
- Format conversion to RGB
- Base64 encoding for API transmission
- Session state management

#### Phase 3: Initial AI Analysis (First Bedrock Call)
- Model ID resolution to inference profile (adds us. prefix)
- Request body construction based on provider (Anthropic)
- AWS Bedrock API invocation
- AI model processing (45-60 seconds typical)
- Token usage tracking for analysis
- JSON response parsing and normalization

#### Phase 4: Ground Truth Comparison (Second Bedrock Call)
- User uploads expected results JSON
- System prepares comparison prompt
- **Second invocation to AWS Bedrock** for intelligent comparison
- AI analyzes differences between:
  - Analysis results from Phase 3
  - Expected ground truth JSON
- Token usage tracking for comparison
- Detailed difference report generation

#### Phase 5: Results & Export
- Display analysis results with metrics
- Show comparison results if ground truth provided
- Calculate accuracy metrics:
  - Recall (products found)
  - Precision (correct positions)
  - Facings compliance
- Export options:
  - JSON structured output
  - CSV tabular format
  - Comparison report

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Streamlit | Web UI for user interaction |
| **Session Manager** | Streamlit State | Maintains data across requests |
| **Analysis Engine** | Python | Business logic orchestration |
| **BedrockClient** | Boto3 | AWS Bedrock API integration |
| **ImageProcessor** | Pillow | Image optimization & encoding |
| **Metrics Calculator** | Python | Compliance metrics computation |
| **Export Handler** | Python | JSON/CSV generation |

### Infrastructure Components

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **VPC** | Network isolation | 10.0.0.0/16 CIDR |
| **ALB** | Load balancing | Internet-facing |
| **ECS Fargate** | Container hosting | 2GB RAM, 1 vCPU |
| **NAT Gateway** | Outbound internet | Per AZ |
| **ECR** | Container registry | Private repository |
| **CloudWatch** | Monitoring & logs | 30-day retention |
| **Secrets Manager** | Credential storage | Auto-rotation enabled |
| **IAM** | Access control | Least privilege |

## 📦 Prerequisites

### Required

- **Python**: 3.10 or higher
- **AWS Account**: With Bedrock access enabled
- **AWS Credentials**: Configured via environment variables, AWS CLI, or IAM roles
- **Model Access**: Request access to desired models in AWS Bedrock console

### Supported Models

Ensure you have access to at least one of the following:

| Model | Model ID | Recommended For |
|-------|----------|-----------------|
| Anthropic Sonnet 3.7 | `anthropic.claude-3-7-sonnet-20250219-v1:0` | General use |
| Anthropic Opus 4.1 | `anthropic.claude-opus-4-1-20250805-v1:0` | High accuracy |

### AWS Permissions

Required IAM permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*",
        "arn:aws:bedrock:us-west-2:*:inference-profile/*"
      ]
    }
  ]
}
```

## 🚀 Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd clientVisionBinBash
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure AWS credentials**

   Option A: Environment variables
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-west-2
   ```

   Option B: AWS CLI
   ```bash
   aws configure
   ```

   Option C: Create `.env` file
   ```bash
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_DEFAULT_REGION=us-west-2
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

6. **Access the interface**
   ```
   http://localhost:8501
   ```

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t planogram-analyzer .
   ```

2. **Run the container**
   ```bash
   docker run -p 8501:8501 \
     -e AWS_ACCESS_KEY_ID=your_key \
     -e AWS_SECRET_ACCESS_KEY=your_secret \
     -e AWS_DEFAULT_REGION=us-west-2 \
     planogram-analyzer
   ```

### AWS ECS Deployment

See [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for detailed infrastructure setup using Terraform.

## ⚙️ Configuration

### Model Configuration (`config.yaml`)

```yaml
models:
  anthropic_sonnet:
    name: "Anthropic Sonnet 3.7 (Recommended)"
    model_id: "anthropic.claude-3-7-sonnet-20250219-v1:0"
    max_tokens: 4096
    temperature: 0.1

default_prompt: |
  Your analysis prompt here...
```

### Streamlit Configuration (`.streamlit/config.toml`)

```toml
[server]
maxUploadSize = 200
enableCORS = false
enableXsrfProtection = false
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_DEFAULT_REGION` | AWS region | `us-west-2` |

## 📖 Usage

### Basic Workflow

1. **Upload Images**
   - Planogram: Image showing expected product layout
   - Realogram: Photo of actual shelf

2. **Configure Analysis**
   - Select AI model
   - Choose prompt mode (default/custom)
   - Set temperature (0.1 recommended)
   - Adjust max tokens if needed

3. **Provide Expected Structure**
   - Upload compliance JSON with product list
   - Include nivel (shelf level) and product details

4. **Run Analysis**
   - Click "START COMPLIANCE ANALYSIS"
   - Wait for AI processing
   - Review token usage

5. **Review Results**
   - View JSON output
   - Check compliance metrics
   - Export data (JSON/CSV)

6. **Optional: Ground Truth Comparison**
   - Upload expected results JSON
   - AI compares Bedrock vs Expected
   - Review accuracy metrics

### Expected JSON Structure

```json
{
  "diferencias": [
    {
      "nivel": 1,
      "resultado": {
        "productos": [
          {
            "posicion_producto": 1,
            "nombre": "Product Name Brand 500ml",
            "encontrado": true,
            "posicion_correcta": true,
            "frentes_esperados": 4,
            "frentes_encontrados": 4
          }
        ]
      }
    }
  ]
}
```

### Output Format

**Analysis Result:**
```json
{
  "diferencias": [...],
  "conclusiones": [
    "List of findings",
    "Missing products",
    "Compliance issues"
  ],
  "_usage": {
    "input_tokens": 12500,
    "output_tokens": 850,
    "total_tokens": 13350
  }
}
```

**Comparison Result:**
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

## 🤖 AI Models

The platform supports multiple state-of-the-art vision models through AWS Bedrock, each optimized for different use cases. All models are used for both initial analysis and ground truth comparison phases.

### Available Models

#### 1. Anthropic Sonnet 3.7
- **Model ID**: `anthropic.claude-3-7-sonnet-20250219-v1:0`
- **Provider**: Anthropic
- **Best For**: Production deployments requiring balance of speed and accuracy
- **Capabilities**: Advanced visual understanding, product recognition, spatial reasoning
- **Usage**: Primary model for retail compliance analysis

#### 2. Anthropic Opus 4.1
- **Model ID**: `anthropic.claude-opus-4-1-20250805-v1:0`
- **Provider**: Anthropic
- **Best For**: High-accuracy requirements, critical compliance checks
- **Capabilities**: Superior visual analysis, detailed product differentiation
- **Usage**: When accuracy is paramount over cost


### Model Comparison

| Feature | Anthropic Sonnet 3.7 | Anthropic Opus 4.1 |
|---------|----------------------|--------------------|
| Accuracy | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Speed | Fast (45-60s) | Moderate (60-90s) |
| Cost | Medium | High |
| Max Tokens | 4096 | 4096 |
| Vision Quality | Excellent | Superior |
| Product Recognition | 95%+ | 98%+ |
| Position Accuracy | High | Very High |
| Facings Detection | Excellent | Excellent |

### Model Selection Guidelines

#### By Use Case
- **Production Deployment**: Anthropic Sonnet 3.7 (best overall balance)
- **Compliance Audits**: Anthropic Opus 4.1 (maximum accuracy)
- **High Volume Processing**: Anthropic Sonnet 3.7 (balanced performance)
- **Development/Testing**: Anthropic Sonnet 3.7 (cost-effective)

#### By Priority
- **Accuracy First**: Opus 4.1 > Sonnet 3.7
- **Speed First**: Sonnet 3.7 > Opus 4.1
- **Cost First**: Sonnet 3.7 > Opus 4.1

### How Models Are Used

Both the initial analysis and comparison phases utilize the same selected model:

1. **Initial Analysis**: Model analyzes planogram vs realogram to identify products
2. **Ground Truth Comparison**: Same model compares analysis results with expected JSON

This ensures consistency in the AI's understanding throughout the process.

## 🌐 Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  planogram-analyzer:
    build: .
    ports:
      - "8501:8501"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=us-west-2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### GitHub Actions CI/CD

The project includes automated deployment via GitHub Actions:

1. **Build**: Docker image creation
2. **Push**: ECR upload
3. **Deploy**: ECS service update
4. **Verify**: Health check validation

See `.github/workflows/deploy.yml` for pipeline configuration.

### Infrastructure as Code (Terraform)

Complete AWS infrastructure defined in `terraform/`:

- VPC and networking
- ECS cluster and service
- ECR repository
- Load balancer
- Security groups
- IAM roles and policies

## 📚 API Reference

### BedrockClient

#### Constructor
```python
client = BedrockClient(
    model_id: str,
    region: str = "us-east-1"
)
```

#### Methods

**analyze_compliance**
```python
result = client.analyze_compliance(
    planogram_b64: str,      # Base64 encoded planogram image
    realogram_b64: str,      # Base64 encoded realogram image
    prompt: str,             # Analysis instructions
    json_structure: Dict,    # Expected output structure
    temperature: float = 0.1,
    max_tokens: int = 4096
) -> Dict
```

### Image Processor

**process_images**
```python
base64_str = process_images(
    image_file: UploadedFile
) -> str
```

**calculate_metrics**
```python
metrics = calculate_metrics(
    result: Dict
) -> Dict[str, Any]
```

**analyze_differences**
```python
analysis = analyze_differences(
    result: Dict,
    expected: Dict = None
) -> List[Dict]
```

## 🔧 Troubleshooting

### Common Issues

**Issue**: Model not supported error
```
ValidationException: Invocation of model ID ... isn't supported
```
**Solution**: Use inference profile format `us.{model_id}` or switch region to `us-west-2`

**Issue**: AWS credentials not found
```
AWS credentials not found
```
**Solution**: Configure credentials via environment variables, AWS CLI, or IAM roles

**Issue**: Token limit exceeded
```
Token limit exceeded
```
**Solution**: Reduce image size or increase `max_tokens` parameter

**Issue**: Image upload fails
```
File too large
```
**Solution**: Images are auto-resized to 2048x2048. Check `.streamlit/config.toml` maxUploadSize

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check `_debug` field in response:
```json
{
  "_debug": {
    "original_model_id": "anthropic.claude...",
    "resolved_model_id": "us.anthropic.claude...",
    "region": "us-west-2"
  }
}
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to new functions
- Include docstrings for public methods
- Write tests for new features
- Update documentation

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

For support, please contact:
- Email: support@example.com
- Issue Tracker: GitHub Issues
- Documentation: [docs.example.com](https://docs.example.com)

## 🙏 Acknowledgments

- AWS Bedrock team for multimodal AI capabilities
- Anthropic for AI models
- Streamlit team for the excellent framework
- Open source community

---

**Built with ❤️ using AWS Bedrock and Streamlit**
