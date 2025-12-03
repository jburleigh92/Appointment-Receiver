# Technical Design Document

## Overview

This document describes the technical architecture, design decisions, and implementation details of the Healthcare Appointment Webhook Receiver service.

-----

## Architecture

### High-Level Components

```
┌─────────────────┐
│  HTTP Client    │ (cURL, Postman, External Systems)
└────────┬────────┘
         │ POST /webhook/appointments
         ▼
┌─────────────────┐
│   FastAPI       │ (Web Framework)
│   Application   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌────────┐ ┌────────┐
│Request │ │Schema│ │Database│ │Logging │
│Handler │ │Valid.│ │Layer   │ │System  │
└────────┘ └──────┘ └────────┘ └────────┘
                │         │
                ▼         ▼
         ┌──────────┬──────────┐
         │schema.   │appoint-  │
         │json      │ments.db  │
         └──────────┴──────────┘
```

### Component Responsibilities

|Component              |Responsibility                                |Technology         |
|-----------------------|----------------------------------------------|-------------------|
|**FastAPI Application**|HTTP request/response handling, routing       |FastAPI            |
|**Request Handler**    |Parse JSON, orchestrate validation and storage|Python async       |
|**Schema Validator**   |Validate payload against rules in schema.json |Custom Python class|
|**Database Layer**     |Store and retrieve events, check duplicates   |SQLite3            |
|**Logging System**     |Log all operations, errors, and audit trail   |Python logging     |

-----

## Design Decisions

### 1. Single-File Architecture

**Decision:** Consolidate all code into `webhook.py`

**Rationale:**

- Easier to review and understand for take-home assessment
- Simplifies deployment (single file + schema)
- Reduces cognitive overhead
- Still maintains logical separation via classes

**Trade-offs:**

- ✅ Simple to deploy and review
- ✅ No import management complexity
- ❌ Not ideal for large-scale production (would split into modules)
- ❌ Testing requires importing entire module

### 2. FastAPI Framework

**Decision:** Use FastAPI over Flask or Django

**Rationale:**

- Modern async support for future scalability
- Built-in request validation and documentation
- Excellent performance
- Clean, Pythonic API design
- Automatic OpenAPI (Swagger) documentation

**Trade-offs:**

- ✅ Fast and modern
- ✅ Great developer experience
- ✅ Built-in async support
- ❌ Slightly more dependencies than Flask
- ❌ Less familiar to some developers

### 3. SQLite for Persistence

**Decision:** Use SQLite over in-memory storage or PostgreSQL

**Rationale:**

- Zero configuration required
- Data persists across restarts
- Easy to inspect with standard tools
- Perfect for development and assessment
- Simple migration path to PostgreSQL if needed

**Trade-offs:**

- ✅ No setup required
- ✅ File-based, easy to inspect
- ✅ ACID compliance
- ❌ Not suitable for high-concurrency production
- ❌ Single-file bottleneck

### 4. Schema-Based Validation

**Decision:** External `schema.json` file rather than hard-coded validation

**Rationale:**

- Declarative, easy to understand
- Can be updated without code changes
- Self-documenting
- Can be shared with API consumers
- Version-controlled separately if needed

**Trade-offs:**

- ✅ Easy to read and modify
- ✅ Self-documenting
- ✅ Shareable with consumers
- ❌ Requires file I/O
- ❌ Fallback needed if file missing

### 5. Duplicate Detection Strategy

**Decision:** Use UNIQUE constraint on (appointment_id, timestamp)

**Rationale:**

- Database-level enforcement (most reliable)
- Atomic operation (no race conditions)
- Explicit 409 Conflict response
- Prevents data duplication at source

**Implementation:**

```sql
UNIQUE(appointment_id, timestamp)
```

**Trade-offs:**

- ✅ Race-condition safe
- ✅ Enforced at DB level
- ✅ Explicit error handling
- ❌ Assumes timestamp granularity sufficient (is for ISO 8601)

### 6. Request ID Generation

**Decision:** Use ISO timestamp as request ID

**Rationale:**

- Simple, no dependencies
- Sortable and human-readable
- Sufficient uniqueness for our use case
- Includes temporal information

**Trade-offs:**

