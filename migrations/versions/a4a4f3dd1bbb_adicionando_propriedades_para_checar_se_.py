"""Adicionando propriedades para checar se produto está ativo e ainda é produzido

Revision ID: a4a4f3dd1bbb
Revises: 320b44029117
Create Date: 2025-04-03 09:51:47.788118

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4a4f3dd1bbb'
down_revision = '320b44029117'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('is_manufactured', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_column('is_manufactured')
        batch_op.drop_column('is_active')

    # ### end Alembic commands ###
