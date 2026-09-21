"""Widen interactions.query and .chunks from VARCHAR(1028) to LONGTEXT

Long pasted queries failed to log at all ("Data too long for column 'query'",
~200 lost rows in Aug-Sep 2026). Applied by hand on prod 2026-09-21.

Revision ID: a1c3f2e9b7d4
Revises: 5813982e9665
Create Date: 2026-09-21 16:20:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'a1c3f2e9b7d4'
down_revision = '5813982e9665'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('interactions', 'query', type_=mysql.LONGTEXT(), existing_nullable=False)
    op.alter_column('interactions', 'chunks', type_=mysql.LONGTEXT(), existing_nullable=True)


def downgrade() -> None:  # truncates anything longer than 1028
    op.alter_column('interactions', 'query', type_=sa.String(length=1028), existing_nullable=False)
    op.alter_column('interactions', 'chunks', type_=sa.String(length=1028), existing_nullable=True)
