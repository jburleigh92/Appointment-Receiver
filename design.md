# Technical Design Document

## Overview

This document outlines the technical design decisions and architecture for the Appointment Webhook API.

## Technology Stack

### FastAPI vs Flask

**Decision: FastAPI**

**Rationale:**

1. **Automatic Data Validation**: Pydantic integration provides built-in request/response validation
1. **Auto-Generated Documentation**: Swagger UI and ReDoc come out of the box
1. **Type Safety**: Python type hints enable better IDE support and catch errors early
1. **Performance**: Built on Starlette and uses async/await for better performance
1. **Modern Standards**: Follows OpenAPI 3.0 specification automatically
1. **Developer Experience**: Less boilerplate code compared to Flask + marshmallow

**Trade-offs:**

- Slightly steeper learning curve for developers unfamiliar with async Python
- Smaller ecosystem compared to Flask (though growing rapidly)

### Database: SQLite

**Decision: SQLite for initial implementation**

**Rationale:**

1. **Zero Configuration**: No separate database server required
1. **File-based**: Easy backup and portability
1. **Sufficient for MVP**: Handles moderate webhook volumes
1. **Development Friendly**: Easy to inspect and reset during testing

**Migration Path:**
For production at scale, consider:

- **PostgreSQL**: Better concurrency, JSONB support, full-text search
- **MySQL**: Wide adoption, good performance
- **MongoDB**: If document structure becomes more complex

## Architecture Components

### 1. Request Validation Layer

**Implementation: Pydantic Models**

```python
class AppointmentEvent(BaseModel):
    event_type: str
    appointment_id: str
    patient_id: str
    timestamp: str
    notes: Optional[str]
```

**Benefits:**

- Declarative validation rules
- Automatic type coercion where possible
- Clear error messages for invalid data
- Reusable across the application

**Validation Strategy:**

- **Field-level**: Type checking, length constraints
- **Custom validators**: Event type enum, ISO 8601 timestamp format
- **Schema-level**: Required vs optional fields

### 2. Storage Layer

**Database Schema:**

```sql
CREATE TABLE appointment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    appointment_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    notes TEXT,
    received_at TEXT NOT NULL,
    raw_payload TEXT NOT NULL
)
```

**Design Decisions:**

- **Store Raw Payload**: Preserves original data for debugging and auditing
- **Normalized Fields**: Extracted fields for efficient querying
- **Received Timestamp**: Tracks when webhook was received (vs event timestamp)
- **Auto-incrementing ID**: Simple primary key for internal reference

**Future Enhancements:**

- Add indexes on `appointment_id`, `patient_id`, `event_type` for faster queries
- Add `created_by` field if multi-tenant
- Add `processed` flag for async processing workflows

### 3. Logging Strategy

**Implementation: Python logging module**

**Log Levels:**

- **INFO**: Successful event receipt
- **WARNING**: Validation errors, recoverable issues
- **ERROR**: System errors, database failures

**Log Outputs:**

1. **Console**: Real-time monitoring during development
1. **File**: Persistent logs for debugging and audit trails

**Log Format:**

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Future Enhancements:**

- Structured logging (JSON format) for log aggregation tools
- Integration with centralized logging (e.g., ELK stack, Datadog)
- Correlation IDs for request tracing

### 4. Error Handling

**HTTP Status Code Strategy:**

|Code|Use Case                  |Response Format                   |
|----|--------------------------|----------------------------------|
|200 |Successful GET requests   |JSON data                         |
|201 |Successful webhook receipt|Success message + event_id        |
|422 |Validation failure        |Error details with field locations|
|500 |Server errors             |Generic error message             |

**Error Response Structure:**

```json
{
  "status": "error",
  "message": "Human-readable summary",
  "errors": [/* detailed validation errors */]
}
```

**Design Principles:**

- **Clear Messages**: Help integrators understand what went wrong
- **Field-level Details**: Specify which fields failed validation
- **No Sensitive Data**: Never expose internal system details in errors

## API Design

### Endpoint Structure

```
POST /webhook/appointment     # Receive events
GET  /webhook/events          # Admin: list events
GET  /                        # Health check
```

**RESTful Principles:**

- Nouns for resources (`/appointment` not `/createAppointment`)
- HTTP methods convey intent (POST for creation)
- Plural nouns for collections (`/events`)

### Request/Response Flow

```
Client Request
    ↓
FastAPI Router
    ↓
Pydantic Validation
    ↓
Business Logic (if needed)
    ↓
Database Storage
    ↓
Logging
    ↓
Response (201 or 422)
```

## Validation Rules

### Event Type Validation

**Allowed Values:**

- `appointment.scheduled`
- `appointment.cancelled`
- `appointment.rescheduled`
- `appointment.completed`
- `appointment.no_show`

