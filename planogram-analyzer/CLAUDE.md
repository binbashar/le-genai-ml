# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
# Primary method - Streamlit
streamlit run app.py

# Docker (recommended for production)
docker-compose up --build

# Automated setup
./setup.sh
```

### Development Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Test AWS connection (verify credentials and Bedrock access)
python3 test_aws_connection.py

# Docker operations
docker-compose build --no-cache
docker-compose logs -f
docker-compose down
```

## Architecture Overview

This is a **Planogram Compliance Analyzer** that uses AI to compare retail shelf layouts (planograms) against actual store photos (realograms).

### Core Components
- **Main App** (`app.py`): Streamlit web interface with file upload, analysis controls, and results display
- **AWS Bedrock Client** (`utils/bedrock_client.py`): Handles LLM inference with Claude models for visual analysis
- **AWS Rekognition Client** (`utils/rekognition_client.py`): Object detection and text recognition
- **Image Processor** (`utils/image_processor.py`): PIL-based image optimization and enhancement
- **Authentication** (`utils/auth.py`): Simple login system

### Analysis Modes
1. **Bedrock-only**: Pure LLM visual analysis using Claude models
2. **Rekognition-only**: AWS computer vision for object detection
3. **Hybrid**: Combines both approaches for enhanced accuracy

### Configuration System
- **Models**: `config.yaml` defines available AI models (Claude 3.7 Sonnet, Claude 4 Opus, etc.)
- **Prompts**: Configurable system prompts with strict JSON output formatting
- **Environment**: `.env` file for AWS credentials and app settings

## Required Files for Analysis
1. **Planogram Image**: Expected shelf layout (JPG/PNG)
2. **Realogram Image**: Actual shelf photo (JPG/PNG)
3. **JSON Structure**: Product definitions with positions and expected quantities
4. **Expected JSON** (optional): For result validation

## Key Technical Details

### AWS Integration
- Requires valid AWS credentials with Bedrock and Rekognition permissions
- Models must be enabled in AWS Bedrock console
- Uses inference profiles for cross-region model access

### JSON Structure Format
```json
{
  "diferencias": [
    {
      "nivel": 1,
      "resultado": {
        "productos": [
          {
            "posicion_producto": 1,
            "nombre": "Product Name",
            "encontrado": null,
            "posicion_correcta": null,
            "frentes_esperados": 6,
            "frentes_encontrados": null
          }
        ]
      }
    }
  ],
  "conclusiones": []
}
```

### Authentication
- Default credentials: Username `Prisma`, Password `Binbash2025`
- Configurable via `APP_USER` and `APP_PASSWORD` environment variables

## Development Notes

### Environment Setup
1. Copy `env_example` to `.env` and configure AWS credentials
2. Ensure AWS Bedrock model access is enabled for your region
3. Run `./setup.sh` for automated environment configuration

### Image Processing
- Images are automatically resized (max 2048x2048) and enhanced for better AI analysis
- Supports contrast and sharpness improvements for product detection

### Docker Deployment
- Multi-stage build with non-root user for security
- Health checks and proper logging configuration
- Volume mounts for data persistence and development workflow