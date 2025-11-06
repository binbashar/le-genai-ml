# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This directory contains production-ready utilities for the Finance Personal Assistant agent. These modules handle document processing, vision analysis, guardrails, session management, and memory retrieval. All utilities are designed as independent, reusable components with comprehensive error handling.

**Parent context:** This `utils/` directory is part of the production finance personal assistant agent located at `../`. See parent CLAUDE.md files for full deployment workflows and architecture patterns.

## Module Architecture

### Document Processing Pipeline

**Vision Analysis** (`vision_analyzer.py` + `vision_context.py`):
- Uses Amazon Nova Premier for financial document recognition
- Detects receipts/invoices and extracts structured data (merchant, date, total, items, category)
- Returns normalized response: `{"status": "success"|"unknown"|"error", "keywords": [], "summary": str, "data": {}}`
- Context injection pattern: `inject_vision_context(user_message, vision_result)`

**PDF Processing** (`pdf_processor.py`):
- Converts first page of PDF to JPEG image using PyMuPDF
- Output can be passed directly to `vision_analyzer.analyze_image()`
- 2x zoom (144 DPI) for OCR-quality rendering
- Returns base64-encoded JPEG or None on error

**CSV Processing** (`csv_processor.py`):
- Converts base64 CSV to plain text with security sanitization
- **CSV formula injection prevention**: Sanitizes `=`, `+`, `-`, `@` at cell start
- Smart negative number handling: "-123.45" allowed, "-2+5" (formula) sanitized
- Multi-encoding support: UTF-8, UTF-8-sig, ISO-8859-1, CP1252
- 5MB size limit with graceful error handling

### Security Layer

**Guardrail Management** (`guardrail.py`):
- Creates production-grade guardrails with AWS best practices
- Content filters: SEXUAL, VIOLENCE, HATE, INSULTS, MISCONDUCT, PROMPT_ATTACK (all HIGH)
- Word policy: 19 gambling terms + PROFANITY managed list
- PII protection: EMAIL, PHONE, NAME, ADDRESS (ANONYMIZE); SSN, CREDIT_DEBIT_CARD_NUMBER (BLOCK)
- Contextual grounding: GROUNDING, RELEVANCE (threshold: 0.7)
- Functions: `create_gambling_guardrail()`, `get_gambling_guardrail_id()`, `delete_gambling_guardrail()`, `create_guardrail_version()`

**Guardrail Pre-Check** (`guardrail_sanitize.py`):
- Uses AWS Bedrock ApplyGuardrail API to validate text WITHOUT model invocation
- **Pre-check pattern**: Validates user input BEFORE agent processing to prevent conversation history contamination
- Function: `apply_guardrail_text(text, guardrail_id=None, guardrail_arn=None, guardrail_version="1", source="INPUT")`
- Returns: `{"action": "NONE"|"GUARDRAIL_INTERVENED", "sanitized_text": str, "is_safe": bool}`
- Fail-safe design: API errors default to allowing content (avoids blocking legitimate queries)

### Session & Memory Management

**Session Management** (`session_manager.py`):
- Protocol-based pattern for extracting session/actor context from AgentCore Runtime
- Actor ID extraction priority: 1) `payload["actor_id"]` (most reliable), 2) Request header `X-Amzn-Bedrock-AgentCore-Runtime-Custom-User-Id`, 3) Default: "user"
- Session ID validation: Minimum 33 characters (AgentCore Memory requirement), auto-generates UUID if invalid
- Immutable `SessionContext` dataclass: `session_id`, `actor_id`, `is_generated_session`
- Factory function: `extract_session_context(context, payload=None, extractor=None)`

**Memory Retrieval** (`memory_retrieval.py`):
- Simple LTM retrieval utility for injecting context into agent prompts
- Function: `retrieve_and_inject_memories(memory_client, memory_id, actor_id, user_message, namespaces={})`
- Namespaces format: `{"namespace_template": top_k}` where template uses `{actorId}` placeholder
- Labels memories by type: `[User Preference]`, `[Financial Fact]`, `[Memory]`
- Returns augmented message with `<retrieved_memories>` XML tags

