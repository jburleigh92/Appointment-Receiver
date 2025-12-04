# Debugging Guide

This guide helps you troubleshoot common issues with the Healthcare Appointment Webhook Receiver.

-----

## Quick Diagnostics

### Is the service running?

```bash
curl http://localhost:8000/
```

**Expected:**

```json
{
  "service": "Healthcare Appointment Webhook",
  "status": "running",
  ...
}
```

**If connection refused:**

- Check if Python process is running: `ps aux | grep python`
- Verify port 8000 is not in use: `lsof -i :8000` (macOS/Linux)
- Check service logs in `webhook.log`

-----

## Common Issues

### 1. “Connection refused” or “Cannot connect”

**Problem:** The service isn’t running or is on a different port.

**Solutions:**

```bash
# Check if service is running
ps aux | grep webhook.py

# Start the service if not running
python webhook.py

# Check which port is being used
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

**If port 8000 is already in use:**

Edit `webhook.py` and change the port:

```python
# At the bottom of webhook.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Change to 8001
```

-----

### 2. “Invalid JSON” (400)

**Problem:** Request body is not valid JSON.

**Common Causes:**

❌ **Missing quotes around keys:**

```json
{
  event_type: "appointment.scheduled"  // WRONG
}
```

✅ **Correct:**

```json
{
  "event_type": "appointment.scheduled"  // RIGHT
}
```

❌ **Trailing commas:**

```json
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A001",  // WRONG - trailing comma
}
```

✅ **Correct:**

```json
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A001"  // RIGHT - no trailing comma
}
```

❌ **Single quotes instead of double:**

```json
{
  'event_type': 'appointment.scheduled'  // WRONG
}
```

**Debug Command:**

```bash
# Validate your JSON first
echo '{"your": "json"}' | python -m json.tool
```

-----

### 3. “Missing required fields” (400)

**Problem:** One or more required fields are missing.

**Required Fields:**

- `event_type`
- `appointment_id`
- `patient_id`
- `timestamp`

**Check Your Payload:**

```bash
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A001",
    "patient_id": "P001",
    "timestamp": "2025-01-10T12:30:00Z"
  }'
```

**Error Message Shows Missing Fields:**

```json
{
  "error": "Validation failed",
  "message": "Missing required fields: patient_id, timestamp"
}
```

Fix by adding the missing fields.

-----

### 4. “Invalid event_type” (400)

**Problem:** The `event_type` value is not one of the allowed values.

**Valid Values:**

- `appointment.scheduled`
- `appointment.cancelled`
- `appointment.updated`

**Common Mistakes:**

❌ Wrong:

```json
"event_type": "scheduled"           // Missing prefix
"event_type": "appointment_scheduled"  // Underscore instead of dot
"event_type": "appointment.deleted"    // Not a valid type
```

✅ Correct:

```json
"event_type": "appointment.scheduled"
```

-----

### 5. “Invalid timestamp format” (400)

**Problem:** Timestamp is not in ISO 8601 format.

**Valid Formats:**

✅ Correct:

```json
"timestamp": "2025-01-10T12:30:00Z"           // UTC
"timestamp": "2025-01-10T12:30:00.123Z"       // With milliseconds
"timestamp": "2025-01-10T07:30:00-05:00"      // With timezone offset
```

❌ Wrong:

```json
"timestamp": "2025-01-10"                      // Missing time
"timestamp": "2025-01-10 12:30:00"            // Missing T separator
"timestamp": "01/10/2025 12:30 PM"            // Wrong format
"timestamp": "2025-01-10T12:30:00"            // Missing timezone
```

**Generate Valid Timestamp:**

```bash
# In terminal
date -u +%Y-%m-%dT%H:%M:%SZ

# In Python
from datetime import datetime
datetime.utcnow().isoformat() + "Z"

