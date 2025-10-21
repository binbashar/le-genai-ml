# LangChain Structured Output with Amazon Bedrock

Enable structured output for ANY Bedrock model using LangChain.

## Quick Start

```bash
# Install dependencies
uv sync

# Configure AWS
export AWS_PROFILE=your-profile

# Open notebook
code demo.ipynb
```

## The Simple Rule

- **ChatBedrockConverse**: Native structured output works for ALL models
- **ChatBedrock**: Requires JsonOutputParser workaround

## Usage

```python
from structured_output import get_llm
from config import Model

# Recommended: ChatBedrockConverse (default)
llm = get_llm(Model.NOVA_MICRO)
result = llm.invoke("Your prompt")
print(result.answer)  # Pydantic model

# Legacy: ChatBedrock with JsonOutputParser
llm = get_llm(Model.NOVA_MICRO, use_bedrock_converse=False)
result = llm.invoke({"query": "Your prompt"})
print(result['answer'])  # Dictionary

# Custom output model
llm = get_llm(Model.CLAUDE_HAIKU, output=CustomModel)
result = llm.invoke("Your prompt")
```

## Project Structure

```
├── demo.ipynb           # Interactive examples
├── structured_output.py # Unified interface
├── config.py           # Model configuration
└── test_nova.py        # Validation tests
```

## Available Models

All models work with both approaches:
- **Nova** (`NOVA_MICRO`, `NOVA_LITE`, `NOVA_PRO`)
- **Claude 4.5** (`CLAUDE_HAIKU`, `CLAUDE_SONNET`)
- **OpenAI OSS** (`GPT_OSS_20B`, `GPT_OSS_120B`)

## Compatibility Notes

| Feature | ChatBedrockConverse | ChatBedrock |
|---------|-------------------|-------------|
| Structured Output | Native (`with_structured_output()`) | JsonOutputParser |
| All Models | Yes | Yes |
| Invoke Format | `llm.invoke("prompt")` | `llm.invoke({"query": "prompt"})` |
| Return Type | Pydantic Model | Dictionary |
| LangChain Recommendation | Recommended | Legacy |

## Requirements

- Python 3.13+
- AWS account with Bedrock access
- Models enabled in Bedrock console