**Rationale:**

- Explicit enum prevents typos
- Follows common webhook naming patterns (resource.action)
- Easy to extend with new event types

### Timestamp Validation

**Format: ISO 8601**

**Valid Examples:**

- `2025-01-10T12:30:00Z` (UTC)
- `2025-01-10T12:30:00+00:00` (UTC with offset)
- `2025-01-10T08:30:00-04:00` (with timezone)

**Rationale:**

- International standard
- Unambiguous timezone handling
- Supported by all modern languages
- Sortable in string format

### ID Validation

**Constraints:**

- 1-50 characters
- Alphanumeric, hyphens, underscores only

**Rationale:**

- Prevents SQL injection attempts
- Maintains compatibility with various ID formats
- Long enough for UUIDs, short enough to prevent abuse

## Security Considerations

### Current Implementation

1. **Input Validation**: Strict schema prevents malformed data
1. **SQL Safety**: Parameterized queries prevent SQL injection
1. **Length Limits**: Prevents memory exhaustion attacks

### Production Enhancements

1. **Authentication**:
- API Key validation
- HMAC signature verification
- OAuth 2.0 for enterprise customers
1. **Rate Limiting**:
- Per-client request limits
- Backoff strategies for misbehaving clients
1. **HTTPS**:
- TLS 1.2+ only
- Valid SSL certificates
1. **Request Signing**:
- Verify webhook authenticity
- Prevent replay attacks with nonce/timestamp
1. **IP Whitelisting**:
- Restrict to known customer IPs
- Useful for internal integrations

## Performance Considerations

### Current Performance

- **Synchronous Processing**: Events processed immediately
- **SQLite**: Suitable for ~100 requests/second
- **No Caching**: Every request hits the database

### Scaling Strategy

**Phase 1: Vertical Scaling**

- Upgrade server resources
- Optimize database queries
- Add indexes

**Phase 2: Async Processing**

```python
@app.post("/webhook/appointment")
async def receive_event(event: AppointmentEvent):
    await queue.enqueue(process_event, event)
    return {"status": "accepted"}
```

**Phase 3: Horizontal Scaling**

- Load balancer
- Multiple API servers
- Centralized database (PostgreSQL/MySQL)
- Redis for caching

**Phase 4: Event Queue**

- RabbitMQ or Kafka
- Separate worker processes
- Retry logic for failed processing

## Monitoring and Observability

### Current Capabilities

1. **Logs**: File-based logging
1. **Admin Endpoint**: Query stored events
1. **API Docs**: Interactive testing interface

### Production Enhancements

1. **Metrics**:
- Request rate
- Error rate
- Response time (p50, p95, p99)
- Database query performance
1. **Alerting**:
- High error rate
- Database connection failures
- Disk space warnings
1. **Tracing**:
- Distributed tracing (OpenTelemetry)
- Request correlation IDs
- End-to-end visibility

## Testing Strategy

### Unit Tests

- Pydantic model validation
- Database operations
- Error handling

### Integration Tests

- Full endpoint testing
- Database persistence
- Error response formats

### Load Tests

- Apache Bench or Locust
- Simulate realistic webhook volumes
- Identify performance bottlenecks

## Deployment Considerations

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "webhook:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
WEBHOOK_DB_PATH=/data/appointments.db
WEBHOOK_LOG_LEVEL=INFO
WEBHOOK_PORT=8000
WEBHOOK_HOST=0.0.0.0
```

### Health Checks

- Endpoint: `GET /`
- Returns 200 if service is healthy
- Can be extended to check database connectivity

## Future Enhancements

### Idempotency

**Problem**: Network issues may cause duplicate webhook deliveries

**Solution**:

- Add `idempotency_key` field to request
- Check for existing events before inserting
- Return original response for duplicates

### Webhook Acknowledgment

**Pattern**: Synchronous response + async processing

```python
1. Validate request (synchronous)
2. Store in queue (synchronous)
3. Return 202 Accepted (synchronous)
4. Process event (asynchronous)
```

### Event Replay

**Use Case**: Customer needs to resend events

**Implementation**:

- Admin endpoint: `POST /webhook/replay/{event_id}`
- Re-processes stored raw payload
- Useful for bug fixes or system recovery

### Webhook Subscriptions

**Enhancement**: Allow customers to specify which events they want

```json
{
  "subscriptions": [
    "appointment.scheduled",
    "appointment.cancelled"
  ]
}
```

## Conclusion

This design prioritizes:

1. **Developer Experience**: Easy to understand and integrate
1. **Reliability**: Comprehensive validation and error handling
1. **Maintainability**: Clear separation of concerns
1. **Scalability**: Clear migration path to production-grade infrastructure

The architecture supports both immediate deployment and future growth with minimal refactoring.
