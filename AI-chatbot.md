# Phase 1 Implementation Guide: Gemini Tool Integration for Fazri Analyzer Chatbot

## Executive Summary

This guide provides a comprehensive roadmap for implementing Phase 1 of the conversational AI chatbot feature for the Fazri Analyzer system. Phase 1 focuses on function calling integration, where **Google Gemini** serves as the reasoning engine and calls your existing FastAPI services as tools to answer natural language queries.

**Goal**: Enable administrators to ask operational questions in plain English and receive accurate, real-time answers derived from the campus monitoring system.

**Status**: ✅ **IMPLEMENTED** - Backend API ready for integration

---

## 1. Architecture Overview

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ADMIN DASHBOARD                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Chat Interface                              │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │ User: "Show me anomalies in the library today"            │  │   │
│  │  │ Assistant: "I found 3 anomalies in Library zones today:   │  │   │
│  │  │   1. Unusual after-hours access at 23:15...               │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                                  │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  Chat Endpoint   │───▶│  Tool Orchestrator│───▶│  Gemini API      │  │
│  │  /api/v1/chat    │    │  (Tool Execution) │◀───│  (Reasoning)     │  │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│                                   │                                      │
│                    ┌──────────────┼──────────────┐                      │
│                    ▼              ▼              ▼                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ Anomaly Service  │  │ Entity Service   │  │ Occupancy Service│      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌────────────┐  ┌────────────┐  ┌────────────┐
            │ PostgreSQL │  │   Neo4j    │  │   Redis    │
            └────────────┘  └────────────┘  └────────────┘
