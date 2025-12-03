# Appointment Webhook API

A robust webhook endpoint built with FastAPI for receiving and processing appointment events from healthcare systems.

## Features

- ✅ Schema validation with Pydantic
- ✅ SQLite database storage
- ✅ Comprehensive logging
- ✅ Clear error messages
- ✅ Auto-generated API documentation
- ✅ RESTful design with proper HTTP status codes

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python webhook.py
```

The server will start at `http://localhost:8000`

### Test the Endpoint

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

**Expected Response (201 Created):**

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

## API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
├── README.md              # This file
├── webhook.py             # Main application
├── requirements.txt       # Python dependencies
├── schema.json           # JSON Schema definition
├── customer_docs.md      # Integration guide for customers
├── debugging.md          # Testing and troubleshooting guide
├── design.md             # Technical design decisions
└── architecture_diagram.png  # System architecture diagram
```

## Required Fields

All webhook events must include:

|Field           |Type  |Description                       |Example                |
|----------------|------|----------------------------------|-----------------------|
|`event_type`    |string|Event type (see valid types below)|`appointment.scheduled`|
|`appointment_id`|string|Unique appointment identifier     |`A12345`               |
|`patient_id`    |string|Unique patient identifier         |`P8765`                |
|`timestamp`     |string|ISO 8601 formatted datetime       |`2025-01-10T12:30:00Z` |
|`notes`         |string|Optional notes (max 1000 chars)   |`Annual physical`      |

### Valid Event Types

- `appointment.scheduled`
- `appointment.cancelled`
- `appointment.rescheduled`
- `appointment.completed`
- `appointment.no_show`

## Endpoints

|Method|Path                  |Description               |
|------|----------------------|--------------------------|
|GET   |`/`                   |Health check              |
|POST  |`/webhook/appointment`|Receive appointment events|
|GET   |`/webhook/events`     |List stored events (admin)|

## HTTP Status Codes

|Code|Status               |Description                           |
|----|---------------------|--------------------------------------|
|200 |OK                   |Successful GET request                |
|201 |Created              |Event successfully received and stored|
|422 |Unprocessable Entity |Invalid payload structure             |
|500 |Internal Server Error|Server error during processing        |

## Documentation

- **For Customers**: See <customer_docs.md> for integration instructions
- **For Developers**: See <debugging.md> for testing scenarios and troubleshooting
- **Technical Design**: See <design.md> for architecture decisions

## Logging

Events are logged to:

- Console output (real-time)
- `webhook_events.log` file

## Database

Events are stored in `appointments.db` (SQLite). The database is automatically created on first run.

## Production Deployment

For production use, consider:

- Adding authentication (API keys, OAuth)
- Implementing rate limiting
- Switching to PostgreSQL/MySQL
- Enabling HTTPS/TLS
- Adding monitoring and alerting
- Implementing idempotency handling

## Support

For issues or questions:

1. Check <debugging.md> for common problems
1. Review logs in `webhook_events.log`
1. Enable debug mode in the application

## License

[Your License Here]