## Common Patterns

### Vision Analysis Workflow

```python
# In main.py entrypoint
from utils.vision_analyzer import analyze_image
from utils.vision_context import inject_vision_context
from utils.pdf_processor import pdf_first_page_to_image

# Handle image upload
image_base64 = payload.get("image_base64")
if image_base64:
    vision_result = analyze_image(image_base64=image_base64)
    user_message = inject_vision_context(user_message, vision_result)

# Handle PDF upload (convert to image first)
document_base64 = payload.get("document_base64")
filename = payload.get("filename", "")
if filename.endswith(".pdf"):
    converted_image = pdf_first_page_to_image(document_base64)
    if converted_image:
        payload["image_base64"] = converted_image
        # Process as image...
```

### CSV Processing Workflow

```python
# In main.py entrypoint
from utils.csv_processor import csv_to_text

document_base64 = payload.get("document_base64")
filename = payload.get("filename", "")
if filename.endswith(".csv"):
    csv_text = csv_to_text(document_base64)
    if csv_text:
        user_message = f"""[CSV File Data]
{csv_text}

User Query: {user_message}"""
```

### Guardrail Pre-Check Pattern

```python
# In main.py entrypoint (BEFORE agent invocation)
from config import get_guardrail_config
from utils.guardrail_sanitize import apply_guardrail_text

guardrail_config = get_guardrail_config()
if guardrail_config:
    pre_check_result = apply_guardrail_text(
        text=user_message,
        guardrail_id=guardrail_config.get("guardrail_id"),
        guardrail_version=guardrail_config.get("guardrail_version"),
        source="INPUT",
    )

    if not pre_check_result["is_safe"]:
        # Return intervention WITHOUT invoking agent
        yield {"type": "final", "result": "I can't assist with that request."}
        return
```

**Key insight:** Pre-check prevents blocked content from entering conversation history, avoiding re-triggering on subsequent turns.

### Session Context Extraction

```python
# In main.py entrypoint
from utils.session_manager import extract_session_context

@app.entrypoint
async def invoke(payload, context):
    session_ctx = extract_session_context(context, payload)

    # Use in memory session manager
    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=AgentCoreMemoryConfig(
            memory_id=memory.memory_id,
            session_id=session_ctx.session_id,
            actor_id=session_ctx.actor_id
        ),
        retrieval_config=RETRIEVAL_CONFIG,
        region_name=region
    )
```

### Memory Retrieval for LTM

```python
# In main.py entrypoint (after session context extraction)
from utils.memory_retrieval import retrieve_and_inject_memories

# Define namespaces to retrieve from
namespaces = {
    "finance-assistant/user/{actorId}/preferences": 5,  # Top-5 user preferences
    "finance-assistant/user/{actorId}/facts": 10,       # Top-10 financial facts
}

# Inject LTM context into user message
user_message = retrieve_and_inject_memories(
    memory_client=memory._client,
    memory_id=memory.memory_id,
    actor_id=session_ctx.actor_id,
    user_message=user_message,
    namespaces=namespaces
)

# Now pass augmented message to agent
response = agent(user_message)
```

## Testing Utilities Individually

All utilities are designed to be testable independently:

```bash
# Test vision analysis (requires sample image)
# Create test_utils_vision.py:
from utils.vision_analyzer import analyze_image
import base64

with open("sample_receipt.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode()

result = analyze_image(image_base64)
print(result)

# Run test
uv run python test_utils_vision.py

# Test CSV processing
# Create test_utils_csv.py:
from utils.csv_processor import csv_to_text
import base64

csv_content = b"Date,Amount\n2024-01-01,100.00"
csv_base64 = base64.b64encode(csv_content).decode()
text = csv_to_text(csv_base64)
print(text)

uv run python test_utils_csv.py

# Test session extraction
# Create test_utils_session.py:
from utils.session_manager import extract_session_context
from dataclasses import dataclass

@dataclass
class MockContext:
    session_id: str = "test-session-id-12345678901234567890123"
    request_headers: dict = None

context = MockContext()
payload = {"actor_id": "test_user"}
session_ctx = extract_session_context(context, payload)
print(f"Session: {session_ctx.session_id}, Actor: {session_ctx.actor_id}")

uv run python test_utils_session.py
```

