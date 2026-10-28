"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-28 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'monitored_endpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False, server_default='GET'),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('interval_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('expected_status', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='HEALTHY'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_check_due', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('consecutive_successes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_monitored_endpoints_id'), 'monitored_endpoints', ['id'], unique=False)
    op.create_index(op.f('ix_monitored_endpoints_name'), 'monitored_endpoints', ['name'], unique=False)
    op.create_index(op.f('ix_monitored_endpoints_is_active'), 'monitored_endpoints', ['is_active'], unique=False)
    op.create_index(op.f('ix_monitored_endpoints_status'), 'monitored_endpoints', ['status'], unique=False)
    op.create_index(op.f('ix_monitored_endpoints_next_check_due'), 'monitored_endpoints', ['next_check_due'], unique=False)

    op.create_table(
        'check_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endpoint_id', sa.Integer(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('is_success', sa.Boolean(), nullable=False),
        sa.Column('error_type', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('response_snippet', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['endpoint_id'], ['monitored_endpoints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_check_results_id'), 'check_results', ['id'], unique=False)
    op.create_index(op.f('ix_check_results_endpoint_id'), 'check_results', ['endpoint_id'], unique=False)
    op.create_index(op.f('ix_check_results_is_success'), 'check_results', ['is_success'], unique=False)

    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endpoint_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='HIGH'),
        sa.Column('error_type', sa.String(length=50), nullable=False),
        sa.Column('root_cause', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['endpoint_id'], ['monitored_endpoints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incidents_id'), 'incidents', ['id'], unique=False)
    op.create_index(op.f('ix_incidents_endpoint_id'), 'incidents', ['endpoint_id'], unique=False)
    op.create_index(op.f('ix_incidents_status'), 'incidents', ['status'], unique=False)

    op.create_table(
        'incident_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_incident_events_id'), 'incident_events', ['id'], unique=False)
    op.create_index(op.f('ix_incident_events_incident_id'), 'incident_events', ['incident_id'], unique=False)


def downgrade() -> None:
    op.drop_table('incident_events')
    op.drop_table('incidents')
    op.drop_table('check_results')
    op.drop_table('monitored_endpoints')
