# Debugging and Testing Guide

## Testing the Webhook Locally

### Start the Server

```bash
python webhook.py
```

Server runs on `http://localhost:8000`

### Interactive API Documentation

Visit these URLs for automatic testing interfaces:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Test Cases

### ✅ Test Case 1: Valid Scheduled Appointment

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z",
    "notes": "Annual physical"
  }'
```

**Expected Response (201):**

```json
{
  "status": "success",
  "message": "Event received and stored successfully",
  "event_id": 1,
  "received_at": "2025-12-03T10:15:30.123456",
  "data": {
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765"
  }
}
```

### ✅ Test Case 2: Valid Cancelled Appointment

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.cancelled",
    "appointment_id": "A12346",
    "patient_id": "P8766",
    "timestamp": "2025-01-11T09:00:00Z",
    "notes": "Patient requested cancellation"
  }'
```

### ✅ Test Case 3: Valid Rescheduled Appointment

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.rescheduled",
    "appointment_id": "A12347",
    "patient_id": "P8767",
    "timestamp": "2025-01-12T15:00:00Z",
    "notes": "Moved from original time slot"
  }'
```

### ✅ Test Case 4: Valid Completed Appointment

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.completed",
    "appointment_id": "A12348",
    "patient_id": "P8768",
    "timestamp": "2025-01-09T14:30:00Z"
  }'
```

### ✅ Test Case 5: Valid No-Show Event

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.no_show",
    "appointment_id": "A12349",
    "patient_id": "P8769",
    "timestamp": "2025-01-08T10:00:00Z",
    "notes": "Patient did not arrive"
  }'
```

### ✅ Test Case 6: Valid Request Without Notes

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.completed",
    "appointment_id": "A12350",
    "patient_id": "P8770",
    "timestamp": "2025-01-09T16:00:00Z"
  }'
```

## Error Test Cases

### ❌ Error Test 1: Missing Required Field (appointment_id)

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Expected Response (422):**

```json
{
  "status": "error",
  "message": "Invalid payload structure",
  "errors": [
    {
      "loc": ["body", "appointment_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### ❌ Error Test 2: Invalid Event Type

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.deleted",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Expected Response (422):**

```json
{
  "status": "error",
  "message": "Invalid payload structure",
  "errors": [
    {
      "loc": ["body", "event_type"],
      "msg": "event_type must be one of: appointment.scheduled, appointment.cancelled, appointment.rescheduled, appointment.completed, appointment.no_show",
      "type": "value_error"
    }
  ]
}
```

### ❌ Error Test 3: Invalid Timestamp Format

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "01/10/2025 12:30 PM"
  }'
```

**Expected Response (422):**

```json
{
  "status": "error",
  "message": "Invalid payload structure",
  "errors": [
    {
      "loc": ["body", "timestamp"],
      "msg": "timestamp must be in ISO 8601 format (e.g., 2025-01-10T12:30:00Z)",
      "type": "value_error"
    }
  ]
}
```

### ❌ Error Test 4: Empty String for Required Field

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Expected Response (422):**

```json
{
  "status": "error",
  "message": "Invalid payload structure",
  "errors": [
    {
      "loc": ["body", "appointment_id"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### ❌ Error Test 5: Notes Too Long (>1000 characters)

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d "{
    \"event_type\": \"appointment.scheduled\",
    \"appointment_id\": \"A12345\",
    \"patient_id\": \"P8765\",
    \"timestamp\": \"2025-01-10T12:30:00Z\",
    \"notes\": \"$(python -c 'print("x" * 1001)')\"
  }"
```

**Expected Response (422):**

```json
{
  "status": "error",
  "message": "Invalid payload structure",
  "errors": [
    {
      "loc": ["body", "notes"],
      "msg": "ensure this value has at most 1000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

### ❌ Error Test 6: Invalid JSON

```bash
curl -X POST http://localhost:8000/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled"
    "appointment_id": "A12345"
  }'
```

**Expected Response (422):**

```json
{
  "detail": [
    {
      "loc": ["body"],
      "msg": "Expecting ',' delimiter",
      "type": "value_error.jsondecode"
    }
  ]
}
```

## Postman Testing

### Import Collection

Create a new Postman collection with these requests:

#### 1. Valid Scheduled Appointment

- **Method**: POST
- **URL**: `http://localhost:8000/webhook/appointment`
- **Headers**: `Content-Type: application/json`
- **Body**:

```json
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z",
  "notes": "Annual physical"
}
```

#### 2. Invalid - Missing Field

- **Body**:

```json
{
  "event_type": "appointment.scheduled",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z"
}
```

#### 3. Invalid - Wrong Event Type

- **Body**:

```json
{
  "event_type": "appointment.unknown",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z"
}
```

### Postman Test Scripts

