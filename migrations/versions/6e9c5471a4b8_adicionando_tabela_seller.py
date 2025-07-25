"""Adicionando tabela seller

Revision ID: 6e9c5471a4b8
Revises: ec5e312a0b53
Create Date: 2025-05-29 10:36:13.719862

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e9c5471a4b8'
down_revision = 'ec5e312a0b53'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('seller',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=75), nullable=False),
    sa.Column('cnpj', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('cnpj'),
    sa.UniqueConstraint('name')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('seller')
    # ### end Alembic commands ###
