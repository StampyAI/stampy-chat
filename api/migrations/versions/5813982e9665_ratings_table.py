"""Ratings table

Revision ID: 5813982e9665
Revises: 78806d965229
Create Date: 2023-11-06 17:31:47.814226

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from stampy_chat.db.models import UUID

# revision identifiers, used by Alembic.
revision = '5813982e9665'
down_revision = '78806d965229'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ratings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', UUID(length=16), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('comment', mysql.LONGTEXT(), nullable=True),
        sa.Column('settings', mysql.LONGTEXT(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('rating')
