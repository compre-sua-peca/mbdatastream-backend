"""Criando chave composta entre id_image e cod_product

Revision ID: 285f1f6c7052
Revises: 7c3c19335a27
Create Date: 2025-06-05 17:31:20.316644
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '285f1f6c7052'
down_revision = '7c3c19335a27'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Dropar a foreign key existente (images_ibfk_1 → product.cod_product)
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.drop_constraint('images_ibfk_1', type_='foreignkey')

    # 2) Dropar a PK atual (que era apenas id_image)
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='primary')

    # 3) Criar a nova PK composta (cod_product, id_image)
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.create_primary_key(
            None,                  # nenhum nome explícito; MySQL tratará como PRIMARY
            ['cod_product', 'id_image']
        )

    # 4) Recriar a foreign key em cod_product → product.cod_product
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'images_ibfk_1',       # nome da constraint
            'product',             # tabela referenciada
            ['cod_product'],       # coluna(s) em images
            ['cod_product'],       # coluna(s) em product
            onupdate='CASCADE',
            ondelete='CASCADE'
        )


def downgrade():
    # Para voltar atrás:
    # 1) Dropar a foreign key atual (images_ibfk_1)
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.drop_constraint('images_ibfk_1', type_='foreignkey')

    # 2) Dropar a PK composta (cod_product, id_image)
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='primary')

    # 3) Recriar a PK original apenas em id_image
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.create_primary_key(
            None,             # MySQL a interpretará como PRIMARY
            ['id_image']      # voltamos a ter primary key somente em id_image
        )

    # 4) Recriar a foreign key antiga (images_ibfk_1 → product.cod_product)
    with op.batch_alter_table('images', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'images_ibfk_1',
            'product',
            ['cod_product'],
            ['cod_product'],
            onupdate='CASCADE',
            ondelete='CASCADE'
        )
