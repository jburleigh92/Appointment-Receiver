from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
import sqlite3
import logging
import json
from contextlib import contextmanager

# Configure logging

logging.basicConfig(
level=logging.INFO,
format=’%(asctime)s - %(name)s - %(levelname)s - %(message)s’,
handlers=[
logging.FileHandler(‘webhook_events.log’),
logging.StreamHandler()
]
)
logger = logging.getLogger(**name**)

app = FastAPI(
title=“Appointment Webhook API”,
description=“Webhook endpoint for receiving appointment events”,
version=“1.0.0”
)

# Database setup

DB_NAME = “appointments.db”

def init_db():
“”“Initialize SQLite database with appointments table”””
with sqlite3.connect(DB_NAME) as conn:
cursor = conn.cursor()
cursor.execute(”””
CREATE TABLE IF NOT EXISTS appointment_events (
id INTEGER PRIMARY KEY AUTOINCREMENT,
event_type TEXT NOT NULL,
appointment_id TEXT NOT NULL,
patient_id TEXT NOT NULL,
timestamp TEXT NOT NULL,
notes TEXT,
received_at TEXT NOT NULL,
raw_payload TEXT NOT NULL
)
“””)
conn.commit()
logger.info(“Database initialized successfully”)

# Initialize database on startup

init_db()

@contextmanager
def get_db():
“”“Context manager for database connections”””
conn = sqlite3.connect(DB_NAME)
try:
yield conn
finally:
conn.close()

# Pydantic model for request validation

class AppointmentEvent(BaseModel):
event_type: str = Field(
…,
description=“Type of appointment event”,
min_length=1,
max_length=100
)
appointment_id: str = Field(
…,
description=“Unique appointment identifier”,
min_length=1,
max_length=50
)
patient_id: str = Field(
…,
description=“Unique patient identifier”,
min_length=1,
max_length=50
)
timestamp: str = Field(
…,
description=“ISO 8601 formatted timestamp”
)
notes: Optional[str] = Field(
None,
description=“Optional notes about the appointment”,
max_length=1000
)

```
@validator('event_type')
def validate_event_type(cls, v):
    """Validate event_type follows expected pattern"""
    allowed_types = [
        'appointment.scheduled',
        'appointment.cancelled',
        'appointment.rescheduled',
        'appointment.completed',
        'appointment.no_show'
    ]
    if v not in allowed_types:
        raise ValueError(
            f"event_type must be one of: {', '.join(allowed_types)}"
        )
    return v

@validator('timestamp')
def validate_timestamp(cls, v):
    """Validate timestamp is valid ISO 8601 format"""
    try:
        datetime.fromisoformat(v.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise ValueError(
            "timestamp must be in ISO 8601 format (e.g., 2025-01-10T12:30:00Z)"
        )
    return v

class Config:
    schema_extra = {
        "example": {
            "event_type": "appointment.scheduled",
            "appointment_id": "A12345",
            "patient_id": "P8765",
            "timestamp": "2025-01-10T12:30:00Z",
            "notes": "Annual physical"
        }
    }
```

def store_event(event: AppointmentEvent, raw_payload: dict) -> int:
“”“Store event in SQLite database”””
with get_db() as conn:
cursor = conn.cursor()
cursor.execute(”””
INSERT INTO appointment_events
(event_type, appointment_id, patient_id, timestamp, notes, received_at, raw_payload)
VALUES (?, ?, ?, ?, ?, ?, ?)
“””, (
event.event_type,
event.appointment_id,
event.patient_id,
event.timestamp,
event.notes,
datetime.utcnow().isoformat(),
json.dumps(raw_payload)
))
conn.commit()
return cursor.lastrowid

@app.get(”/”, tags=[“Health”])
async def root():
“”“Health check endpoint”””
return {
“status”: “healthy”,
“service”: “Appointment Webhook API”,
“version”: “1.0.0”
}

@app.post(
“/webhook/appointment”,
status_code=status.HTTP_201_CREATED,
tags=[“Webhook”]
)
async def receive_appointment_event(event: AppointmentEvent, request: Request):
“””
Receive and process appointment events

```
Required fields:
- event_type: Type of event (appointment.scheduled, etc.)
- appointment_id: Unique appointment identifier
- patient_id: Unique patient identifier
- timestamp: ISO 8601 formatted timestamp

Optional fields:
- notes: Additional notes about the appointment
"""
try:
    # Get raw JSON for logging
    raw_payload = await request.json()
    
    # Log the incoming event
    logger.info(
        f"Received {event.event_type} event - "
        f"Appointment: {event.appointment_id}, Patient: {event.patient_id}"
    )
    
    # Store in database
    event_id = store_event(event, raw_payload)
    
    # Return success response
    return {
        "status": "success",
        "message": "Event received and stored successfully",
        "event_id": event_id,
        "received_at": datetime.utcnow().isoformat(),
        "data": {
            "event_type": event.event_type,
            "appointment_id": event.appointment_id,
            "patient_id": event.patient_id
        }
    }
    
except Exception as e:
    logger.error(f"Error processing event: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error while processing event"
    )
```

@app.get(”/webhook/events”, tags=[“Admin”])
async def list_events(limit: int = 50):
“”“Retrieve stored events (for testing/admin purposes)”””
try:
with get_db() as conn:
cursor = conn.cursor()
cursor.execute(”””
SELECT id, event_type, appointment_id, patient_id,
timestamp, notes, received_at
FROM appointment_events
ORDER BY received_at DESC
LIMIT ?
“””, (limit,))

```
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "event_type": row[1],
                "appointment_id": row[2],
                "patient_id": row[3],
                "timestamp": row[4],
                "notes": row[5],
                "received_at": row[6]
            })
        
        return {
            "total": len(events),
            "events": events
        }
except Exception as e:
    logger.error(f"Error retrieving events: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error retrieving events"
    )
```

@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
“”“Custom handler for validation errors”””
logger.warning(f”Validation error: {exc}”)
return JSONResponse(
status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
content={
“status”: “error”,
“message”: “Invalid payload structure”,
“errors”: exc.errors() if hasattr(exc, ‘errors’) else str(exc)
}
)

if **name** == “**main**”:
import uvicorn
uvicorn.run(app, host=“0.0.0.0”, port=8000)
