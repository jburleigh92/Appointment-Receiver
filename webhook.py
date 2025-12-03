“””
Healthcare Appointment Webhook Receiver
Main application entry point
“””
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from models import AppointmentEvent, ValidationError
from db import Database
from validators import validate_appointment_event

# Configure logging

logging.basicConfig(
level=logging.INFO,
format=’%(asctime)s - %(name)s - %(levelname)s - %(message)s’,
handlers=[
logging.FileHandler(‘webhook.log’),
logging.StreamHandler()
]
)
logger = logging.getLogger(**name**)

# Database instance

db = Database()

@asynccontextmanager
async def lifespan(app: FastAPI):
“”“Initialize database on startup, cleanup on shutdown”””
logger.info(“Starting webhook service…”)
db.initialize()
logger.info(“Database initialized”)
yield
logger.info(“Shutting down webhook service…”)

app = FastAPI(
title=“Healthcare Appointment Webhook”,
description=“Webhook receiver for healthcare appointment events”,
version=“1.0.0”,
lifespan=lifespan
)

@app.get(”/”)
async def root():
“”“Health check endpoint”””
return {
“service”: “Healthcare Appointment Webhook”,
“status”: “running”,
“timestamp”: datetime.utcnow().isoformat()
}

@app.post(”/webhook/appointments”, status_code=status.HTTP_200_OK)
async def receive_appointment_webhook(request: Request):
“””
Receive and process healthcare appointment webhook events

```
Accepts POST requests with appointment event data and:
- Validates the payload structure
- Checks for duplicate events
- Logs the event
- Stores valid events in the database

Returns:
    200: Event accepted and stored
    400: Invalid payload
    409: Duplicate event
    500: Internal server error
"""
request_id = datetime.utcnow().isoformat()

try:
    # Parse request body
    try:
        payload = await request.json()
        logger.info(f"[{request_id}] Received webhook payload: {payload}")
    except Exception as e:
        logger.error(f"[{request_id}] Failed to parse JSON: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Invalid JSON",
                "message": "Request body must be valid JSON",
                "request_id": request_id
            }
        )
    
    # Validate payload
    try:
        event = validate_appointment_event(payload)
        logger.info(f"[{request_id}] Validation successful for appointment {event.appointment_id}")
    except ValidationError as e:
        logger.warning(f"[{request_id}] Validation failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Validation failed",
                "message": str(e),
                "request_id": request_id
            }
        )
    
    # Check for duplicate
    if db.event_exists(event.appointment_id, event.timestamp):
        logger.warning(f"[{request_id}] Duplicate event detected: {event.appointment_id}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "Duplicate event",
                "message": f"Event for appointment {event.appointment_id} at {event.timestamp} already exists",
                "request_id": request_id
            }
        )
    
    # Store event
    event_id = db.store_event(event)
    logger.info(f"[{request_id}] Event stored successfully with ID: {event_id}")
    
    return {
        "status": "accepted",
        "message": "Appointment event received and stored",
        "event_id": event_id,
        "appointment_id": event.appointment_id,
        "request_id": request_id
    }
    
except Exception as e:
    logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred while processing the event",
            "request_id": request_id
        }
    )
```

@app.get(”/events”, status_code=status.HTTP_200_OK)
async def list_events(limit: int = 100):
“””
List stored appointment events (for testing/debugging)

```
Args:
    limit: Maximum number of events to return (default: 100)
"""
try:
    events = db.get_events(limit=limit)
    return {
        "count": len(events),
        "events": events
    }
except Exception as e:
    logger.error(f"Failed to retrieve events: {str(e)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Failed to retrieve events",
            "message": str(e)
        }
    )
```

if **name** == “**main**”:
import uvicorn
uvicorn.run(app, host=“0.0.0.0”, port=8000)
