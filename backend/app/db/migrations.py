"""Idempotent schema updates for databases created before model changes."""

SCHEMA_MIGRATIONS = [
    # patients — add columns if upgrading from earlier schema
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS last_ip_address VARCHAR(45)",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS ip_addresses JSONB DEFAULT '[]'",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT false",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS intake_step VARCHAR(80)",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS intake_data JSONB DEFAULT '{}'",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS language_preference VARCHAR(10)",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS known_facts JSONB DEFAULT '{}'",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS conversation_summary TEXT",
    "ALTER TABLE patients ADD COLUMN IF NOT EXISTS persona VARCHAR(32) DEFAULT 'patient'",
    # messages — voice support
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_type VARCHAR(10) DEFAULT 'text'",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_patients_phone_number ON patients (phone_number) WHERE phone_number IS NOT NULL",
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        id UUID PRIMARY KEY,
        patient_id UUID NOT NULL REFERENCES patients(id),
        session_id UUID,
        kind VARCHAR(40) NOT NULL,
        payload JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_audit_events_patient_id ON audit_events (patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_audit_events_session_id ON audit_events (session_id)",
]
