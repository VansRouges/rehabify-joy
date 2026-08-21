"""Baseline: current Joy schema.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-20

Idempotent so it is safe on databases that already exist from create_all /
the old SCHEMA_MIGRATIONS list. Future revisions should be one change each.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id UUID PRIMARY KEY,
            phone_number VARCHAR(20),
            display_name VARCHAR(255) NOT NULL,
            consent_given BOOLEAN DEFAULT false,
            consent_at TIMESTAMPTZ,
            intake_step VARCHAR(80),
            intake_data JSONB DEFAULT '{}',
            language_preference VARCHAR(10),
            known_facts JSONB DEFAULT '{}',
            conversation_summary TEXT,
            persona VARCHAR(32) DEFAULT 'patient',
            region VARCHAR(100),
            intake_session_id UUID,
            last_ip_address VARCHAR(45),
            ip_addresses JSONB DEFAULT '[]',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id UUID PRIMARY KEY,
            patient_id UUID NOT NULL REFERENCES patients(id),
            title VARCHAR(255),
            mode VARCHAR(50) DEFAULT 'triage',
            triage_complete BOOLEAN DEFAULT false,
            triage_summary JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY,
            session_id UUID REFERENCES chat_sessions(id),
            patient_id UUID REFERENCES patients(id),
            direction VARCHAR(10) NOT NULL,
            content TEXT NOT NULL,
            message_type VARCHAR(10) DEFAULT 'text',
            audio_url VARCHAR(500),
            red_flag_triggered BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id UUID PRIMARY KEY,
            patient_id UUID NOT NULL REFERENCES patients(id),
            session_id UUID,
            kind VARCHAR(40) NOT NULL,
            payload JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )

    for stmt in (
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
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS region VARCHAR(100)",
        "ALTER TABLE patients ADD COLUMN IF NOT EXISTS intake_session_id UUID",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_type VARCHAR(10) DEFAULT 'text'",
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS audio_url VARCHAR(500)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_patients_phone_number ON patients (phone_number) WHERE phone_number IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS ix_patients_phone_number ON patients (phone_number)",
        "CREATE INDEX IF NOT EXISTS ix_chat_sessions_patient_id ON chat_sessions (patient_id)",
        "CREATE INDEX IF NOT EXISTS ix_messages_patient_id ON messages (patient_id)",
        "CREATE INDEX IF NOT EXISTS ix_audit_events_patient_id ON audit_events (patient_id)",
        "CREATE INDEX IF NOT EXISTS ix_audit_events_session_id ON audit_events (session_id)",
    ):
        op.execute(stmt)


def downgrade() -> None:
    # Baseline is not reversed — existing production data must stay.
    pass
