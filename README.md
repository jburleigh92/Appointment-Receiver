# Healthcare Appointment Webhook Receiver

A production-ready webhook service for receiving and processing healthcare appointment events with comprehensive validation, logging, and persistence.

## 📋 Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn python-multipart

# Run the service
python webhook.py
```

The service will start on `http://localhost:8000`

## 🗂️ Project Structure

```
├── README.md                 # Main documentation (this file)
├── design.md                 # Technical design decisions
├── webhook.py                # Complete webhook service implementation
├── schema.json               # JSON validation schema
├── debugging.md              # Troubleshooting and debugging guide
├── customer_docs.md          # Customer-facing API documentation
├── architecture_diagram.png  # System architecture visualization
├── requirements.txt          # Python dependencies
├── appointments.db           # SQLite database (auto-created)
└── webhook.log              # Application logs (auto-created)
```

## 🎯 Overview

This webhook service provides:

- **RESTful API endpoint** for appointment events (`POST /webhook/appointments`)
- **JSON schema validation** with detailed error messages
- **Duplicate detection** to prevent processing the same event twice
- **SQLite persistence** with automatic database initialization
- **Comprehensive logging** to both file and console
- **Proper HTTP status codes** (200, 400, 409, 500)
- **Request ID tracking** for debugging and audit trails

## 🔧 Tech Stack

|Component    |Technology          |Purpose                                             |
|-------------|--------------------|----------------------------------------------------|
|Web Framework|FastAPI             |Modern, fast API framework with automatic validation|
|Server       |Uvicorn             |ASGI server for running the application             |
|Database     |SQLite              |Lightweight embedded database for event storage     |
|Logging      |Python logging      |Structured logging to file and console              |
|Validation   |Custom + schema.json|Schema-based validation with clear error messages   |

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Create project directory**
   
   ```bash
   mkdir webhook-receiver
   cd webhook-receiver
   ```
1. **Create virtual environment (recommended)**
   
   ```bash
   python -m venv venv
   
   # Activate on macOS/Linux
   source venv/bin/activate
   
   # Activate on Windows
   venv\Scripts\activate
   ```
1. **Install dependencies**
   
   ```bash
   pip install fastapi uvicorn python-multipart
   ```
1. **Add project files**
- Copy `webhook.py` to the directory
- Copy `schema.json` to the directory
- Optionally copy documentation files
1. **Run the service**
   
   ```bash
   python webhook.py
   ```

## 🚀 Usage

### Basic Request

```bash
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "appointment.scheduled",
    "appointment_id": "A12345",
    "patient_id": "P8765",
    "timestamp": "2025-01-10T12:30:00Z",
    "notes": "Annual physical"
  }'
```

### Response

```json
{
  "status": "accepted",
  "message": "Appointment event received and stored",
  "event_id": 1,
  "appointment_id": "A12345",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

## 📊 API Endpoints

|Endpoint               |Method|Description                             |
|-----------------------|------|----------------------------------------|
|`/`                    |GET   |Health check - verify service is running|
|`/webhook/appointments`|POST  |Receive appointment events              |
|`/events`              |GET   |List stored events (for debugging)      |

## ✅ Validation Rules

The service validates all incoming events against `schema.json`:

### Required Fields

- `event_type` (string) - Must be one of:
  - `appointment.scheduled`
  - `appointment.cancelled`
  - `appointment.updated`
- `appointment_id` (string) - Non-empty appointment identifier
- `patient_id` (string) - Non-empty patient identifier
- `timestamp` (string) - ISO 8601 format (e.g., `2025-01-10T12:30:00Z`)

### Optional Fields

- `notes` (string) - Additional information about the appointment

### Validation Checks

1. ✓ All required fields present
1. ✓ Field types match expected types
1. ✓ No null values in required fields
1. ✓ Valid event_type from allowed list
1. ✓ Valid ISO 8601 timestamp format
1. ✓ Non-empty appointment_id and patient_id
1. ✓ No duplicate events (same appointment_id + timestamp)

## 📝 Response Codes

|Code   |Status               |When It Occurs                                                    |
|-------|---------------------|------------------------------------------------------------------|
|**200**|Success              |Event validated and stored successfully                           |
|**400**|Bad Request          |Invalid JSON, missing fields, type mismatch, or validation failure|
|**409**|Conflict             |Duplicate event (same appointment_id + timestamp already exists)  |
|**500**|Internal Server Error|Unexpected system error during processing                         |

## 🔍 Logging

All events are logged to:

- **Console** - Real-time monitoring
- **webhook.log** - Persistent audit trail

Log entries include:

- Timestamp
- Request ID
- Full payload
- Validation results
- Database operations
- Error details with stack traces

## 💾 Data Persistence

Events are stored in SQLite (`appointments.db`) with:

- Automatic table creation on first run
- Unique constraint on appointment_id + timestamp
- Index for query performance
- All event fields preserved
- Received timestamp for audit

### Querying the Database

```bash
# Open database
sqlite3 appointments.db

