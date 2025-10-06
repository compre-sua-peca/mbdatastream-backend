"""merge branches

Revision ID: 2c7786aa65ae
Revises: 23a0f01f68b4, 82cf421964e3
Create Date: 2025-10-01 09:55:43.664614

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c7786aa65ae'
down_revision = ('23a0f01f68b4', '82cf421964e3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
