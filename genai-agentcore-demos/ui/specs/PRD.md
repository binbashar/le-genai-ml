# Product Requirements Document (PRD) - MVP
## AWS AgentCore FinTech Demo - Streamlit Interface

### 1. Executive Summary

**Product Name**: AgentCore FinTech Demo Interface
**Version**: 1.0 MVP
**Runtime**: Python 3.13+
**Package Manager**: uv with pyproject.toml
**Scope**: One persona, two scenarios

### 2. Product Vision

Create the simplest possible demonstration that effectively showcases AWS AgentCore's dual-agent capabilities with real-time tool orchestration visibility.

### 3. Core Scope

#### Single Persona: "Tech Professional - Sarah Chen"
- **Profile**: Software Engineer at SF startup
- **Income**: $180K salary, $4K monthly expenses
- **Goal**: Budget optimization and investment planning

#### Two Demo Scenarios

**Scenario 1 - Finance Assistant**
```
"I make $180K with $4K monthly expenses. Create my 50/30/20
budget and analyze if I'm overspending on dining at $1200/month"
```
**Tools displayed**: Budget breakdown, spending analysis

### 4. Key Features

#### 4.1 Single-Page Interface
- Finance Assistant interface
- Fixed persona display
- One-click demo execution
- Real-time response streaming

#### 4.2 Tool Orchestration Visibility
- Show "thinking" messages as tools execute
- Display tool names during processing
- Stream response tokens as they arrive
- Clear visual feedback of agent activity

#### 4.3 Minimal Interaction
- No user input required
- Pre-defined queries only
- Single button per demo
- No configuration needed

### 5. Technical Approach

- **Deployment**: Local Streamlit application
- **Architecture**: Single Python file (~100 lines)
- **Dependencies**: streamlit, boto3 only
- **Region**: us-west-2 (San Francisco proximity)
- **No offline mode**: Trust AgentCore connection

### 6. Out of Scope

- User authentication
- Custom queries
- Error recovery/retry logic
- Data persistence
- Multiple personas (for MVP)
- Offline/cached responses

### 7. Success Criteria

1. **Reliability**: Both demos execute without errors
2. **Visibility**: Tool execution clearly shown
3. **Performance**: Responses stream smoothly
4. **Simplicity**: Setup in < 5 minutes
5. **Impact**: Clear demonstration of AgentCore value

### 8. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Network failure | Test morning-of event |
| API timeout | Simple timeout message |
| Laptop issue | Backup laptop ready |

### 9. Future Expansion Path

Post-MVP additions (not for event):
- Additional personas
- Custom query input
- Visualization charts
- Cloud deployment

---
**Focus**: Deliver working demo that showcases streaming and tool orchestration
**Timeline**: 2-3 hours implementation
**Complexity**: Minimum viable