## Design Principles

### Error Handling Philosophy

All utilities follow a **graceful degradation** pattern:
- Vision analysis errors → Return `{"status": "error"}` with descriptive summary
- PDF conversion errors → Return `None` (caller handles fallback)
- CSV decoding errors → Return `None` with logged warnings
- Guardrail API errors → **Fail-safe**: Allow content (avoid blocking legitimate queries)
- Session extraction errors → Generate UUID session ID, use default actor ID

### Security Patterns

**CSV Formula Injection Prevention:**
- Dangerous characters: `=`, `+`, `@`, `\t`, `\r` at cell start
- Smart handling: "-123.45" (negative number) allowed, "-2+5" (formula) sanitized
- Method: Prefix dangerous cells with single quote (`'`)

**PII Protection (via Guardrails):**
- ANONYMIZE: EMAIL, PHONE, NAME, ADDRESS → Replaced with placeholder tags `[EMAIL-1]`, `[PHONE-1]`
- BLOCK: SSN, CREDIT_DEBIT_CARD_NUMBER → Reject entire request/response

**Fail-Safe Design:**
- Guardrail API errors default to allowing content (prevents false positives)
- Vision API errors return structured error response (system continues)
- Document processing errors return None (caller decides fallback strategy)

### Immutability & Type Safety

**Session Management:**
- `SessionContext` is a frozen dataclass (immutable after creation)
- Protocol-based `AgentCoreContextExtractor` for extensibility without inheritance

**Vision Analysis:**
- Normalized response format enforced: `{"status": str, "keywords": list, "summary": str, "data": dict}`
- All return types explicitly documented in docstrings

### Logging Strategy

All modules use Python's `logging` module consistently:
- `logger.info()`: Normal operation (e.g., "Successfully decoded CSV with utf-8 encoding")
- `logger.warning()`: Recoverable issues (e.g., "CSV file too large: 6.5MB (max: 5MB)")
- `logger.error()`: Errors with context (e.g., "Failed to process CSV: <exception>", exc_info=True)
- `logger.debug()`: Verbose details (e.g., "Vision model response: {...}")

## Configuration Dependencies

These utilities depend on configuration from parent modules:

**From `../config.py`:**
- `get_region()`: Returns AWS region for Bedrock clients
- `get_guardrail_config()`: Returns `{"guardrail_id": str, "guardrail_version": str}` or `None`

**From `../memory_config.py`:**
- `RETRIEVAL_CONFIG`: Memory retrieval strategies (USER_PREFERENCE, SEMANTIC, SUMMARY)

**Environment variables:**
- `AWS_REGION`: AWS region (fallback chain: env var → boto3 config → default "us-west-2")
- `AWS_PROFILE`: AWS credentials profile (default: "binbash")

## Model Configuration

**Vision model (Amazon Nova Premier):**
- Model ID: `us.amazon.nova-premier-v1:0` (inference profile for cross-region routing)
- Temperature: 0.1 (deterministic extraction)
- Max tokens: 4096

**Guardrail models:**
- Guardrails are model-agnostic (apply to any Bedrock model)
- Use numbered versions for production (e.g., version="1"), DRAFT for testing

## Integration Points

**Called by:**
- `../main.py`: Orchestrator entrypoint (uses all utilities)
- `../budget_agent.py`: May use memory retrieval
- `../financial_analysis_agent.py`: May use session context

**Depends on:**
- `../config.py`: Model and region configuration
- `../memory_config.py`: Memory retrieval strategies
- `../../libs/python/`: Shared libraries (not directly imported by utils)

## Common Issues & Solutions