```

### 1.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Chat Interface** | Capture user input, display responses, manage conversation UI |
| **Chat Endpoint** | Receive messages, manage conversation state, return responses |
| **Tool Orchestrator** | Define tools, execute tool calls, format results for Gemini |
| **Gemini API** | Understand intent, decide which tools to call, synthesize responses |
| **Existing Services** | Provide actual data via existing business logic |

### 1.3 Request-Response Lifecycle

1. User types natural language question in chat UI
2. Frontend sends message to `/api/v1/chat/message` endpoint
3. Backend constructs Gemini API request with tool definitions and conversation history
4. Gemini analyzes the question and decides which tool(s) to call
5. Backend executes the requested tool (calls internal service/existing endpoint)
6. Tool results are sent back to Gemini
7. Gemini synthesizes a natural language response
8. Response is returned to frontend and displayed to user

---

## 2. Tool Selection and Design

### 2.1 Recommended Tools for Phase 1

Based on your existing system capabilities and typical admin queries, prioritize these 6 tools:

| Tool Name | Purpose | Underlying Service/Endpoint | Priority |
|-----------|---------|----------------------------|----------|
| `get_anomalies` | Retrieve anomaly alerts with filters | Anomaly detection service | High |
| `get_zone_occupancy` | Current occupancy counts by zone | Zone occupancy service | High |
| `search_entity` | Find entity by name, ID, or attributes | Entity resolution service | High |
| `get_entity_location` | Current/recent location of an entity | Card swipe + WiFi services | High |
| `get_zone_activity` | Activity summary for a specific zone | Aggregated from multiple sources | Medium |
| `get_entity_timeline` | Timeline of entity movements/activities | Card swipes, library, lab bookings | Medium |

### 2.2 Tool Schema Design Principles

Each tool needs a well-defined schema that Claude can understand. Key principles:

**Be Specific with Parameters**
- Use enums for constrained values (zone names, severity levels)
- Include clear descriptions for each parameter
- Mark required vs optional parameters explicitly

**Return Structured Data**
- Consistent response format across tools
- Include metadata (count, time range, filters applied)
- Limit result sets to prevent token overflow

**Handle Edge Cases**
- Define behavior for empty results
- Include error states in tool responses
- Set sensible defaults for optional parameters

### 2.3 Detailed Tool Specifications

#### Tool 1: get_anomalies

**Purpose**: Retrieve anomaly alerts based on various filters

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | No | Filter by specific zone (e.g., "LIBRARY_MAIN", "LAB_A") |
| `severity` | enum | No | Filter by severity: "low", "medium", "high", "critical" |
| `anomaly_type` | enum | No | Type: "after_hours", "unusual_pattern", "access_violation", "occupancy_spike" |
| `time_range` | enum | No | "last_hour", "today", "last_24h", "last_week" (default: "today") |
| `entity_id` | string | No | Filter anomalies related to specific entity |
| `limit` | integer | No | Maximum results to return (default: 10, max: 50) |

**Returns**:
- List of anomalies with: id, type, severity, zone, timestamp, description, related_entities
- Total count matching filters
- Time range covered

**Example Queries This Handles**:
- "Show me today's anomalies"
- "Are there any critical alerts in the library?"
- "What anomalies are associated with entity E-1234?"

---

#### Tool 2: get_zone_occupancy

**Purpose**: Get current or historical occupancy data for zones

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | No | Specific zone (if omitted, returns all zones) |
| `include_prediction` | boolean | No | Include ML-based occupancy prediction (default: false) |
| `time_point` | enum | No | "current", "1h_ago", "peak_today" (default: "current") |

**Returns**:
- Zone occupancy data: zone_id, zone_name, current_count, capacity, utilization_percentage
- Optional: predicted_count, prediction_confidence
- Timestamp of data

**Example Queries This Handles**:
- "How many people are in the library right now?"
- "Which zones are at capacity?"
- "What's the predicted occupancy for Lab A?"

---

#### Tool 3: search_entity

**Purpose**: Find entities matching search criteria

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search term (name, ID, email, card_id) |
| `role` | enum | No | Filter by role: "student", "staff", "faculty", "visitor" |
| `department` | string | No | Filter by department |
| `limit` | integer | No | Maximum results (default: 10) |

**Returns**:
- List of matching entities: entity_id, name, role, department, email
- Match confidence score
- Total matches found

**Example Queries This Handles**:
- "Find John Smith"
- "Who is entity E-4521?"
- "Show me all staff in Computer Science department"

---

#### Tool 4: get_entity_location

**Purpose**: Get current or recent location of a specific entity

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | Yes | The entity identifier |
| `include_history` | boolean | No | Include location history (default: false) |
| `history_hours` | integer | No | Hours of history to include (default: 4, max: 24) |

**Returns**:
- Current location: zone_id, zone_name, last_seen_timestamp, confidence
- Data sources: which systems detected (card_swipe, wifi, cctv)
- Optional: location_history array with timestamps

**Example Queries This Handles**:
- "Where is John Smith right now?"
- "Where has entity E-1234 been today?"
- "When was the last time this person was seen?"

---

#### Tool 5: get_zone_activity

**Purpose**: Get activity summary for a specific zone

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | Yes | The zone identifier |
| `time_range` | enum | No | "last_hour", "today", "last_24h" (default: "today") |
| `include_entries_exits` | boolean | No | Include entry/exit counts (default: true) |

**Returns**:
- Activity summary: total_entries, total_exits, unique_visitors, peak_occupancy, peak_time
- Current status: current_occupancy, is_open, operating_hours
- Notable events: any anomalies or unusual patterns

**Example Queries This Handles**:
- "What's the activity in Lab B today?"
- "How many people visited the library this morning?"
- "What was the peak occupancy in Zone A?"

---

#### Tool 6: get_entity_timeline

**Purpose**: Get chronological activity timeline for an entity

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | Yes | The entity identifier |
| `date` | string | No | Specific date (YYYY-MM-DD), default: today |
| `event_types` | array | No | Filter: ["card_swipe", "library", "lab_booking", "wifi"] |

**Returns**:
- Timeline array: timestamp, event_type, location, details
- Summary: first_seen, last_seen, zones_visited, total_events
- Patterns: typical_schedule_match (boolean)

**Example Queries This Handles**:
- "Show me John's activity timeline for today"
- "What did entity E-1234 do yesterday?"
- "When did this person check out library books?"

---

## 3. Backend Implementation Plan

### 3.1 New Components to Create

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── chat.py              # New: Chat endpoint
│   ├── services/
│   │   └── chatbot/
│   │       ├── __init__.py
│   │       ├── orchestrator.py      # New: Tool orchestration logic
│   │       ├── tools.py             # New: Tool definitions
│   │       ├── tool_executor.py     # New: Tool execution logic
│   │       └── prompts.py           # New: System prompts
│   ├── schemas/
│   │   └── chat.py                  # New: Request/response models
│   └── core/
│       └── config.py                # Update: Add Gemini API config
```

