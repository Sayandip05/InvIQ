"""add_org_id_to_transactions_and_requisitions

Revision ID: d3e4f5a6b789
Revises: c2d3e4f5g678
Create Date: 2026-10-18 23:55:00.000000

Hardens multi-tenant isolation on the two high-volume tables that previously
derived their tenant through item/location:

  * inventory_transactions.org_id  (NOT NULL, backfilled from items.org_id)
  * requisitions.org_id            (NOT NULL, backfilled from locations.org_id)
  * chat_sessions.org_id           (nullable audit scope, backfilled from users)
  * chat_sessions.user_id          (missing FK -> users.id)

Composite index on inventory_transactions is re-keyed so the tenant id leads:
  ix_inv_tx_loc_item_date (location_id, item_id, date)
    -> ix_inv_tx_org_loc_item_date (org_id, location_id, item_id, date)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b789'
down_revision: Union[str, None] = 'c2d3e4f5g678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ----------------------------------------------------------------------
    # 1. inventory_transactions.org_id
    # ----------------------------------------------------------------------
    op.add_column('inventory_transactions', sa.Column('org_id', sa.Integer(), nullable=True))

    # Backfill from the owning item (never invent an org).
    conn.execute(
        sa.text(
            "UPDATE inventory_transactions it SET org_id = i.org_id "
            "FROM items i WHERE it.item_id = i.id AND it.org_id IS NULL"
        )
    )
    orphans = conn.execute(
        sa.text("SELECT COUNT(*) FROM inventory_transactions WHERE org_id IS NULL")
    ).scalar()
    if orphans and orphans > 0:
        raise RuntimeError(
            f"Multi-tenant migration halted: {orphans} inventory_transaction row(s) could not be "
            "linked to an item's organization. Resolve or quarantine them before applying NOT NULL."
        )

    op.alter_column(
        'inventory_transactions', 'org_id', existing_type=sa.Integer(), nullable=False
    )
    op.create_foreign_key(
        'fk_inventory_transactions_org_id',
        'inventory_transactions',
        'organizations',
        ['org_id'],
        ['id'],
    )
    # Re-key the composite index so tenant filtering is index-supported.
    op.drop_index('ix_inv_tx_loc_item_date', table_name='inventory_transactions')
    op.create_index(
        'ix_inv_tx_org_loc_item_date',
        'inventory_transactions',
        ['org_id', 'location_id', 'item_id', 'date'],
        unique=False,
    )

    # ----------------------------------------------------------------------
    # 2. requisitions.org_id
    # ----------------------------------------------------------------------
    op.add_column('requisitions', sa.Column('org_id', sa.Integer(), nullable=True))

    conn.execute(
        sa.text(
            "UPDATE requisitions r SET org_id = l.org_id "
            "FROM locations l WHERE r.location_id = l.id AND r.org_id IS NULL"
        )
    )
    orphans = conn.execute(
        sa.text("SELECT COUNT(*) FROM requisitions WHERE org_id IS NULL")
    ).scalar()
    if orphans and orphans > 0:
        raise RuntimeError(
            f"Multi-tenant migration halted: {orphans} requisition row(s) could not be linked to a "
            "location's organization. Resolve or quarantine them before applying NOT NULL."
        )

    op.alter_column('requisitions', 'org_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        'fk_requisitions_org_id', 'requisitions', 'organizations', ['org_id'], ['id']
    )
    op.create_index(
        'ix_requisitions_org_status', 'requisitions', ['org_id', 'status'], unique=False
    )

    # ----------------------------------------------------------------------
    # 3. chat_sessions — optional audit scope + missing FK on user_id
    # ----------------------------------------------------------------------
    op.add_column('chat_sessions', sa.Column('org_id', sa.Integer(), nullable=True))
    conn.execute(
        sa.text(
            "UPDATE chat_sessions c SET org_id = u.org_id "
            "FROM users u WHERE c.user_id = u.id AND c.org_id IS NULL"
        )
    )
    op.create_index('ix_chat_sessions_org_id', 'chat_sessions', ['org_id'], unique=False)

    # Only add the FK if no chat session references a non-existent user.
    orphan_users = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM chat_sessions c "
            "LEFT JOIN users u ON c.user_id = u.id WHERE u.id IS NULL"
        )
    ).scalar()
    if not orphan_users:
        op.create_foreign_key(
            'fk_chat_sessions_user_id', 'chat_sessions', 'users', ['user_id'], ['id']
        )


def downgrade() -> None:
    # chat_sessions
    op.drop_constraint('fk_chat_sessions_user_id', 'chat_sessions', type_='foreignkey')
    op.drop_index('ix_chat_sessions_org_id', table_name='chat_sessions')
    op.drop_column('chat_sessions', 'org_id')

    # requisitions
    op.drop_constraint('fk_requisitions_org_id', 'requisitions', type_='foreignkey')
    op.drop_index('ix_requisitions_org_status', table_name='requisitions')
    op.drop_column('requisitions', 'org_id')

    # inventory_transactions
    op.drop_constraint('fk_inventory_transactions_org_id', 'inventory_transactions', type_='foreignkey')
    op.drop_index('ix_inv_tx_org_loc_item_date', table_name='inventory_transactions')
    op.create_index(
        'ix_inv_tx_loc_item_date',
        'inventory_transactions',
        ['location_id', 'item_id', 'date'],
        unique=False,
    )
    op.drop_column('inventory_transactions', 'org_id')