# View all events
SELECT * FROM appointment_events;

# Count total events
SELECT COUNT(*) FROM appointment_events;

# Find specific appointment
SELECT * FROM appointment_events WHERE appointment_id = 'A12345';
```

## 📚 Additional Documentation

- **<design.md>** - Technical architecture and design decisions
- **<customer_docs.md>** - API reference for webhook consumers
- **<debugging.md>** - Troubleshooting guide and common issues
- **<schema.json>** - Detailed validation schema specification

## 🧪 Testing

Test the service with various scenarios:

```bash
# Valid request
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{"event_type":"appointment.scheduled","appointment_id":"A001","patient_id":"P001","timestamp":"2025-01-10T12:30:00Z"}'

# Missing field (should return 400)
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{"event_type":"appointment.scheduled","appointment_id":"A001","timestamp":"2025-01-10T12:30:00Z"}'

# Invalid event type (should return 400)
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{"event_type":"appointment.deleted","appointment_id":"A001","patient_id":"P001","timestamp":"2025-01-10T12:30:00Z"}'

# Duplicate (send same request twice, second should return 409)
curl -X POST http://localhost:8000/webhook/appointments \
  -H "Content-Type: application/json" \
  -d '{"event_type":"appointment.scheduled","appointment_id":"A999","patient_id":"P999","timestamp":"2025-01-10T12:30:00Z"}'
```

## 🔧 Configuration

Key configuration variables in `webhook.py`:

```python
DB_PATH = "appointments.db"      # SQLite database file
SCHEMA_PATH = "schema.json"      # Validation schema file
LOG_FILE = "webhook.log"         # Log file path
```

To run on a different port:

```python
# At the bottom of webhook.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Change port here
```

## 🚨 Error Handling

The service provides detailed error messages:

### Invalid JSON

```json
{
  "error": "Invalid JSON",
  "message": "Request body must be valid JSON",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

### Validation Failure

```json
{
  "error": "Validation failed",
  "message": "Missing required fields: patient_id",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

### Duplicate Event

```json
{
  "error": "Duplicate event",
  "message": "Event for appointment A12345 at 2025-01-10T12:30:00Z already exists",
  "request_id": "2025-01-10T14:23:15.123456"
}
```

## 🎓 Learning Points

This implementation demonstrates:

1. **Clean Architecture** - Separation of concerns (validation, storage, API)
1. **Error Handling** - Graceful handling with appropriate HTTP codes
1. **Input Validation** - Schema-based validation with clear error messages
1. **Logging** - Comprehensive logging for debugging and audit
1. **Idempotency** - Duplicate detection prevents reprocessing
1. **RESTful Design** - Proper HTTP methods and status codes
1. **Documentation** - Clear, comprehensive documentation structure

## 📄 License

MIT License - Free to use and modify

## 🤝 Support

For issues or questions:

1. Check `debugging.md` for common problems
1. Review logs in `webhook.log`
1. Consult `customer_docs.md` for API details
1. Examine `design.md` for architectural decisions