### 3.2 Configuration Requirements

**Environment Variables to Add**:
```
GOOGLE_API_KEY=your-gemini-api-key
CHATBOT_MODEL=gemini-2.0-flash
CHATBOT_MAX_TOKENS=4096
CHATBOT_TEMPERATURE=0.3
CHATBOT_MAX_TOOL_CALLS=5
CHATBOT_CONVERSATION_TTL=3600
CHATBOT_ENABLED=true
```

**Configuration Considerations**:
- **Model Selection**: Use Gemini 2.0 Flash for fast, cost-effective responses with function calling
- **Temperature**: Keep low (0.2-0.4) for factual, consistent responses
- **Max Tool Calls**: Limit to prevent runaway loops (5 is reasonable)
- **Conversation TTL**: How long to keep conversation history in Redis

### 3.3 Chat Endpoint Design

**Endpoint**: `POST /api/v1/chat/message`

**Request Structure**:
```
{
  "message": "Show me anomalies in the library today",
  "conversation_id": "conv-uuid-optional",
  "context": {
    "current_zone": "ADMIN_OFFICE",  // Optional context hints
    "user_role": "admin"
  }
}
```

**Response Structure**:
```
{
  "response": "I found 3 anomalies in Library zones today...",
  "conversation_id": "conv-uuid",
  "tools_used": ["get_anomalies"],
  "data": {
    "anomalies": [...],  // Raw data if frontend wants to render it
    "count": 3
  },
  "metadata": {
    "model": "claude-sonnet-4-20250514",
    "tokens_used": 1250,
    "processing_time_ms": 1340
  }
}
```

### 3.4 Tool Orchestrator Design

The orchestrator manages the conversation loop with Claude:

**Core Loop**:
1. Receive user message and conversation history
2. Build Claude API request with tools and system prompt
3. Send to Claude API
4. If Claude requests tool calls:
   - Execute each tool call
   - Collect results
   - Send results back to Claude
   - Repeat until Claude provides final response
5. Return final response to user

**Key Design Decisions**:

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Tool call limit | Max 5 per turn | Prevent infinite loops, control costs |
| Parallel execution | Yes, when independent | Faster response times |
| Error handling | Return error as tool result | Let Claude explain the issue naturally |
| Result truncation | Truncate at ~2000 chars per tool | Prevent token overflow |

### 3.5 System Prompt Design

The system prompt is critical for reliable behavior. It should include:

**Identity and Role**:
- Define the assistant as a campus security monitoring expert
- Clarify it can only answer questions about campus data
- Set professional, helpful tone

**Tool Usage Guidelines**:
- When to use each tool
- How to interpret tool results
- How to handle empty results
- How to combine multiple tool calls

**Response Formatting**:
- Keep responses concise but complete
- Use bullet points for lists
- Include relevant timestamps
- Mention data sources when relevant

**Boundaries and Limitations**:
- Cannot access external systems
- Cannot make predictions beyond ML model outputs
- Cannot modify any data
- Should escalate security concerns to human admins