### Vision Analysis Returns "unknown"

**Symptom:** Vision model returns `{"status": "unknown"}` for financial documents

**Diagnosis:**
```bash
# Check model access
aws bedrock list-foundation-models --region us-west-2 --query "modelSummaries[?contains(modelId, 'nova-premier')]"

# Check image encoding
# Ensure image is JPEG/PNG, properly base64-encoded
```

**Solutions:**
- Verify model access enabled in Bedrock Console
- Check image format (JPEG/PNG only, no HEIC/WebP)
- Reduce image size (<5MB) before base64 encoding
- Check CloudWatch Logs for vision model errors

### CSV Formula Injection Not Sanitized

**Symptom:** Dangerous formulas like `=2+5` not sanitized

**Diagnosis:**
```python
# Test sanitization directly
from utils.csv_processor import _sanitize_csv_formulas

test_csv = "Name,Formula\nTest,=2+5"
sanitized = _sanitize_csv_formulas(test_csv)
print(sanitized)  # Should show: Name,Formula\nTest,'=2+5
```

**Solutions:**
- Check regex patterns in `_sanitize_csv_formulas()`: line 101-104
- Verify negative numbers still work: "-123.45" should NOT be sanitized
- Update patterns if new formula injection vectors discovered

### Guardrail Pre-Check Blocking Legitimate Content

**Symptom:** Valid financial queries blocked by guardrails

**Diagnosis:**
```bash
# Check guardrail configuration
aws bedrock get-guardrail --guardrail-identifier <id> --guardrail-version 1

# Test pre-check directly
uv run python -c "
from utils.guardrail_sanitize import apply_guardrail_text
result = apply_guardrail_text(
    text='I want to invest $10,000 in stocks',
    guardrail_id='<id>',
    guardrail_version='1'
)
print(result)
"
```

**Solutions:**
- Review word policy in `guardrail.py`: lines 64-88 (gambling terms)
- Adjust content filter thresholds (currently HIGH)
- Create new guardrail version with refined policies
- Temporarily disable guardrails: `aws ssm delete-parameter --name "/agentcore/finance-personal-assistant/guardrail-config"`

### Session ID Validation Fails

**Symptom:** Auto-generated session IDs even when provided

**Diagnosis:**
```python
# Check session ID length
session_id = "test-session"
print(f"Length: {len(session_id)} (minimum: 33)")

# Verify context object structure
from utils.session_manager import extract_session_context
# Add breakpoint and inspect context.session_id
```

**Solutions:**
- Ensure provided session IDs are 33+ characters (AgentCore requirement)
- Check if `context.session_id` exists (might be None in local testing)
- Use auto-generated UUIDs for local testing (36 characters)

### Memory Retrieval Returns Empty Context

**Symptom:** `retrieve_and_inject_memories()` returns original message (no memories)

**Diagnosis:**
```bash
# Check if memories exist in namespace
aws bedrock-agentcore list-memory-events \
    --memory-id <memory-id> \
    --max-results 10

# Verify namespace format
# Should use {actorId} placeholder, not hardcoded values
```

**Solutions:**
- Verify memories were stored in correct namespace
- Check `actor_id` matches between storage and retrieval
- Ensure `top_k` value is reasonable (5-10 for most use cases)
- Review relevance threshold in `../memory_config.py`

## Module Interdependencies

**No circular dependencies:**
- All modules are independent (no imports between utils modules)
- Parent modules (`../main.py`, `../config.py`) import from utils, not vice versa

**Import graph:**
```
utils/vision_analyzer.py → ../config.py (get_region)
utils/vision_context.py → (no dependencies)
utils/csv_processor.py → (no dependencies)
utils/pdf_processor.py → (no dependencies)
utils/session_manager.py → (no dependencies)
utils/guardrail.py → (no dependencies)
utils/guardrail_sanitize.py → (no dependencies)
utils/memory_retrieval.py → (no dependencies)
```

All utilities only import standard library, boto3, or third-party packages (Pillow, PyMuPDF).
