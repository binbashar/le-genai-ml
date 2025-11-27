# Tasks Document
## AWS AgentCore FinTech Demo - Strategic Implementation Tasks

### Overview
Build a minimal viable demo that showcases AgentCore's streaming and tool orchestration capabilities. Focus on working software over comprehensive features.

---

## [x] TASK-1: Foundation
**Goal**: Get a basic Streamlit app running
**Time**: ~20 minutes
**Context**: See requirements REQ-001, REQ-002

Create a working environment and verify AWS connectivity. The outcome should be a runnable Streamlit application, even if empty.

**Done when**: `streamlit run app.py` works

---

## [x] TASK-2: Interface
**Goal**: Build the demo UI with Sarah Chen persona
**Time**: ~30 minutes
**Context**: See requirements REQ-003 to REQ-005, design.md section 4.2

Create the single-page interface with tabs for both agents. Focus on clean presentation suitable for projection.

**Done when**: UI shows tabs, persona, and button

---

## [x] TASK-3: Streaming Integration
**Goal**: Connect to AgentCore with real-time responses
**Time**: ~45 minutes
**Context**: See requirements REQ-006 to REQ-012, design.md sections 4.3-4.4

Implement the core functionality - calling agents and streaming their responses with visible tool execution messages.

**Done when**: Both demos stream responses with tool visibility

---

## [x] TASK-4: Refinement
**Goal**: Ensure reliable demo execution
**Time**: ~30 minutes
**Context**: See requirements REQ-013 to REQ-017

Add basic error handling and UI feedback. Keep it simple but ensure the demo won't crash during presentation.

**Done when**: Demo handles errors gracefully

---

## [X] TASK-5: Validation
**Goal**: Verify and document
**Time**: ~25 minutes
**Context**: See requirements REQ-020, REQ-021

Test both scenarios thoroughly and create minimal documentation for setup and execution.

**Done when**: Both demos work reliably, README exists

---

### Guiding Principles

- **Simplicity over features**: Better to have 50 working lines than 200 broken ones
- **Hard-code for reliability**: This is a demo, not production
- **Test frequently**: Run the app after each task
- **Creative freedom**: Implementation details are up to you

### Time Budget
**Total: ~2 hours**
- If ahead of schedule: Add polish
- If behind: Skip task 4, focus on core functionality

### Success Criteria
□ Finance demo runs and shows tools
□ Market demo runs and shows tools
□ Setup takes < 5 minutes
□ Code is debuggable on-the-fly

---
*Remember: The goal is a successful live demo, not perfect code.*