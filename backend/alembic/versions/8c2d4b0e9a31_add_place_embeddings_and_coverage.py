"""add place embeddings and coverage fields

Revision ID: 8c2d4b0e9a31
Revises: b58c94f88282
Create Date: 2026-05-09 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "8c2d4b0e9a31"
down_revision: Union[str, Sequence[str], None] = "b58c94f88282"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TYPE hangoutstatus ADD VALUE IF NOT EXISTS 'COVERAGE_PENDING'")
    op.execute("ALTER TYPE hangoutstatus ADD VALUE IF NOT EXISTS 'GENERATING'")

    op.add_column("places", sa.Column("region", sa.String(), nullable=True))
    op.add_column("places", sa.Column("country", sa.String(), nullable=True))
    op.add_column("places", sa.Column("coverage_key", sa.String(), nullable=True))
    op.add_column("places", sa.Column("embedding", Vector(384), nullable=True))
    op.create_index(op.f("ix_places_coverage_key"), "places", ["coverage_key"], unique=False)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_places_embedding_hnsw "
        "ON places USING hnsw (embedding vector_cosine_ops) "
        "WHERE embedding IS NOT NULL"
    )

    op.add_column("hangout_requests", sa.Column("resolved_city", sa.String(), nullable=True))
    op.add_column("hangout_requests", sa.Column("resolved_region", sa.String(), nullable=True))
    op.add_column("hangout_requests", sa.Column("resolved_country", sa.String(), nullable=True))
    op.add_column("hangout_requests", sa.Column("coverage_key", sa.String(), nullable=True))
    op.add_column("hangout_requests", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("hangout_requests", sa.Column("longitude", sa.Float(), nullable=True))
    op.create_index(
        op.f("ix_hangout_requests_coverage_key"),
        "hangout_requests",
        ["coverage_key"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_hangout_requests_coverage_key"), table_name="hangout_requests")
    op.drop_column("hangout_requests", "longitude")
    op.drop_column("hangout_requests", "latitude")
    op.drop_column("hangout_requests", "coverage_key")
    op.drop_column("hangout_requests", "resolved_country")
    op.drop_column("hangout_requests", "resolved_region")
    op.drop_column("hangout_requests", "resolved_city")

    op.execute("DROP INDEX IF EXISTS ix_places_embedding_hnsw")
    op.drop_index(op.f("ix_places_coverage_key"), table_name="places")
    op.drop_column("places", "embedding")
    op.drop_column("places", "coverage_key")
    op.drop_column("places", "country")
    op.drop_column("places", "region")