Add to the **Tests** tab:

```javascript
// Test for successful response
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Response has success status", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.status).to.eql("success");
});

pm.test("Response contains event_id", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.event_id).to.be.a('number');
});

pm.test("Response contains received_at timestamp", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.received_at).to.be.a('string');
});

// Test for error responses
if (pm.response.code === 422) {
    pm.test("Error response has proper structure", function () {
        var jsonData = pm.response.json();
        pm.expect(jsonData.status).to.eql("error");
        pm.expect(jsonData.errors).to.be.an('array');
    });
}
```

## Admin Endpoints

### View All Stored Events

```bash
curl -X GET http://localhost:8000/webhook/events
```

**Response:**

```json
{
  "total": 5,
  "events": [
    {
      "id": 5,
      "event_type": "appointment.scheduled",
      "appointment_id": "A12345",
      "patient_id": "P8765",
      "timestamp": "2025-01-10T12:30:00Z",
      "notes": "Annual physical",
      "received_at": "2025-12-03T10:15:30.123456"
    }
  ]
}
```

### View Limited Events

```bash
curl -X GET "http://localhost:8000/webhook/events?limit=10"
```

### Health Check

```bash
curl -X GET http://localhost:8000/
```

**Response:**

```json
{
  "status": "healthy",
  "service": "Appointment Webhook API",
  "version": "1.0.0"
}
```

## Log Analysis

### Log Location

- **File**: `webhook_events.log`
- **Console**: Real-time output during server runtime

### Log Format

```
2025-12-03 10:15:30 - __main__ - INFO - Received appointment.scheduled event - Appointment: A12345, Patient: P8765
2025-12-03 10:16:45 - __main__ - WARNING - Validation error: <error details>
2025-12-03 10:17:12 - __main__ - ERROR - Error processing event: <error message>
```

### Common Log Messages

**Successful Event:**

```
INFO - Received appointment.scheduled event - Appointment: A12345, Patient: P8765
```

**Validation Error:**

```
WARNING - Validation error: 1 validation error for AppointmentEvent
appointment_id
  field required (type=value_error.missing)
```

**Server Error:**

```
ERROR - Error processing event: Database connection failed
```

## Common Issues and Solutions

### Issue 1: Connection Refused

**Error:**

```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Solution:**

- Ensure the server is running: `python webhook.py`
- Check that port 8000 is not in use by another application

### Issue 2: 422 Validation Error

**Error:**

```json
{
  "status": "error",
  "message": "Invalid payload structure"
}
```

**Solution:**

- Check that all required fields are present
- Verify field names match exactly (case-sensitive)
- Ensure timestamp is in ISO 8601 format
- Confirm event_type is one of the valid values

### Issue 3: Database Locked

**Error in logs:**

```
ERROR - Error processing event: database is locked
```

**Solution:**

- Close any SQLite browser tools accessing the database
- Check file permissions on `appointments.db`
- Restart the server

### Issue 4: Invalid JSON

**Error:**

```
Expecting ',' delimiter
```

**Solution:**

- Validate JSON syntax using a JSON validator
- Check for missing commas, brackets, or quotes
- Ensure proper escaping of special characters

## Database Inspection

### Using SQLite CLI

```bash
sqlite3 appointments.db

# View all events
SELECT * FROM appointment_events;

# View recent events
SELECT event_type, appointment_id, received_at 
FROM appointment_events 
ORDER BY received_at DESC 
LIMIT 10;

# Count events by type
SELECT event_type, COUNT(*) as count 
FROM appointment_events 
GROUP BY event_type;

# Exit
.quit
```

### Reset Database

```bash
# Stop the server first
rm appointments.db

# Restart the server - it will recreate the database
python webhook.py
```

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install Apache Bench (if needed)
# Ubuntu: sudo apt-get install apache2-utils
# Mac: brew install apache-bench

# Test 100 requests with 10 concurrent connections
ab -n 100 -c 10 -p payload.json -T application/json \
  http://localhost:8000/webhook/appointment
```

**payload.json:**

```json
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z",
  "notes": "Load test"
}
```

## Debugging Tips

1. **Enable Detailed Logging**: Set log level to DEBUG in webhook.py
1. **Use Interactive Docs**: Visit `/docs` for built-in testing interface
1. **Check Raw Logs**: Review `webhook_events.log` for detailed error messages
1. **Validate JSON**: Use online JSON validators before sending requests
1. **Test Incrementally**: Start with minimal payload, then add optional fields
1. **Monitor Database**: Query SQLite to confirm events are being stored

## Environment Variables (Future)

For production deployment, consider using environment variables:

```bash
export WEBHOOK_DB_PATH=/path/to/production.db
export WEBHOOK_LOG_LEVEL=INFO
export WEBHOOK_PORT=8000
```