- ✅ Simple implementation
- ✅ Human-readable
- ✅ Sortable
- ❌ Not guaranteed unique (could use UUID if needed)
- ❌ Microsecond collisions possible under high load

-----

## Data Model

### AppointmentEvent

```python
@dataclass
class AppointmentEvent:
    event_type: str          # One of: scheduled, cancelled, updated
    appointment_id: str      # Unique appointment identifier
    patient_id: str          # Unique patient identifier
    timestamp: str           # ISO 8601 timestamp
    notes: Optional[str]     # Optional notes
```

### Database Schema

```sql
CREATE TABLE appointment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    appointment_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    notes TEXT,
    received_at TEXT NOT NULL,
    UNIQUE(appointment_id, timestamp)
);

CREATE INDEX idx_appointment_timestamp 
ON appointment_events(appointment_id, timestamp);
```

**Rationale for Fields:**

- `id` - Auto-incrementing primary key for internal reference
- `event_type`, `appointment_id`, `patient_id`, `timestamp`, `notes` - Direct mapping from event
- `received_at` - Audit trail of when we received the event
- `UNIQUE(appointment_id, timestamp)` - Prevent duplicates
- Index - Optimize duplicate detection queries

-----

## Validation Flow

```
┌──────────────┐
│ JSON Payload │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Parse JSON           │ ──[Invalid]──> 400 Bad Request
└──────┬───────────────┘
       │ [Valid JSON]
       ▼
┌──────────────────────┐
│ Check Required Fields│ ──[Missing]──> 400 Bad Request
└──────┬───────────────┘
       │ [All present]
       ▼
┌──────────────────────┐
│ Validate Types       │ ──[Type Error]─> 400 Bad Request
└──────┬───────────────┘
       │ [Types OK]
       ▼
┌──────────────────────┐
│ Validate event_type  │ ──[Invalid]──> 400 Bad Request
└──────┬───────────────┘
       │ [Valid]
       ▼
┌──────────────────────┐
│ Validate Timestamp   │ ──[Invalid]──> 400 Bad Request
└──────┬───────────────┘
       │ [Valid ISO 8601]
       ▼
┌──────────────────────┐
│ Check Non-Empty IDs  │ ──[Empty]───> 400 Bad Request
└──────┬───────────────┘
       │ [Valid]
       ▼
┌──────────────────────┐
│ Check Duplicate      │ ──[Exists]──> 409 Conflict
└──────┬───────────────┘
       │ [New Event]
       ▼
┌──────────────────────┐
│ Store in Database    │ ──[Error]───> 500 Server Error
└──────┬───────────────┘
       │ [Success]
       ▼
┌──────────────────────┐
│ Return 200 OK        │
└──────────────────────┘
```

-----

## Error Handling Strategy

### Principle: Fail Fast, Fail Clear

Every error provides:

1. **HTTP Status Code** - Standard semantic meaning
1. **Error Type** - High-level category
1. **Error Message** - Specific, actionable description
1. **Request ID** - For tracking and debugging

### Error Categories

|HTTP Code|Error Type  |Cause                    |Example                    |
|---------|------------|-------------------------|---------------------------|
|400      |Bad Request |Invalid input from client|Missing field, wrong type  |
|409      |Conflict    |Business rule violation  |Duplicate event            |
|500      |Server Error|Unexpected system error  |Database connection failure|

### Error Response Format

