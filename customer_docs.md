# Customer Integration Guide

## Overview

This webhook endpoint receives appointment events from your healthcare system. When an appointment event occurs (scheduled, cancelled, rescheduled, etc.), send a POST request to our webhook URL.

## Webhook URL

```
POST https://your-domain.com/webhook/appointment
```

## Authentication

*[Add your authentication method here - API keys, OAuth, etc.]*

## Request Format

### Headers

```
Content-Type: application/json
```

### Payload Structure

```json
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z",
  "notes": "Annual physical"
}
```

## Required Fields

|Field           |Type  |Required|Description                           |Constraints                                     |
|----------------|------|--------|--------------------------------------|------------------------------------------------|
|`event_type`    |string|Yes     |Type of appointment event             |Must be one of the valid event types (see below)|
|`appointment_id`|string|Yes     |Unique identifier for the appointment |1-50 characters                                 |
|`patient_id`    |string|Yes     |Unique identifier for the patient     |1-50 characters                                 |
|`timestamp`     |string|Yes     |When the event occurred               |ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)          |
|`notes`         |string|No      |Additional information about the event|Max 1000 characters                             |

## Valid Event Types

Your system should send one of these event types:

|Event Type               |Description              |When to Send                              |
|-------------------------|-------------------------|------------------------------------------|
|`appointment.scheduled`  |New appointment created  |When a patient books an appointment       |
|`appointment.cancelled`  |Appointment was cancelled|When a patient or provider cancels        |
|`appointment.rescheduled`|Appointment time changed |When an appointment is moved to a new time|
|`appointment.completed`  |Appointment finished     |After the appointment concludes           |
|`appointment.no_show`    |Patient didn’t attend    |When a patient misses their appointment   |

## Timestamp Format

Use ISO 8601 format with timezone:

**Valid Examples:**

- `2025-01-10T12:30:00Z` (UTC)
- `2025-01-10T12:30:00+00:00` (UTC with offset)
- `2025-01-10T08:30:00-04:00` (Eastern Time)

**Invalid Examples:**

- `01/10/2025 12:30 PM` ❌
- `2025-01-10 12:30:00` ❌
- `1704888600` ❌ (Unix timestamp)

## Response Format

### Success Response (201 Created)

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

### Error Response (422 Unprocessable Entity)

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

## Integration Examples

### Python

```python
import requests
import json
from datetime import datetime

def send_appointment_event(event_type, appointment_id, patient_id, notes=None):
    url = "https://your-domain.com/webhook/appointment"
    
    payload = {
        "event_type": event_type,
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "notes": notes
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 201:
        print("Event sent successfully!")
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None

# Example usage
send_appointment_event(
    event_type="appointment.scheduled",
    appointment_id="A12345",
    patient_id="P8765",
    notes="Annual physical"
)
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function sendAppointmentEvent(eventType, appointmentId, patientId, notes = null) {
  const url = 'https://your-domain.com/webhook/appointment';
  
  const payload = {
    event_type: eventType,
    appointment_id: appointmentId,
    patient_id: patientId,
    timestamp: new Date().toISOString(),
    notes: notes
  };
  
  try {
    const response = await axios.post(url, payload, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Event sent successfully!');
    return response.data;
  } catch (error) {
    console.error('Error:', error.response.status);
    console.error(error.response.data);
    return null;
  }
}

// Example usage
sendAppointmentEvent(
  'appointment.scheduled',
  'A12345',
  'P8765',
  'Annual physical'
);
```

### cURL

```bash
curl -X POST https://your-domain.com/webhook/appointment \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z",
    "notes": "Annual physical"
  }'
```

## Common Integration Scenarios

### Scenario 1: Patient Books Appointment

```json
{
  "event_type": "appointment.scheduled",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z",
  "notes": "Initial consultation - new patient"
}
```

### Scenario 2: Patient Cancels

```json
{
  "event_type": "appointment.cancelled",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-09T08:15:00Z",
  "notes": "Patient called to cancel due to conflict"
}
```

### Scenario 3: Appointment Rescheduled

```json
{
  "event_type": "appointment.rescheduled",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-15T14:00:00Z",
  "notes": "Moved from Jan 10 to Jan 15 per patient request"
}
```

### Scenario 4: Appointment Completed

```json
{
  "event_type": "appointment.completed",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T13:00:00Z",
  "notes": "Routine checkup completed successfully"
}
```

### Scenario 5: Patient No-Show

```json
{
  "event_type": "appointment.no_show",
  "appointment_id": "A12345",
  "patient_id": "P8765",
  "timestamp": "2025-01-10T12:30:00Z",
  "notes": "Patient did not arrive for scheduled appointment"
}
```

## Error Handling Best Practices

1. **Retry Logic**: Implement exponential backoff for failed requests
1. **Validate Before Sending**: Check required fields before making the request
1. **Log Errors**: Keep records of failed webhook deliveries
1. **Monitor Success Rate**: Track delivery success rates over time

## Rate Limits

*[Add your rate limiting information here]*

## Support

If you encounter issues integrating with our webhook:

1. Verify your payload matches the required format
1. Check that all required fields are present
1. Ensure timestamp is in ISO 8601 format
1. Confirm event_type is one of the valid values

For additional support, contact: *[your support contact]*

## Changelog

*[Document any changes to the webhook API]*
