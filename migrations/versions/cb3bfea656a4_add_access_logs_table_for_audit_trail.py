"""Add access_logs table for audit trail

Revision ID: cb3bfea656a4
Revises: d255df3d9647
Create Date: 2025-12-30 21:31:33.273499

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cb3bfea656a4"
down_revision = "d255df3d9647"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("resource_name", sa.String(length=200), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column("access_granted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        # Optional fields
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("resource_id", sa.String(length=200), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),  # IPv6 max length
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for common query patterns
    op.create_index("idx_access_logs_user_id", "access_logs", ["user_id"])
    op.create_index("idx_access_logs_company_id", "access_logs", ["company_id"])
    op.create_index("idx_access_logs_created_at", "access_logs", ["created_at"])
    op.create_index(
        "idx_access_logs_company_created", "access_logs", ["company_id", "created_at"]
    )
    op.create_index("idx_access_logs_service", "access_logs", ["service"])


def downgrade():
    op.drop_index("idx_access_logs_service", table_name="access_logs")
    op.drop_index("idx_access_logs_company_created", table_name="access_logs")
    op.drop_index("idx_access_logs_created_at", table_name="access_logs")
    op.drop_index("idx_access_logs_company_id", table_name="access_logs")
    op.drop_index("idx_access_logs_user_id", table_name="access_logs")
    op.drop_table("access_logs")