```json
{
  "error": "Error Type",
  "message": "Specific description of what went wrong",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

**Design Choice:** Consistent error format across all endpoints

- Easier for clients to parse
- Consistent developer experience
- Includes request_id for support queries

-----

## Logging Strategy

### Log Levels

|Level  |When to Use       |Example                                |
|-------|------------------|---------------------------------------|
|INFO   |Normal operations |Event received, stored, service started|
|WARNING|Recoverable issues|Validation failure, duplicate event    |
|ERROR  |Unexpected errors |Database error, unexpected exception   |

### What Gets Logged

1. **Service Lifecycle**
- Startup, shutdown
- Database initialization
1. **Every Request**
- Request ID
- Full payload (for audit)
- Validation result
- Storage result
1. **All Errors**
- Error type and message
- Stack trace (for 500 errors)
- Request context

### Log Format

```
2025-01-10 14:23:15,123 - webhook - INFO - [request_id] Message
```

**Design Choice:** Structured, parseable format

- Timestamp for temporal ordering
- Logger name for filtering
- Level for severity
- Request ID for correlation
- Message for details

-----

## Scalability Considerations

### Current Limitations

1. **Single-threaded SQLite**
- ❌ Limited concurrent writes
- ✅ Sufficient for assessment and low-volume production
1. **Synchronous Database Operations**
- ❌ Blocks async event loop
- ✅ Simple, correct implementation
1. **File-based Logging**
- ❌ Disk I/O bottleneck at scale
- ✅ Easy to debug locally

### Future Improvements

If scaling to production:

1. **Database**
- Replace SQLite with PostgreSQL
- Use async database driver (asyncpg)
- Add connection pooling
1. **Logging**
- Replace file logging with structured logging to stdout
- Aggregate with ELK stack or CloudWatch
- Add distributed tracing (OpenTelemetry)
1. **Architecture**
- Add message queue (RabbitMQ, Kafka) for reliability
- Separate API and worker processes
- Add Redis for caching duplicate checks
1. **Operations**
- Add health checks for database
- Add metrics (Prometheus)
- Add rate limiting
- Add authentication/authorization

-----

## Testing Strategy

### Manual Testing

Provided via cURL examples in documentation:

- Valid requests
- Missing fields
- Invalid types
- Invalid event_type
- Duplicate events

### Automated Testing (Future)

Would add:

```python
# tests/test_webhook.py
def test_valid_event():
    response = client.post("/webhook/appointments", json=valid_payload)
    assert response.status_code == 200

def test_missing_field():
    response = client.post("/webhook/appointments", json=invalid_payload)
    assert response.status_code == 400
    
def test_duplicate_event():
    client.post("/webhook/appointments", json=payload)
    response = client.post("/webhook/appointments", json=payload)
    assert response.status_code == 409
```

-----

## Security Considerations

### Current State (Assessment)

- No authentication (acceptable for local testing)
- No rate limiting
- Full payload logging (includes PII)

### Production Requirements

Would need to add:

1. **Authentication**
- API key validation
- HMAC signature verification
- OAuth 2.0 for external integrations
1. **Authorization**
- Role-based access control
- Tenant isolation
1. **Input Sanitization**
- SQL injection prevention (using parameterized queries ✓)
- NoSQL injection prevention
- XSS prevention
1. **Data Privacy**
- PII redaction in logs
- Encryption at rest
- Encryption in transit (HTTPS)
- HIPAA compliance considerations
1. **Rate Limiting**
- Per-client rate limits
- DDoS prevention
- Circuit breakers

-----

## Performance Characteristics

### Expected Performance

**Throughput:**

- ~1000-5000 requests/second (limited by SQLite writes)
- Async I/O allows handling many concurrent connections

**Latency:**

- P50: <10ms (validation + DB write)
- P95: <50ms
- P99: <100ms

**Bottlenecks:**

1. SQLite write lock (serializes writes)
1. Disk I/O for logging
1. JSON parsing

### Optimization Opportunities

1. **Batch Writes**
- Accept batch of events
- Single DB transaction
1. **Async Logging**
- Queue log messages
- Write in background
1. **Connection Pooling**
- Reuse DB connections (when using PostgreSQL)

-----

## Monitoring & Observability

### Key Metrics to Track (Production)

1. **Request Metrics**
- Request rate (requests/sec)
- Error rate (errors/sec)
- Response time (P50, P95, P99)
1. **Business Metrics**
- Events received by type
- Duplicate event rate
- Validation failure rate
1. **System Metrics**
- Database size
- Log file size
- Memory usage
- CPU usage
1. **Alerts**
- Error rate > 5%
- Response time P99 > 1s
- Duplicate rate > 10%
- Disk space < 10%

-----

## Conclusion

This design prioritizes:

1. ✅ **Simplicity** - Easy to understand and review
1. ✅ **Correctness** - Proper validation and error handling
1. ✅ **Reliability** - Duplicate detection, atomic operations
1. ✅ **Observability** - Comprehensive logging
1. ✅ **Maintainability** - Clear structure, good documentation

The implementation is production-ready for low-to-medium volume use cases and provides a clear migration path to scale further if needed.