# In JavaScript
new Date().toISOString()
```

-----

### 6. “Field must be a string” (400)

**Problem:** Field type doesn’t match expected type.

**All fields must be strings:**

❌ Wrong:

```json
{
  "appointment_id": 12345,  // Number instead of string
  "patient_id": true        // Boolean instead of string
}
```

✅ Correct:

```json
{
  "appointment_id": "12345",  // String
  "patient_id": "P001"        // String
}
```

-----

### 7. “Duplicate event” (409)

**Problem:** Event with same `appointment_id` and `timestamp` already exists.

**This is by design** to prevent duplicate processing.

**Understanding:**

```json
// First request - SUCCESS (200)
{"appointment_id": "A001", "timestamp": "2025-01-10T10:00:00Z"}

// Same request again - DUPLICATE (409)
{"appointment_id": "A001", "timestamp": "2025-01-10T10:00:00Z"}

// Different timestamp - SUCCESS (200)
{"appointment_id": "A001", "timestamp": "2025-01-10T11:00:00Z"}
```

**Solutions:**

1. **If this is a retry:** Consider it successful (event already processed)
1. **If this is an update:** Use `event_type: "appointment.updated"` with new timestamp
1. **If you need to resend:** Change the timestamp to current time

**Check Existing Events:**

```bash
curl http://localhost:8000/events | python -m json.tool
```

-----

### 8. “Cannot be empty or whitespace” (400)

**Problem:** `appointment_id` or `patient_id` is empty string or only whitespace.

❌ Wrong:

```json
{
  "appointment_id": "",        // Empty
  "patient_id": "   "          // Only whitespace
}
```

✅ Correct:

```json
{
  "appointment_id": "A001",
  "patient_id": "P001"
}
```

-----

### 9. Database Locked Error (500)

**Problem:** SQLite database is locked.

**Common Causes:**

- Database file open in SQLite browser/tool
- Multiple processes accessing database
- File permission issues

**Solutions:**

```bash
# Close any SQLite GUI tools
# Check who's using the database
lsof appointments.db

# Restart the service
pkill -f webhook.py
python webhook.py

# If persist, delete and recreate
rm appointments.db
python webhook.py  # Will auto-create new database
```

-----

### 10. Module Not Found Error

**Problem:** Missing Python dependencies.

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**

```bash
# Activate virtual environment if using one
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install fastapi uvicorn python-multipart

# Verify installation
pip list | grep fastapi
```

-----

## Debugging Techniques

### 1. Enable Detailed Logging

The service logs to `webhook.log` and console by default.

**View Logs:**

```bash
# Watch logs in real-time
tail -f webhook.log

# Search for specific request
grep "A12345" webhook.log

# View recent errors
grep "ERROR" webhook.log | tail -20
```

**Log Entries Include:**

- Request ID (for tracking)
- Full payload received
- Validation results
- Database operations
- Error stack traces

### 2. Inspect the Database

```bash
# Open database
sqlite3 appointments.db

# View all events
SELECT * FROM appointment_events;

# Count events by type
SELECT event_type, COUNT(*) 
FROM appointment_events 
GROUP BY event_type;

# Find specific appointment
SELECT * FROM appointment_events 
WHERE appointment_id = 'A12345';

# View recent events
SELECT * FROM appointment_events 
ORDER BY received_at DESC 
LIMIT 10;

# Exit
.quit
```

### 3. Test with Minimal Payload

Start with the simplest possible valid payload:

```bash
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "TEST",
    "patient_id": "TEST",
    "timestamp": "2025-01-10T12:00:00Z"
  }'
```

Then gradually add fields to isolate the problem.

### 4. Use Request ID for Tracking

Every response includes a `request_id`. Use it to find the request in logs:

```bash
# Response includes:
# "request_id": "2025-01-10T14:23:15.123456"

# Search logs
grep "2025-01-10T14:23:15.123456" webhook.log
```

### 5. Validate JSON Before Sending

```bash
# Create a file with your JSON
cat > test.json << 'EOF'
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A001",
  "patient_id": "P001",
  "timestamp": "2025-01-10T12:30:00Z"
}
EOF

