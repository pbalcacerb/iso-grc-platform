"""add findings checklist item foreign key

Revision ID: 9f0cb9027dda
Revises: 2d24c946bcb1
Create Date: 2026-09-13 14:28:55.837671
"""

from alembic import op


revision = "9f0cb9027dda"
down_revision = "2d24c946bcb1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'findings_checklist_item_id_fkey'
                  AND conrelid = 'findings'::regclass
            ) THEN
                ALTER TABLE findings
                ADD CONSTRAINT findings_checklist_item_id_fkey
                FOREIGN KEY (checklist_item_id)
                REFERENCES audit_checklist_items(id)
                ON DELETE CASCADE;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE findings
        DROP CONSTRAINT IF EXISTS findings_checklist_item_id_fkey;
    """)