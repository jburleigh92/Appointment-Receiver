# Healthcare Appointment Webhook API

## Customer Integration Guide

This document provides everything you need to integrate with our Healthcare Appointment Webhook API.

-----

## Base URL

```
http://localhost:8000
```

For production, your dedicated endpoint URL will be provided separately.

-----

## Authentication

**Current:** No authentication required (development environment)

**Production:** API key authentication via `X-API-Key` header (details provided upon deployment)

-----

## Webhook Endpoint

### Send Appointment Event

**Endpoint:** `POST /webhook/appointments`

**Description:** Submit appointment events (scheduled, cancelled, or updated) to our system for processing.

#### Request Headers

```http
Content-Type: application/json
```

#### Request Body

|Field           |Type  |Required|Description                                     |Example                  |
|----------------|------|--------|------------------------------------------------|-------------------------|
|`event_type`    |string|✅ Yes   |Type of appointment event                       |`"appointment.scheduled"`|
|`appointment_id`|string|✅ Yes   |Your unique appointment identifier              |`"A12345"`               |
|`patient_id`    |string|✅ Yes   |Your unique patient identifier                  |`"P8765"`                |
|`timestamp`     |string|✅ Yes   |When the event occurred (ISO 8601 with timezone)|`"2025-01-10T12:30:00Z"` |
|`notes`         |string|❌ No    |Additional information about the appointment    |`"Annual physical"`      |

#### Valid Event Types

|Event Type             |When to Use                          |
|-----------------------|-------------------------------------|
|`appointment.scheduled`|When a new appointment is created    |
|`appointment.cancelled`|When an appointment is cancelled     |
|`appointment.updated`  |When appointment details are modified|

#### Request Example

```bash
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z",
    "notes": "Annual physical examination"
  }'
```

#### Success Response

**Status Code:** `200 OK`