**Example System Prompt Structure**:
```
You are an AI assistant for the Fazri Analyzer campus security monitoring system.
You help administrators query real-time campus data including entity locations,
zone occupancy, anomaly alerts, and activity patterns.

## Your Capabilities
- Search for people (students, staff, faculty) by name or ID
- Check current and historical locations of individuals
- View zone occupancy and activity
- Retrieve and filter anomaly alerts
- Show activity timelines for entities

## Guidelines
- Always use the appropriate tool to get current data; never make up information
- When results are empty, clearly state that no matching data was found
- For location queries, mention the data source (card swipe, WiFi, etc.)
- Keep responses concise and actionable
- If a query is ambiguous, ask for clarification

## Limitations
- You can only read data, not modify it
- You cannot access systems outside this campus monitoring platform
- For urgent security concerns, advise the admin to take direct action

## Response Format
- Lead with the key finding or answer
- Use bullet points for multiple items
- Include relevant timestamps
- Mention when data might be incomplete
```

### 3.6 Conversation State Management

**Storage**: Redis with conversation ID as key

**State Structure**:
```
{
  "conversation_id": "conv-uuid",
  "user_id": "admin-123",
  "created_at": "2025-01-15T10:30:00Z",
  "last_activity": "2025-01-15T10:35:00Z",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "tool_calls_count": 3,
  "context": {}
}
```

**Conversation Limits**:
- Maximum messages per conversation: 20 (then summarize or reset)
- TTL: 1 hour of inactivity
- Maximum concurrent conversations per user: 3

---

## 4. Frontend Implementation Plan

### 4.1 Component Structure

```
frontend/
├── components/
│   └── chat/
│       ├── ChatWidget.tsx           # Main container
│       ├── ChatHeader.tsx           # Title, minimize/close
│       ├── MessageList.tsx          # Scrollable message area
│       ├── MessageBubble.tsx        # Individual message
│       ├── ChatInput.tsx            # Text input + send
│       ├── ToolResultCard.tsx       # Display structured data
│       └── TypingIndicator.tsx      # Loading state
├── hooks/
│   └── useChat.ts                   # Chat state management
├── services/
│   └── chatService.ts               # API integration
└── types/
    └── chat.ts                      # TypeScript interfaces
```

### 4.2 UI/UX Design Specifications

**Widget Placement**: Fixed position, bottom-right corner of admin dashboard

**States**:
| State | Appearance |
|-------|------------|
| Collapsed | Floating action button with chat icon |
| Expanded | Chat window (400w x 600h pixels) |
| Loading | Typing indicator with pulsing dots |
| Error | Error message with retry option |

**Message Types**:
- **User messages**: Right-aligned, primary color background
- **Assistant messages**: Left-aligned, neutral background
- **Tool results**: Expandable cards showing structured data
- **System messages**: Centered, muted text (e.g., "Conversation cleared")

**Interaction Patterns**:
- Enter key sends message (Shift+Enter for newline)
- Auto-scroll to newest message
- Click to expand/collapse tool result details
- Conversation history persists during session

### 4.3 State Management

**Local State (React useState/useReducer)**:
- Current message input
- Messages array
- Loading state
- Widget expanded/collapsed

**Persisted State (localStorage or sessionStorage)**:
- Conversation ID (to resume conversations)
- Widget position preference
- Sound notification preference

### 4.4 API Integration

**Service Layer Functions**:
```typescript
// Pseudo-interface for chat service
interface ChatService {
  sendMessage(message: string, conversationId?: string): Promise<ChatResponse>;
  getConversationHistory(conversationId: string): Promise<Message[]>;
  clearConversation(conversationId: string): Promise<void>;
}
```

**Error Handling**:
- Network errors: Show retry button, preserve message
- Rate limit: Show cooldown timer
- Server errors: Show generic error, log details

### 4.5 Accessibility Requirements

- Keyboard navigation (Tab through messages, Enter to send)
- Screen reader announcements for new messages
- High contrast support
- Minimum touch target sizes (44x44px)
- Focus management when widget opens/closes

---

## 5. Integration with Existing Services

### 5.1 Service Mapping

Map each tool to existing service methods:

| Tool | Existing Service | Method/Endpoint |
|------|-----------------|-----------------|
| `get_anomalies` | `AnomalyService` | `get_anomalies(filters)` |
| `get_zone_occupancy` | `OccupancyService` | `get_current_occupancy()` |
| `search_entity` | `EntityService` | `search_entities(query)` |
| `get_entity_location` | `LocationService` | `get_entity_location(entity_id)` |
| `get_zone_activity` | `ActivityService` | `get_zone_summary(zone_id)` |
| `get_entity_timeline` | `TimelineService` | `get_entity_timeline(entity_id)` |

