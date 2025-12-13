"""
Healthcare Appointment Webhook Receiver
Complete implementation in a single file
"""
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = "appointments.db"
SCHEMA_PATH = "schema.json"
LOG_FILE = "webhook.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

@dataclass
class AppointmentEvent:
    """Represents a healthcare appointment event"""
    event_type: str
    appointment_id: str
    patient_id: str
    timestamp: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format"""
        return {
            "event_type": self.event_type,
            "appointment_id": self.appointment_id,
            "patient_id": self.patient_id,
            "timestamp": self.timestamp,
            "notes": self.notes
        }

# ============================================================================
# SCHEMA VALIDATION
# ============================================================================

class SchemaValidator:
    """Validates appointment events against JSON schema"""

    # Valid event types
    VALID_EVENT_TYPES = {
        "appointment.scheduled",
        "appointment.cancelled",
        "appointment.updated"
    }

    def __init__(self, schema_path: str = SCHEMA_PATH):
        """Initialize validator and load schema"""
        self.schema_path = schema_path
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file"""
        try:
            if Path(self.schema_path).exists():
                with open(self.schema_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Schema file not found at {self.schema_path}, using default")
                return self._get_default_schema()
        except Exception as e:
            logger.error(f"Failed to load schema: {e}")
            return self._get_default_schema()

    def _get_default_schema(self) -> Dict[str, Any]:
        """Return default schema if file not found"""
        return {
            "required_fields": {
                "event_type": "string",
                "appointment_id": "string",
                "patient_id": "string",
                "timestamp": "string"
            },
            "optional_fields": {
                "notes": "string"
            },
            "valid_event_types": list(self.VALID_EVENT_TYPES)
        }

    def validate(self, payload: Dict[str, Any]) -> AppointmentEvent:
        """
        Validate an appointment event payload

        Args:
            payload: Dictionary containing event data

        Returns:
            AppointmentEvent: Validated event object

        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(payload, dict):
            raise ValidationError("Payload must be a JSON object")

        # Get field definitions from schema
        required_fields = self.schema.get("required_fields", {})
        optional_fields = self.schema.get("optional_fields", {})

        # Check for required fields
        missing_fields = []
        for field in required_fields:
            if field not in payload:
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Validate required field types
        for field, expected_type in required_fields.items():
            value = payload[field]
            if value is None:
                raise ValidationError(f"Field '{field}' cannot be null")

            if expected_type == "string" and not isinstance(value, str):
                raise ValidationError(
                    f"Field '{field}' must be a string, got {type(value).__name__}"
                )

        # Validate optional fields if present
        for field, expected_type in optional_fields.items():
            if field in payload and payload[field] is not None:
                if expected_type == "string" and not isinstance(payload[field], str):
                    raise ValidationError(
                        f"Field '{field}' must be a string, got {type(payload[field]).__name__}"
                    )

        # Validate event_type
        event_type = payload["event_type"]
        valid_types = set(self.schema.get("valid_event_types", self.VALID_EVENT_TYPES))
        if event_type not in valid_types:
            raise ValidationError(
                f"Invalid event_type '{event_type}'. "
                f"Must be one of: {', '.join(sorted(valid_types))}"
            )

        # Validate timestamp format (ISO 8601)
        timestamp = payload["timestamp"]
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise ValidationError(
                f"Invalid timestamp format. Must be ISO 8601 format "
                f"(e.g., '2025-01-10T12:30:00Z'). Error: {str(e)}"
            )

        # Validate non-empty strings
        if not payload["appointment_id"].strip():
            raise ValidationError("appointment_id cannot be empty or whitespace")

        if not payload["patient_id"].strip():
            raise ValidationError("patient_id cannot be empty or whitespace")

        # Create and return the event object
        return AppointmentEvent(
            event_type=payload["event_type"],
            appointment_id=payload["appointment_id"],
            patient_id=payload["patient_id"],
            timestamp=payload["timestamp"],
            notes=payload.get("notes")
        )

# ============================================================================
# DATABASE LAYER
# ============================================================================

class Database:
    """SQLite database handler for appointment events"""

    def __init__(self, db_path: str = DB_PATH):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def initialize(self):
        """Create database tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointment_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                appointment_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT,
                received_at TEXT NOT NULL,
                UNIQUE(appointment_id, timestamp)
            )
        """)

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointment_timestamp
            ON appointment_events(appointment_id, timestamp)
        """)

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def store_event(self, event: AppointmentEvent) -> int:
        """
        Store an appointment event in the database

        Args:
            event: AppointmentEvent object to store

        Returns:
            int: ID of the stored event

        Raises:
            sqlite3.IntegrityError: If duplicate event exists
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO appointment_events
                (event_type, appointment_id, patient_id, timestamp, notes, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event.event_type,
                event.appointment_id,
                event.patient_id,
                event.timestamp,
                event.notes,
                datetime.utcnow().isoformat()
            ))

            self.conn.commit()
            event_id = cursor.lastrowid
            logger.info(f"Stored event with ID {event_id}")
            return event_id

        except sqlite3.IntegrityError as e:
            logger.error(f"Failed to store event: {str(e)}")
            raise

    def event_exists(self, appointment_id: str, timestamp: str) -> bool:
        """Check if an event already exists"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM appointment_events
            WHERE appointment_id = ? AND timestamp = ?
        """, (appointment_id, timestamp))

        result = cursor.fetchone()
        return result['count'] > 0

    def get_events(self, limit: int = 100) -> List[Dict]:
        """Retrieve stored events"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, event_type, appointment_id, patient_id,
                   timestamp, notes, received_at
            FROM appointment_events
            ORDER BY received_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Global instances
db = Database()
validator = SchemaValidator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, cleanup on shutdown"""
    logger.info("Starting webhook service...")
    db.initialize()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down webhook service...")
    db.close()

app = FastAPI(
    title="Healthcare Appointment Webhook",
    description="Webhook receiver for healthcare appointment events",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "Healthcare Appointment Webhook",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.post("/webhook/appointments", status_code=status.HTTP_200_OK)
async def receive_appointment_webhook(request: Request):
    """
    Receive and process healthcare appointment webhook events

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
            event = validator.validate(payload)
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

@app.get("/events", status_code=status.HTTP_200_OK)
async def list_events(limit: int = 100):
    """List stored appointment events (for testing/debugging)"""
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

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
