"""Interactions table

Revision ID: 78806d965229
Revises:
Create Date: 2023-08-24 16:26:36.265228

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from stampy_chat.db.models import UUID

# revision identifiers, used by Alembic.
revision = '78806d965229'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', UUID(length=16), nullable=False),
        sa.Column('interaction_no', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(length=1028), nullable=False),
        sa.Column('prompt', mysql.LONGTEXT(), nullable=True),
        sa.Column('response', mysql.LONGTEXT(), nullable=True),
        sa.Column('chunks', sa.String(length=1028), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('moderation', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('interactions')