### 5.2 Data Transformation Layer

Each tool executor needs to:
1. Map tool parameters to service method parameters
2. Call the existing service
3. Transform the response to a Claude-friendly format
4. Handle service errors gracefully

**Transformation Considerations**:
- Truncate large result sets
- Format timestamps consistently (ISO 8601)
- Redact sensitive fields if needed
- Add human-readable labels to enum values

### 5.3 New Service Methods Needed

Some tools may require new aggregation methods:

| Tool | New Method Needed | Description |
|------|------------------|-------------|
| `get_zone_activity` | `ActivityService.get_zone_summary()` | Aggregate entries/exits/unique visitors |
| `get_entity_timeline` | `TimelineService.get_unified_timeline()` | Merge events from multiple sources |

### 5.4 Database Queries to Optimize

The chatbot will increase query frequency. Pre-optimize:

**High Priority**:
- Anomaly queries with zone + time filters
- Entity search with partial name matching
- Recent card swipes by entity

**Indexes to Verify**:
```sql
-- Anomalies
CREATE INDEX idx_anomalies_zone_timestamp ON anomalies(zone_id, detected_at);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);

-- Card swipes
CREATE INDEX idx_swipes_entity_time ON card_swipes(entity_id, timestamp DESC);
CREATE INDEX idx_swipes_zone_time ON card_swipes(zone_id, timestamp DESC);

-- Entity search
CREATE INDEX idx_entities_name_trgm ON entities USING gin(name gin_trgm_ops);
```

---

## 6. Security Implementation

### 6.1 Authentication and Authorization

**Requirements**:
- Chat endpoint requires valid admin session
- Reuse existing JWT authentication middleware
- Add role check: only users with "admin" or "security" role

**Implementation**:
```python
# Pseudo-code for endpoint protection
@router.post("/chat")
@require_auth(roles=["admin", "security"])
async def chat_endpoint(request: ChatRequest, current_user: User):
    # User is authenticated and authorized
    pass
```

### 6.2 Rate Limiting

**Limits**:
| Limit Type | Value | Scope |
|------------|-------|-------|
| Messages per minute | 10 | Per user |
| Messages per hour | 100 | Per user |
| Concurrent requests | 2 | Per user |
| Max message length | 500 chars | Per message |

**Implementation**: Use Redis-based rate limiter (you may already have one)

### 6.3 Audit Logging

**Log Every**:
- Chat message sent (user_id, message, timestamp)
- Tool executed (tool_name, parameters, user_id)
- Data accessed (entities viewed, zones queried)

**Log Structure**:
```json
{
  "event_type": "chatbot_query",
  "timestamp": "2025-01-15T10:30:00Z",
  "user_id": "admin-123",
  "conversation_id": "conv-uuid",
  "message": "Where is John Smith?",
  "tools_called": ["search_entity", "get_entity_location"],
  "entities_accessed": ["E-4521"],
  "response_tokens": 250
}
```

### 6.4 Input Validation

**Sanitization**:
- Strip HTML/script tags from user input
- Limit message length
- Validate conversation_id format (UUID)

**Tool Parameter Validation**:
- Validate entity_id format before queries
- Sanitize search queries (prevent injection)
- Validate enum values against allowed lists

### 6.5 Data Access Controls

**Entity-Level Permissions** (if applicable):
- Some entities might have restricted access
- Tool executor should check permissions before returning data

**Response Filtering**:
- Redact sensitive fields (SSN, personal phone if stored)
- Limit exposure of security-critical data in responses

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Tool Executors**:
- Test each tool executor with mock service responses
- Test parameter validation
- Test error handling
- Test response transformation

**Orchestrator**:
- Test tool selection logic
- Test multi-tool conversation flows
- Test conversation state management
- Test rate limit enforcement

### 7.2 Integration Tests

