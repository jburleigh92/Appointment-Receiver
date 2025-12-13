"""
Comprehensive test suite for the Healthcare Appointment Webhook Receiver
Tests validation, database operations, and API endpoints
"""
import pytest
import sqlite3
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient

from webhook import (
    AppointmentEvent,
    SchemaValidator,
    ValidationError,
    Database,
    app,
    db,
    validator
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    test_db = Database(db_path=path)
    test_db.initialize()
    yield test_db
    test_db.close()
    os.unlink(path)


@pytest.fixture
def temp_schema():
    """Create a temporary schema file for testing"""
    fd, path = tempfile.mkstemp(suffix='.json')
    schema = {
        "required_fields": {
            "event_type": "string",
            "appointment_id": "string",
            "patient_id": "string",
            "timestamp": "string"
        },
        "optional_fields": {
            "notes": "string"
        },
        "valid_event_types": [
            "appointment.scheduled",
            "appointment.cancelled",
            "appointment.updated"
        ]
    }
    with os.fdopen(fd, 'w') as f:
        json.dump(schema, f)
    yield path
    os.unlink(path)


@pytest.fixture
def test_validator(temp_schema):
    """Create a validator with a temporary schema"""
    return SchemaValidator(schema_path=temp_schema)


@pytest.fixture(autouse=True)
def setup_test_database():
    """Set up a fresh test database for each test"""
    # Clean up any existing test database
    if os.path.exists("test_appointments.db"):
        os.unlink("test_appointments.db")

    # Override the global db instance with test database
    import webhook
    webhook.db = Database(db_path="test_appointments.db")
    webhook.db.initialize()

    yield

    # Cleanup after test
    webhook.db.close()
    if os.path.exists("test_appointments.db"):
        os.unlink("test_appointments.db")


@pytest.fixture
def client(setup_test_database):
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def valid_payload():
    """Return a valid appointment event payload"""
    return {
        "event_type": "appointment.scheduled",
        "appointment_id": "A12345",
        "patient_id": "P8765",
        "timestamp": "2025-01-10T12:30:00Z",
        "notes": "Annual physical"
    }


# ============================================================================
# APPOINTMENT EVENT TESTS
# ============================================================================

class TestAppointmentEvent:
    """Test the AppointmentEvent dataclass"""

    def test_create_event_with_notes(self):
        """Test creating an event with all fields"""
        event = AppointmentEvent(
            event_type="appointment.scheduled",
            appointment_id="A001",
            patient_id="P001",
            timestamp="2025-01-10T12:30:00Z",
            notes="Test note"
        )
        assert event.event_type == "appointment.scheduled"
        assert event.appointment_id == "A001"
        assert event.patient_id == "P001"
        assert event.timestamp == "2025-01-10T12:30:00Z"
        assert event.notes == "Test note"

    def test_create_event_without_notes(self):
        """Test creating an event without optional notes"""
        event = AppointmentEvent(
            event_type="appointment.cancelled",
            appointment_id="A002",
            patient_id="P002",
            timestamp="2025-01-11T14:00:00Z"
        )
        assert event.notes is None

    def test_to_dict(self):
        """Test converting event to dictionary"""
        event = AppointmentEvent(
            event_type="appointment.updated",
            appointment_id="A003",
            patient_id="P003",
            timestamp="2025-01-12T09:15:00Z",
            notes="Updated time"
        )
        event_dict = event.to_dict()
        assert event_dict == {
            "event_type": "appointment.updated",
            "appointment_id": "A003",
            "patient_id": "P003",
            "timestamp": "2025-01-12T09:15:00Z",
            "notes": "Updated time"
        }


# ============================================================================
# SCHEMA VALIDATOR TESTS
# ============================================================================

class TestSchemaValidator:
    """Test the SchemaValidator class"""

    def test_validate_valid_payload(self, test_validator, valid_payload):
        """Test validation with a valid payload"""
        event = test_validator.validate(valid_payload)
        assert isinstance(event, AppointmentEvent)
        assert event.event_type == "appointment.scheduled"
        assert event.appointment_id == "A12345"
        assert event.patient_id == "P8765"

    def test_validate_non_dict_payload(self, test_validator):
        """Test validation fails for non-dictionary payload"""
        with pytest.raises(ValidationError, match="Payload must be a JSON object"):
            test_validator.validate("not a dict")

    def test_validate_missing_required_field(self, test_validator):
        """Test validation fails when required fields are missing"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A001",
            "timestamp": "2025-01-10T12:30:00Z"
            # Missing patient_id
        }
        with pytest.raises(ValidationError, match="Missing required fields: patient_id"):
            test_validator.validate(payload)

    def test_validate_multiple_missing_fields(self, test_validator):
        """Test validation fails with multiple missing fields"""
        payload = {
            "event_type": "appointment.scheduled"
            # Missing appointment_id, patient_id, timestamp
        }
        with pytest.raises(ValidationError, match="Missing required fields"):
            test_validator.validate(payload)

    def test_validate_null_required_field(self, test_validator):
        """Test validation fails when required field is null"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A001",
            "patient_id": None,
            "timestamp": "2025-01-10T12:30:00Z"
        }
        with pytest.raises(ValidationError, match="Field 'patient_id' cannot be null"):
            test_validator.validate(payload)

    def test_validate_wrong_field_type(self, test_validator):
        """Test validation fails when field type is incorrect"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": 12345,  # Should be string
            "patient_id": "P001",
            "timestamp": "2025-01-10T12:30:00Z"
        }
        with pytest.raises(ValidationError, match="Field 'appointment_id' must be a string"):
            test_validator.validate(payload)

    def test_validate_invalid_event_type(self, test_validator):
        """Test validation fails with invalid event type"""
        payload = {
            "event_type": "appointment.deleted",  # Not in valid types
            "appointment_id": "A001",
            "patient_id": "P001",
            "timestamp": "2025-01-10T12:30:00Z"
        }
        with pytest.raises(ValidationError, match="Invalid event_type"):
            test_validator.validate(payload)

    def test_validate_invalid_timestamp_format(self, test_validator):
        """Test validation fails with invalid timestamp"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A001",
            "patient_id": "P001",
            "timestamp": "not-a-timestamp"
        }
        with pytest.raises(ValidationError, match="Invalid timestamp format"):
            test_validator.validate(payload)

    def test_validate_empty_appointment_id(self, test_validator):
        """Test validation fails with empty appointment_id"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "   ",  # Only whitespace
            "patient_id": "P001",
            "timestamp": "2025-01-10T12:30:00Z"
        }
        with pytest.raises(ValidationError, match="appointment_id cannot be empty"):
            test_validator.validate(payload)

    def test_validate_empty_patient_id(self, test_validator):
        """Test validation fails with empty patient_id"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A001",
            "patient_id": "",
            "timestamp": "2025-01-10T12:30:00Z"
        }
        with pytest.raises(ValidationError, match="patient_id cannot be empty"):
            test_validator.validate(payload)

    def test_validate_with_optional_notes(self, test_validator, valid_payload):
        """Test validation succeeds with optional notes field"""
        event = test_validator.validate(valid_payload)
        assert event.notes == "Annual physical"

    def test_validate_without_optional_notes(self, test_validator):
        """Test validation succeeds without optional notes"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A001",
            "patient_id": "P001",
            "timestamp": "2025-01-10T12:30:00Z"
        }
        event = test_validator.validate(payload)
        assert event.notes is None

    def test_validate_all_event_types(self, test_validator):
        """Test validation works for all valid event types"""
        event_types = [
            "appointment.scheduled",
            "appointment.cancelled",
            "appointment.updated"
        ]
        for event_type in event_types:
            payload = {
                "event_type": event_type,
                "appointment_id": "A001",
                "patient_id": "P001",
                "timestamp": "2025-01-10T12:30:00Z"
            }
            event = test_validator.validate(payload)
            assert event.event_type == event_type

    def test_load_schema_file_not_found(self):
        """Test validator uses default schema when file not found"""
        validator = SchemaValidator(schema_path="nonexistent.json")
        assert validator.schema is not None
        assert "required_fields" in validator.schema


# ============================================================================
# DATABASE TESTS
# ============================================================================

class TestDatabase:
    """Test the Database class"""

    def test_initialize_creates_table(self, temp_db):
        """Test that initialize creates the events table"""
        cursor = temp_db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='appointment_events'
        """)
        result = cursor.fetchone()
        assert result is not None

    def test_initialize_creates_index(self, temp_db):
        """Test that initialize creates the index"""
        cursor = temp_db.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_appointment_timestamp'
        """)
        result = cursor.fetchone()
        assert result is not None

    def test_store_event(self, temp_db):
        """Test storing an event"""
        event = AppointmentEvent(
            event_type="appointment.scheduled",
            appointment_id="A001",
            patient_id="P001",
            timestamp="2025-01-10T12:30:00Z",
            notes="Test event"
        )
        event_id = temp_db.store_event(event)
        assert event_id > 0

    def test_store_event_without_notes(self, temp_db):
        """Test storing an event without notes"""
        event = AppointmentEvent(
            event_type="appointment.cancelled",
            appointment_id="A002",
            patient_id="P002",
            timestamp="2025-01-11T14:00:00Z"
        )
        event_id = temp_db.store_event(event)
        assert event_id > 0

    def test_store_duplicate_event_raises_error(self, temp_db):
        """Test that storing duplicate event raises IntegrityError"""
        event = AppointmentEvent(
            event_type="appointment.scheduled",
            appointment_id="A003",
            patient_id="P003",
            timestamp="2025-01-12T09:00:00Z"
        )
        temp_db.store_event(event)

        # Try to store the same event again
        with pytest.raises(sqlite3.IntegrityError):
            temp_db.store_event(event)

    def test_event_exists_returns_true_for_existing(self, temp_db):
        """Test event_exists returns True for existing event"""
        event = AppointmentEvent(
            event_type="appointment.scheduled",
            appointment_id="A004",
            patient_id="P004",
            timestamp="2025-01-13T10:00:00Z"
        )
        temp_db.store_event(event)

        assert temp_db.event_exists("A004", "2025-01-13T10:00:00Z") is True

    def test_event_exists_returns_false_for_nonexistent(self, temp_db):
        """Test event_exists returns False for non-existent event"""
        assert temp_db.event_exists("A999", "2025-01-20T15:00:00Z") is False

    def test_get_events_returns_all_events(self, temp_db):
        """Test get_events returns all stored events"""
        events = [
            AppointmentEvent("appointment.scheduled", "A001", "P001", "2025-01-10T12:00:00Z"),
            AppointmentEvent("appointment.cancelled", "A002", "P002", "2025-01-11T13:00:00Z"),
            AppointmentEvent("appointment.updated", "A003", "P003", "2025-01-12T14:00:00Z")
        ]

        for event in events:
            temp_db.store_event(event)

        retrieved = temp_db.get_events(limit=100)
        assert len(retrieved) == 3

    def test_get_events_respects_limit(self, temp_db):
        """Test get_events respects the limit parameter"""
        for i in range(10):
            event = AppointmentEvent(
                event_type="appointment.scheduled",
                appointment_id=f"A{i:03d}",
                patient_id=f"P{i:03d}",
                timestamp=f"2025-01-{i+1:02d}T12:00:00Z"
            )
            temp_db.store_event(event)

        retrieved = temp_db.get_events(limit=5)
        assert len(retrieved) == 5

    def test_get_events_returns_most_recent_first(self, temp_db):
        """Test get_events returns events in reverse chronological order"""
        event1 = AppointmentEvent("appointment.scheduled", "A001", "P001", "2025-01-10T12:00:00Z")
        event2 = AppointmentEvent("appointment.scheduled", "A002", "P002", "2025-01-11T12:00:00Z")

        temp_db.store_event(event1)
        temp_db.store_event(event2)

        events = temp_db.get_events(limit=10)
        # Most recently stored should be first
        assert events[0]["appointment_id"] == "A002"
        assert events[1]["appointment_id"] == "A001"


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================

class TestAPIEndpoints:
    """Test FastAPI endpoints"""

    def test_health_check(self, client):
        """Test the health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Healthcare Appointment Webhook"
        assert data["status"] == "running"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_webhook_valid_payload(self, client, valid_payload):
        """Test webhook with valid payload"""
        response = client.post("/webhook/appointments", json=valid_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "event_id" in data
        assert data["appointment_id"] == "A12345"
        assert "request_id" in data

    def test_webhook_invalid_json(self, client):
        """Test webhook with invalid JSON"""
        response = client.post(
            "/webhook/appointments",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Invalid JSON"

    def test_webhook_missing_required_field(self, client):
        """Test webhook with missing required field"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A001",
            "timestamp": "2025-01-10T12:30:00Z"
            # Missing patient_id
        }
        response = client.post("/webhook/appointments", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Validation failed"
        assert "patient_id" in data["message"]

    def test_webhook_invalid_event_type(self, client):
        """Test webhook with invalid event type"""
        payload = {
            "event_type": "appointment.deleted",
            "appointment_id": "A001",
            "patient_id": "P001",
            "timestamp": "2025-01-10T12:30:00Z"
        }
        response = client.post("/webhook/appointments", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Validation failed"
        assert "Invalid event_type" in data["message"]

    def test_webhook_duplicate_event(self, client):
        """Test webhook rejects duplicate events"""
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A_DUPLICATE",
            "patient_id": "P001",
            "timestamp": "2025-01-10T12:30:00Z"
        }

        # First request should succeed
        response1 = client.post("/webhook/appointments", json=payload)
        assert response1.status_code == 200

        # Second identical request should return 409 Conflict
        response2 = client.post("/webhook/appointments", json=payload)
        assert response2.status_code == 409
        data = response2.json()
        assert data["error"] == "Duplicate event"

    def test_webhook_all_event_types(self, client):
        """Test webhook accepts all valid event types"""
        event_types = [
            "appointment.scheduled",
            "appointment.cancelled",
            "appointment.updated"
        ]

        for i, event_type in enumerate(event_types):
            payload = {
                "event_type": event_type,
                "appointment_id": f"A{i:03d}",
                "patient_id": f"P{i:03d}",
                "timestamp": f"2025-01-{i+10:02d}T12:30:00Z"
            }
            response = client.post("/webhook/appointments", json=payload)
            assert response.status_code == 200

    def test_list_events_endpoint(self, client):
        """Test the list events endpoint"""
        # First, create some events
        for i in range(3):
            payload = {
                "event_type": "appointment.scheduled",
                "appointment_id": f"A_LIST_{i:03d}",
                "patient_id": f"P{i:03d}",
                "timestamp": f"2025-01-{i+15:02d}T12:30:00Z"
            }
            client.post("/webhook/appointments", json=payload)

        # Now retrieve them
        response = client.get("/events?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "events" in data
        assert data["count"] >= 3

    def test_list_events_with_limit(self, client):
        """Test list events respects limit parameter"""
        response = client.get("/events?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 5


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for the complete workflow"""

    def test_complete_workflow(self, client):
        """Test complete workflow from webhook to retrieval"""
        # 1. Send a webhook event
        payload = {
            "event_type": "appointment.scheduled",
            "appointment_id": "A_WORKFLOW",
            "patient_id": "P_WORKFLOW",
            "timestamp": "2025-01-20T15:00:00Z",
            "notes": "Integration test"
        }

        response = client.post("/webhook/appointments", json=payload)
        assert response.status_code == 200
        event_id = response.json()["event_id"]

        # 2. Verify event is stored
        response = client.get("/events")
        assert response.status_code == 200
        events = response.json()["events"]

        # Find our event
        our_event = next(
            (e for e in events if e["appointment_id"] == "A_WORKFLOW"),
            None
        )
        assert our_event is not None
        assert our_event["event_type"] == "appointment.scheduled"
        assert our_event["patient_id"] == "P_WORKFLOW"
        assert our_event["notes"] == "Integration test"

    def test_multiple_events_same_appointment(self, client):
        """Test handling multiple events for the same appointment"""
        appointment_id = "A_MULTI_EVENT"

        # Schedule appointment
        payload1 = {
            "event_type": "appointment.scheduled",
            "appointment_id": appointment_id,
            "patient_id": "P001",
            "timestamp": "2025-01-20T10:00:00Z"
        }
        response1 = client.post("/webhook/appointments", json=payload1)
        assert response1.status_code == 200

        # Update appointment (different timestamp)
        payload2 = {
            "event_type": "appointment.updated",
            "appointment_id": appointment_id,
            "patient_id": "P001",
            "timestamp": "2025-01-20T11:00:00Z",
            "notes": "Time changed"
        }
        response2 = client.post("/webhook/appointments", json=payload2)
        assert response2.status_code == 200

        # Cancel appointment (different timestamp)
        payload3 = {
            "event_type": "appointment.cancelled",
            "appointment_id": appointment_id,
            "patient_id": "P001",
            "timestamp": "2025-01-20T12:00:00Z"
        }
        response3 = client.post("/webhook/appointments", json=payload3)
        assert response3.status_code == 200

        # All three should be stored
        assert response1.json()["event_id"] != response2.json()["event_id"]
        assert response2.json()["event_id"] != response3.json()["event_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
