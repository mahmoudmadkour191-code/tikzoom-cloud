"""initial schema

Revision ID: 20250903_000001
Revises: 
Create Date: 2025-09-03 00:00:01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250903_000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    item_type = postgresql.ENUM('service', 'digital', name='item_type')
    item_type.create(op.get_bind(), checkfirst=True)

    payment_method = postgresql.ENUM('36', '44', name='payment_method', create_type=False)
    # We will not create ENUM as strings; instead, use an integer column with CHECK

    order_status = postgresql.ENUM('created', 'pending', 'paid', 'failed', 'canceled', name='order_status')
    order_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tg_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('first_name', sa.String(length=64), nullable=True),
        sa.Column('last_name', sa.String(length=64), nullable=True),
        sa.Column('language_code', sa.String(length=64), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_tg_id', 'users', ['tg_id'], unique=True)

    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price_minor', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.Enum('service', 'digital', name='item_type'), nullable=False),
        sa.Column('image_file_id', sa.String(length=256), nullable=True),

        sa.Column('service_admin_contact', sa.String(length=128), nullable=True),

        sa.Column('digital_file_path', sa.String(length=512), nullable=True),
        sa.Column('github_repo_read_grant', sa.String(length=256), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )

    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='RUB'),
        sa.Column('payment_method', sa.Enum('CARD_RF','SBP_QR', name='payment_method'), nullable=False),
        sa.Column('status', sa.Enum('created', 'pending', 'paid', 'failed', 'canceled', name='order_status'), nullable=False, server_default='created'),
        sa.Column('fk_order_id', sa.String(length=64), nullable=True),
        sa.Column('fk_payment_url', sa.String(length=1024), nullable=True),
        sa.Column('buyer_tg_id', sa.String(length=64), nullable=True),
    )

    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('delivery_info', sa.String(length=1024), nullable=True),
    )

    op.create_table(
        'item_codes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=512), nullable=False),
        sa.Column('is_sold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sold_order_id', sa.Integer(), nullable=True),
    )

    # files table удалена


def downgrade() -> None:
    op.drop_table('purchases')
    op.drop_table('orders')
    op.drop_table('items')
    op.drop_index('ix_users_tg_id', table_name='users')
    op.drop_table('users')

    order_status = postgresql.ENUM('created', 'pending', 'paid', 'failed', 'canceled', name='order_status')
    order_status.drop(op.get_bind(), checkfirst=True)

    item_type = postgresql.ENUM('service', 'digital', name='item_type')
    item_type.drop(op.get_bind(), checkfirst=True)