**Claude API Integration**:
- Test real API calls with test prompts
- Verify tool call parsing
- Test response handling

**Service Integration**:
- Test tools calling real services (with test data)
- Verify data transformation accuracy
- Test timeout handling

### 7.3 End-to-End Tests

**Conversation Flows**:
| Test Case | Input | Expected Tools | Expected Output |
|-----------|-------|----------------|-----------------|
| Simple anomaly query | "Show anomalies today" | get_anomalies | List of anomalies |
| Entity search + location | "Where is John Smith?" | search_entity, get_entity_location | Location with timestamp |
| Zone occupancy | "How full is the library?" | get_zone_occupancy | Occupancy count + percentage |
| Complex multi-step | "Who was in Lab A when the anomaly occurred?" | get_anomalies, get_zone_activity | Combined answer |

### 7.4 Performance Tests

**Targets**:
| Metric | Target | Maximum |
|--------|--------|---------|
| Response time (simple query) | < 2s | 5s |
| Response time (multi-tool) | < 4s | 10s |
| Concurrent users | 10 | 20 |
| Messages per second | 5 | 10 |

### 7.5 Security Tests

- Input injection attempts
- Rate limit bypass attempts
- Unauthorized access attempts
- Conversation hijacking attempts

---

## 8. Deployment Plan

### 8.1 Environment Setup

**Development**:
- Use Claude API with test key
- Connect to development database
- Enable verbose logging
- Disable rate limiting for testing

**Staging**:
- Full integration with staging services
- Enable rate limiting
- Test with realistic data volumes
- Performance testing

**Production**:
- Production Claude API key
- Full security controls enabled
- Monitoring and alerting active
- Gradual rollout

### 8.2 Feature Flag Strategy

**Flags to Implement**:
```
CHATBOT_ENABLED=true
CHATBOT_ALLOWED_USERS=["admin-1", "admin-2"]  # For gradual rollout
CHATBOT_DEBUG_MODE=false
CHATBOT_TOOLS_ENABLED=["get_anomalies", "get_zone_occupancy", ...]
```

**Rollout Phases**:
1. Internal testing (dev team only)
2. Limited beta (2-3 trusted admins)
3. Expanded beta (all security team)
4. General availability (all admins)

### 8.3 Monitoring Setup

**Metrics to Track**:
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `chatbot_requests_total` | Total chat requests | N/A |
| `chatbot_response_time_seconds` | Response latency | > 5s |
| `chatbot_errors_total` | Error count by type | > 5/min |
| `chatbot_tool_calls_total` | Tool usage by type | N/A |
| `claude_api_tokens_used` | Token consumption | > 1M/day |
| `claude_api_errors_total` | API errors | > 1% error rate |

**Dashboards to Create**:
- Chatbot usage overview
- Response time distribution
- Tool usage breakdown
- Error rate tracking
- Cost tracking (API tokens)

### 8.4 Rollback Plan

**Triggers for Rollback**:
- Claude API error rate > 10%
- Average response time > 10s
- Security incident detected
- Cost exceeds budget threshold

**Rollback Steps**:
1. Set `CHATBOT_ENABLED=false`
2. Return "Service temporarily unavailable" message
3. Investigate and fix issues
4. Re-enable with monitoring

---

## 9. Cost Estimation

### 9.1 Claude API Costs

**Assumptions**:
- Model: Claude Sonnet
- Average input tokens per request: 1,500 (includes history + tools)
- Average output tokens per request: 400
- Daily active admin users: 10
- Average queries per user per day: 20

**Monthly Estimate**:
```
Daily requests: 10 users × 20 queries = 200 requests
Monthly requests: 200 × 22 work days = 4,400 requests

Input tokens: 4,400 × 1,500 = 6.6M tokens
Output tokens: 4,400 × 400 = 1.76M tokens

Cost (Claude Sonnet pricing):
- Input: 6.6M × $3/1M = $19.80
- Output: 1.76M × $15/1M = $26.40
- Total: ~$46/month
```

### 9.2 Infrastructure Costs