```json
{
  "status": "accepted",
  "message": "Appointment event received and stored",
  "event_id": 1,
  "appointment_id": "A12345",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

**Response Fields:**

- `status` - Always “accepted” for successful requests
- `message` - Human-readable confirmation message
- `event_id` - Our internal ID for this event (for support queries)
- `appointment_id` - Echo of your appointment ID
- `request_id` - Unique request identifier (save this for debugging)

-----

## Error Responses

All error responses follow this format:

```json
{
  "error": "Error Category",
  "message": "Detailed description of what went wrong",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

### 400 Bad Request

**When:** Invalid JSON or validation failure

#### Example 1: Missing Required Field

```bash
# Request missing patient_id
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Response:**

```json
{
  "error": "Validation failed",
  "message": "Missing required fields: patient_id",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

#### Example 2: Invalid Event Type

```bash
# Using non-existent event type
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.deleted",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Response:**

```json
{
  "error": "Validation failed",
  "message": "Invalid event_type 'appointment.deleted'. Must be one of: appointment.cancelled, appointment.scheduled, appointment.updated",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

#### Example 3: Invalid Timestamp

```bash
# Missing time portion
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10"
  }'
```

**Response:**

```json
{
  "error": "Validation failed",
  "message": "Invalid timestamp format. Must be ISO 8601 format (e.g., '2025-01-10T12:30:00Z'). Error: Invalid isoformat string: '2025-01-10'",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

#### Example 4: Wrong Data Type

```bash
# appointment_id is a number instead of string
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": 12345,
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Response:**

```json
{
  "error": "Validation failed",
  "message": "Field 'appointment_id' must be a string, got int",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

### 409 Conflict

**When:** Duplicate event detected (same appointment_id + timestamp)

```bash
# Send the same event twice
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z"
  }'

# Second request returns 409
```

**Response:**

```json
{
  "error": "Duplicate event",
  "message": "Event for appointment A12345 at 2025-01-10T12:30:00Z already exists",
  "request_id": "2025-01-10T14:23:15.234567"
}
```

**Note:** This is by design to ensure idempotency. If you need to update an appointment, use `event_type: "appointment.updated"` with a new timestamp.

### 500 Internal Server Error

**When:** Unexpected system error on our side

```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred while processing the event",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

**Action:** Contact support with the `request_id` for investigation.

-----

## Integration Best Practices

### 1. Timestamp Format

✅ **Always use ISO 8601 with timezone:**

```json
"timestamp": "2025-01-10T12:30:00Z"        // ✓ Correct (UTC)
"timestamp": "2025-01-10T12:30:00-05:00"   // ✓ Correct (EST)
```

❌ **Avoid these formats:**

```json
"timestamp": "2025-01-10"                  // ✗ Missing time
"timestamp": "01/10/2025 12:30 PM"        // ✗ Wrong format
"timestamp": "2025-01-10 12:30:00"        // ✗ Missing timezone
```

### 2. Error Handling

Always check the HTTP status code:

```python
# Python example
response = requests.post(url, json=payload)

if response.status_code == 200:
    # Success - event accepted
    event_id = response.json()["event_id"]
    
elif response.status_code == 400:
    # Validation error - fix the payload
    error = response.json()["message"]
    log.error(f"Invalid payload: {error}")
    
elif response.status_code == 409:
    # Duplicate - this event was already sent
    log.info("Event already processed, skipping")
    
elif response.status_code == 500:
    # Server error - retry with exponential backoff
    request_id = response.json()["request_id"]
    log.error(f"Server error, request_id: {request_id}")
    # Implement retry logic
```

### 3. Retry Logic

**For 500 errors:**

- Retry with exponential backoff
- Maximum 3 retry attempts
- Save `request_id` for support queries

**For 400 errors:**

- Do NOT retry (invalid data)
- Log the error
- Fix the payload

**For 409 errors:**

- Do NOT retry (already processed)
- Consider it a success

### 4. Idempotency

The API guarantees idempotency based on `appointment_id` + `timestamp`:

✅ **Safe to send:**

```json
// First event
{"appointment_id": "A001", "timestamp": "2025-01-10T10:00:00Z", ...}

// Different timestamp - new event
{"appointment_id": "A001", "timestamp": "2025-01-10T11:00:00Z", ...}
```

❌ **Will return 409:**

```json
// Same appointment_id AND timestamp
{"appointment_id": "A001", "timestamp": "2025-01-10T10:00:00Z", ...}
{"appointment_id": "A001", "timestamp": "2025-01-10T10:00:00Z", ...}
```

### 5. Rate Limiting

**Current:** No rate limits (development)

**Production:**

- 1000 requests per minute per API key
- Burst allowance of 100 requests
- 429 status code when exceeded

-----

## Code Examples

### Python

```python
import requests
from datetime import datetime

def send_appointment_event(event_type, appointment_id, patient_id, notes=None):
    url = "http://localhost:8000/webhook/appointments"
    
    payload = {
        "event_type": event_type,
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "notes": notes
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Event sent successfully: {result['event_id']}")
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            error = e.response.json()
            print(f"✗ Validation error: {error['message']}")
        elif e.response.status_code == 409:
            print(f"✓ Event already processed (duplicate)")
        elif e.response.status_code == 500:
            error = e.response.json()
            print(f"✗ Server error: {error['request_id']}")
        raise
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error: {str(e)}")
        raise

# Usage
send_appointment_event(
    event_type="appointment.scheduled",
    appointment_id="A12345",
    patient_id="P8765",
    notes="Annual physical"
)
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

async function sendAppointmentEvent(eventType, appointmentId, patientId, notes = null) {
  const url = 'http://localhost:8000/webhook/appointments';
  
  const payload = {
    event_type: eventType,
    appointment_id: appointmentId,
    patient_id: patientId,
    timestamp: new Date().toISOString(),
    notes: notes
  };
  
  try {
    const response = await axios.post(url, payload);
    console.log(`✓ Event sent successfully: ${response.data.event_id}`);
    return response.data;
    
  } catch (error) {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;
      
      if (status === 400) {
        console.error(`✗ Validation error: ${data.message}`);
      } else if (status === 409) {
        console.log('✓ Event already processed (duplicate)');
      } else if (status === 500) {
        console.error(`✗ Server error: ${data.request_id}`);
      }
    } else {
      console.error(`✗ Network error: ${error.message}`);
    }
    throw error;
  }
}

// Usage
sendAppointmentEvent(
  'appointment.scheduled',
  'A12345',
  'P8765',
  'Annual physical'
);
```

### cURL

```bash
#!/bin/bash

# Send appointment event
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"appointment.scheduled\",
    \"appointment_id\": \"A12345\",
    \"patient_id\": \"P8765\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"notes\": \"Annual physical\"
  }"
```

-----

## Testing Your Integration

### 1. Health Check

Verify the service is running:

```bash
curl http://localhost:8000/
```

Expected response:

```json
{
  "service": "Healthcare Appointment Webhook",
  "status": "running",
  "timestamp": "2025-01-10T14:23:15.123456",
  "version": "1.0.0"
}
```

### 2. Test Valid Event

```bash
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "TEST-001",
    "patient_id": "TEST-P001",
    "timestamp": "2025-01-10T12:30:00Z",
    "notes": "Test appointment"
  }'
```

### 3. Test Error Handling

```bash
# Test missing field
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "TEST-002"
  }'
```

-----

## Support

### Debugging

If you encounter issues:

1. **Save the `request_id`** from error responses
1. **Check the error message** for specific details
1. **Verify your payload** matches the schema
1. **Test with cURL** to isolate client issues

### Contact

**Email:** support@example.com  
**Documentation:** See `debugging.md` for common issues  
**Schema Reference:** See `schema.json` for full validation rules

### SLA

**Development:** Best effort support  
**Production:**

- Response time: < 4 hours
- Resolution time: < 24 hours
- Uptime: 99.9%

-----

## Changelog

### v1.0.0 (Current)

- Initial release
- Support for scheduled, cancelled, and updated events
- Duplicate detection
- Request ID tracking

-----

## Appendix

### Complete Validation Rules

1. ✓ Request body must be valid JSON
1. ✓ All required fields must be present
1. ✓ Fields must have correct types (all strings)
1. ✓ Required fields cannot be null
1. ✓ `event_type` must be one of: `appointment.scheduled`, `appointment.cancelled`, `appointment.updated`
1. ✓ `timestamp` must be valid ISO 8601 with timezone
1. ✓ `appointment_id` cannot be empty or whitespace
1. ✓ `patient_id` cannot be empty or whitespace
1. ✓ Combination of `appointment_id` + `timestamp` must be unique
1. ✓ `notes` is optional, but if provided must be a string

### Timezone Recommendations

Always send timestamps in UTC (with `Z` suffix) to avoid timezone conversion issues:

```json
"timestamp": "2025-01-10T12:30:00Z"
```

If you must use local timezone, include offset:

```json
"timestamp": "2025-01-10T07:30:00-05:00"  // EST
```
