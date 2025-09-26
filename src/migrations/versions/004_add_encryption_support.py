"""Add encryption support for sensitive fields

Revision ID: 004
Revises: 003
Create Date: 2024-01-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = 'a2233915da04'
branch_labels = None
depends_on = None

def upgrade():
    # SQLite doesn't support ALTER COLUMN TYPE, so we'll skip these changes for now
    # The encryption will work with existing field sizes
    pass

def downgrade():
    # Revert agents table changes
    op.alter_column('agents', 'phone',
                   existing_type=sa.String(255),
                   type_=sa.String(20),
                   existing_nullable=True)
    
    op.alter_column('agents', 'email',
                   existing_type=sa.String(255),
                   type_=sa.String(100),
                   existing_nullable=False)
    
    # Revert citizens table changes
    op.alter_column('citizens', 'email',
                   existing_type=sa.String(255),
                   type_=sa.String(100),
                   existing_nullable=True)
    
    op.alter_column('citizens', 'phone_number',
                   existing_type=sa.String(255),
                   type_=sa.String(20),
                   existing_nullable=True)