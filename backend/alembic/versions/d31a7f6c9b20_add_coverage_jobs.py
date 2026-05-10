"""add coverage jobs

Revision ID: d31a7f6c9b20
Revises: 8c2d4b0e9a31
Create Date: 2026-05-09 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d31a7f6c9b20"
down_revision: Union[str, Sequence[str], None] = "8c2d4b0e9a31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "coverage_jobs",
        sa.Column("coverage_key", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "COMPLETED", "FAILED", name="coveragejobstatus"),
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("coverage_key"),
    )
    op.create_index(op.f("ix_coverage_jobs_coverage_key"), "coverage_jobs", ["coverage_key"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_coverage_jobs_coverage_key"), table_name="coverage_jobs")
    op.drop_table("coverage_jobs")
    op.execute("DROP TYPE IF EXISTS coveragejobstatus")