**Additional Redis Usage**: Minimal (conversation state is small)

**Additional Database Load**: Monitor, but likely minimal impact

**Total Estimated Monthly Cost**: $50-100 (mainly Claude API)

---

## 10. Success Metrics

### 10.1 Usage Metrics

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Daily active users | 5 | 10 |
| Queries per user/day | 10 | 20 |
| Conversation completion rate | 80% | 90% |

### 10.2 Quality Metrics

| Metric | Target |
|--------|--------|
| Successful tool execution rate | > 95% |
| User satisfaction (if surveyed) | > 4/5 |
| Escalation to manual lookup rate | < 20% |

### 10.3 Performance Metrics

| Metric | Target |
|--------|--------|
| P50 response time | < 2s |
| P95 response time | < 5s |
| Error rate | < 1% |

---

## 11. Post-Launch Iteration Plan

### 11.1 Week 1-2: Observation

- Monitor all metrics closely
- Collect user feedback
- Identify common query patterns not well served
- Fix any bugs or issues

### 11.2 Week 3-4: Refinement

- Tune system prompt based on observed issues
- Adjust tool parameters based on usage patterns
- Optimize slow queries
- Consider adding 1-2 more tools if clear gaps exist

### 11.3 Phase 2 Preparation

- Identify queries that would benefit from RAG
- Analyze free-text notes usage patterns
- Plan vector database setup
- Design embedding pipeline

---

## 12. Appendix

### A. Gemini API Integration Reference

**Library**: `google-generativeai` (Python SDK)

**Key Components**:

- `genai.configure(api_key=...)`: Configure API key
- `genai.GenerativeModel(...)`: Create model instance with tools
- `model.start_chat(history=...)`: Start conversation with history
- `chat.send_message(...)`: Send message and get response

**Tool Definition Format (Gemini)**:

```json
{
  "name": "tool_name",
  "description": "What this tool does",
  "parameters": {
    "type": "object",
    "properties": {
      "param1": {
        "type": "string",
        "description": "Parameter description"
      }
    },
    "required": ["param1"]
  }
}
```

### B. Conversation History Format

**Message Roles**:

- `user`: User messages
- `model`: Assistant responses
- `function_call`: Tool call by assistant (includes name, args)
- `function_response`: Result of tool execution

### C. Error Codes

| Code | Description | User Message |
|------|-------------|--------------|
| `RATE_LIMITED` | Too many requests | "Please wait a moment before sending another message." |
| `TOOL_ERROR` | Tool execution failed | "I encountered an issue accessing that data. Please try again." |
| `INVALID_INPUT` | Bad user input | "I couldn't understand that. Could you rephrase?" |
| `SERVICE_UNAVAILABLE` | Backend service down | "Some data is temporarily unavailable. Please try again later." |

---

## 13. Implementation Status (COMPLETED)

### Backend Files Created

```
backend/
├── config.py                        # Updated with Gemini config
├── main.py                          # Updated to include chat_routes
├── chat_routes.py                   # Chat API endpoints
├── models/
│   └── chat.py                      # Pydantic models for chat
├── services/
│   └── chatbot/
│       ├── __init__.py
│       ├── orchestrator.py          # Gemini conversation orchestration
│       ├── tools.py                 # Tool definitions for function calling
│       ├── tool_executor.py         # Execute tools via existing services
│       └── prompts.py               # System prompt
└── requirements.txt                 # Added google-generativeai
```

### API Endpoints Available

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/message` | Send a chat message |
| DELETE | `/api/v1/chat/conversation/{id}` | Clear conversation history |
| GET | `/api/v1/chat/health` | Check chatbot health status |
| GET | `/api/v1/chat/tools` | List available tools |

### Next Steps

1. **Set up Google API key** - Get from Google AI Studio
2. **Add to environment**: `GOOGLE_API_KEY=your-key-here`
3. **Test the API** using curl or Postman
4. **Build frontend chat widget** to integrate with the API


This guide provides the blueprint. Let me know when you want to proceed with code implementation or if you need clarification on any section.