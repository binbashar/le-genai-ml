# CLAUDE.md - Claude Code Assistant Instructions

## Context Management for Streamlit Demo Implementation

### When Working with Tasks

**IMPORTANT**: When reading or implementing any task from `tasks.md`, always load the related context files to maintain full understanding:

1. **For ANY task implementation**, read in this order:
   - `PRD.md` - Product vision and scope
   - `requirements.md` - Functional specifications (REQ-XXX references)
   - `design.md` - Technical patterns and code examples
   - `tasks.md` - The specific task to implement

2. **Task Context Mapping**:
   - **TASK-1 (Foundation)** → References REQ-001, REQ-002 → See design.md section 4.1
   - **TASK-2 (Interface)** → References REQ-003 to REQ-005 → See design.md section 4.2
   - **TASK-3 (Streaming)** → References REQ-006 to REQ-012 → See design.md sections 4.3-4.4
   - **TASK-4 (Refinement)** → References REQ-013 to REQ-017 → See design.md error handling
   - **TASK-5 (Validation)** → References REQ-020, REQ-021 → See all documentation

### Implementation Guidelines

When implementing the demo:

1. **Always start by reading the full context** - Don't rely on task description alone
2. **Follow the design patterns** in design.md - The 50-line implementation is the target
3. **Verify requirements** - Each task maps to specific REQ-XXX items
4. **Keep it simple** - This is a demo for a live event, not production code

### Code Patterns to Follow

From design.md, the core streaming pattern is:
```python
for line in response["response"].iter_lines():
    if line.startswith(b"data: "):
        event = json.loads(line[6:])
        if event.get("type") == "thinking":
            st.caption(f"🔧 {event.get('message')}")
        elif event.get("type") == "stream_token":
            st.write(event.get("token", ""), end="")
```

### Project Context

- **Event**: AWS GenAI Loft FinTech Event in San Francisco
- **Goal**: Demonstrate AWS AgentCore's streaming and tool orchestration
- **Persona**: Sarah Chen (Tech Professional, $180K income)
- **Scenarios**: Finance Assistant (budgeting) and Market Trends (portfolio)
- **Target**: ~50-100 lines of code in single app.py file
- **Region**: us-west-2 (closest to San Francisco)

### AWS Authentication

**IMPORTANT**: This project always uses AWS SSO with a specific profile.

- **Profile**: `binbash`
- **Login Command**: `aws sso login --profile binbash`
- **Environment Variable**: `AWS_PROFILE=binbash`

**Before running any AWS commands or the demo:**
```bash
# Login to AWS SSO
aws sso login --profile binbash

# Verify connection
aws sts get-caller-identity --profile binbash
```

**When running the Streamlit app:**
```bash
# Set profile for the session
export AWS_PROFILE=binbash

# Run the app
uv run streamlit run app.py
```

### File Reading Order for Full Context

```bash
# When starting implementation, read all documentation:
cat PRD.md          # Understand the vision
cat requirements.md  # Understand the behaviors
cat design.md        # Understand the patterns
cat tasks.md         # Understand the work
```

### Key Decisions Already Made

1. **No offline mode** - Trust AgentCore connection
2. **Hard-coded configuration** - Demo reliability over flexibility
3. **Single file implementation** - app.py only
4. **Direct SSE parsing** - No generators or abstractions
5. **Minimal error handling** - Simple message only
6. **Python 3.13+** with uv package manager

### Remember

This is a live demo at an AWS event. The code should be:
- **Reliable** - It must work during the presentation
- **Simple** - Easy to debug if issues arise
- **Visual** - Show tool orchestration clearly
- **Fast** - 5-minute demo maximum

When in doubt, choose simplicity over sophistication.