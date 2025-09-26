"""Merge migration heads

Revision ID: b4006e0193f6
Revises: 005, 986f000fe331
Create Date: 2025-09-13 16:45:55.024828

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4006e0193f6'
down_revision = ('005', '986f000fe331')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
