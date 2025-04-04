"""Adicionando descrição em produtos

Revision ID: 320b44029117
Revises: 5b91f29741ea
Create Date: 2025-04-02 15:56:40.587709

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '320b44029117'
down_revision = '5b91f29741ea'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.String(length=2500), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_column('description')

    # ### end Alembic commands ###