# Validate it
cat test.json | python -m json.tool

# Send it
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d @test.json
```

### 6. Check Service Status

```bash
# Is Python running?
ps aux | grep webhook.py

# What port is it on?
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Any errors on startup?
cat webhook.log | grep ERROR
```

-----

## Advanced Debugging

### Enable Python Debugger

Add breakpoints in `webhook.py`:

```python
import pdb; pdb.set_trace()  # Add this line where you want to break
```

### Test with Python Requests

```python
import requests
import json

url = "http://localhost:8000/webhook/appointments"
payload = {
    "event_type": "appointment.scheduled",
    "appointment_id": "DEBUG001",
    "patient_id": "P001",
    "timestamp": "2025-01-10T12:30:00Z"
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

### Check Server Performance

```bash
# CPU usage
top | grep python

# Memory usage
ps aux | grep python | awk '{print $4, $11}'

# Database size
ls -lh appointments.db
```

-----

## Error Reference Table

|HTTP Code|Error Type        |Common Cause                |Quick Fix                              |
|---------|------------------|----------------------------|---------------------------------------|
|400      |Invalid JSON      |Malformed JSON              |Validate JSON syntax                   |
|400      |Missing fields    |Required field absent       |Add missing fields                     |
|400      |Invalid type      |Wrong field type            |Check all fields are strings           |
|400      |Invalid event_type|Wrong event type            |Use valid event type                   |
|400      |Invalid timestamp |Wrong timestamp format      |Use ISO 8601 format                    |
|400      |Empty ID          |Empty appointment/patient ID|Provide non-empty IDs                  |
|409      |Duplicate         |Same ID + timestamp         |Change timestamp or consider it success|
|500      |Server error      |Internal error              |Check logs, contact support            |

-----

## Getting Help

### Self-Service

1. ✅ Check this debugging guide
1. ✅ Review `webhook.log` for errors
1. ✅ Inspect database: `sqlite3 appointments.db`
1. ✅ Test with minimal payload
1. ✅ Validate JSON syntax

### Contact Support

If you still need help, provide:

1. **Request ID** from error response
1. **Full error message** from response
1. **Relevant log entries** from `webhook.log`
1. **Sample payload** that’s failing (sanitized if needed)
1. **Steps to reproduce** the issue

**Format:**

```
Subject: Webhook Error - Request ID: 2025-01-10T14:23:15.123456

Description:
Getting 400 error when sending appointment event.

Request ID: 2025-01-10T14:23:15.123456

Payload (sanitized):
{
  "event_type": "appointment.scheduled",
  "appointment_id": "XXX",
  "patient_id": "YYY",
  "timestamp": "2025-01-10T12:30:00Z"
}

Error Message:
"Missing required fields: patient_id"

Log Entry:
[2025-01-10 14:23:15,123] ERROR - Validation failed...
```

-----

## Prevention Checklist

Before sending events, verify:

- [ ] Service is running (`curl http://localhost:8000/`)
- [ ] JSON is valid (`python -m json.tool`)
- [ ] All required fields present
- [ ] All fields are strings
- [ ] `event_type` is one of the three valid values
- [ ] `timestamp` is ISO 8601 with timezone
- [ ] IDs are non-empty strings
- [ ] Error handling implemented in your code
- [ ] Request ID saved for debugging

-----

## Maintenance

### Clear Old Events

```bash
# Open database
sqlite3 appointments.db

# Delete events older than 30 days
DELETE FROM appointment_events 
WHERE received_at < datetime('now', '-30 days');

# Vacuum to reclaim space
VACUUM;
```

### Rotate Logs

```bash
# Backup current log
cp webhook.log webhook.log.backup

# Clear log (service will create new one)
> webhook.log
```

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

response=$(curl -s http://localhost:8000/)
status=$(echo $response | grep -o '"status":"running"')

if [ -n "$status" ]; then
    echo "✓ Service is healthy"
    exit 0
else
    echo "✗ Service is down"
    exit 1
fi
```
