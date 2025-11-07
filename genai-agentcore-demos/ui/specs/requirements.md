# Requirements Document
## AWS AgentCore FinTech Demo - Functional Requirements

### 1. Application Startup

**REQ-001**: Application Launch
- WHEN the user executes `streamlit run app.py`
- THEN the application SHALL display within 3 seconds
- AND SHALL show title "AWS AgentCore FinTech Demo"

**REQ-002**: Initial State
- WHEN the application loads
- THEN the Finance tab SHALL be selected by default
- AND the "Run Demo Scenario" button SHALL be enabled

### 2. Persona Display

**REQ-003**: Persona Information
- WHEN the application is running
- THEN the system SHALL display "Sarah Chen | $180K income | Tech Professional | SF"
- AND this SHALL remain visible at all times

### 3. Navigation

**REQ-004**: Tab Selection
- WHEN the user selects a different tab
- THEN the system SHALL immediately switch context
- AND SHALL maintain the same persona

**REQ-005**: State Management
- WHEN switching between tabs
- THEN the system SHALL NOT lose state
- AND SHALL NOT trigger API calls

### 4. Demo Execution

**REQ-006**: Finance Demo
- WHEN the user clicks "Run Demo Scenario" on Finance tab
- THEN the system SHALL invoke the Finance Assistant
- AND SHALL display loading feedback

### 5. Streaming Response

**REQ-008**: Tool Messages
- WHEN the agent sends "thinking" events
- THEN the system SHALL display tool messages with 🔧 emoji
- AND SHALL update in real-time

**REQ-009**: Response Streaming
- WHEN the agent sends "stream_token" events
- THEN the system SHALL display tokens progressively
- AND SHALL maintain formatting

**REQ-010**: Completion
- WHEN streaming completes
- THEN the system SHALL re-enable the button
- AND SHALL clear tool messages

### 6. Tool Visibility

**REQ-011**: Finance Tools
- WHEN Finance Assistant processes
- THEN the system SHALL show:
  - "🔧 Calculating budget breakdown..."
  - "🔧 Analyzing spending patterns..."

### 7. Error Handling

**REQ-013**: Connection Error
- WHEN API call fails
- THEN the system SHALL display simple error message
- AND SHALL re-enable button

**REQ-014**: Timeout
- WHEN response exceeds 30 seconds
- THEN the system SHALL show timeout message

**REQ-015**: Stream Errors
- WHEN SSE parsing fails
- THEN the system SHALL continue processing
- AND SHALL NOT crash

### 8. UI Feedback

**REQ-016**: Loading State
- WHEN demo executes
- THEN the system SHALL show "Agent thinking..."
- AND SHALL disable button

**REQ-017**: Button States
- WHEN idle, button SHALL be enabled
- WHEN processing, button SHALL be disabled

### 9. Display

**REQ-018**: Message Container
- WHEN showing responses
- THEN use st.chat_message("assistant")

**REQ-019**: Markdown
- WHEN response contains markdown
- THEN render formatting correctly

### 10. Performance

**REQ-020**: Response Time
- WHEN demo starts
- THEN first tool message SHALL appear < 5 seconds

**REQ-021**: Streaming
- WHEN tokens stream
- THEN display SHALL be smooth

### 11. Configuration

**REQ-023**: AWS Setup
- WHEN connecting to AWS
- THEN use region us-west-2
- AND use environment credentials

**REQ-024**: Agent ARNs
- WHEN calling agents
- THEN use hardcoded ARNs

### 12. Queries

**REQ-025**: Finance Query
- SHALL send: "I make $180K with $4K monthly expenses. Create my 50/30/20 budget and analyze if I'm overspending on dining at $1200/month"

**REQ-026**: Market Query
- SHALL send: "Compare NVDA, MSFT, and GOOGL over 6 months and create a $50K growth portfolio for a tech professional"

### 13. Layout

**REQ-027**: Structure
- Layout SHALL be: Title → Tabs → Persona → Button → Response

---
**Total Requirements**: 27
**All requirements are P0 (Critical) for MVP**