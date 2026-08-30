"""Vincular membresías de cliente a un Client (aislamiento por cliente).

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001_fundacion"  # ← ajusta si tu revision real difiere
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("memberships", sa.Column("client_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_memberships_client_id", "memberships", "clients",
        ["client_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_memberships_client_id", "memberships", type_="foreignkey")
    op.drop_column("memberships", "client_id")