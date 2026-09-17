"""Drop redundant analytics_events indexes.

ix_analytics_events_created_at is a left-prefix of ix_analytics_events_created_action
and ix_analytics_events_action_name is a left-prefix of
ix_analytics_events_action_name_created_at, so both are redundant and only add
write overhead on the hottest insert table.

Revision ID: 20260726_000010
Revises: 20260722_000009
Create Date: 2026-07-26 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260726_000010"
down_revision: Union[str, Sequence[str], None] = "20260722_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REDUNDANT_INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    ("ix_analytics_events_created_at", "analytics_events", ["created_at"]),
    ("ix_analytics_events_action_name", "analytics_events", ["action_name"]),
)


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {index["name"] for index in inspector.get_indexes(table_name)}
    return index_name in index_names


def upgrade() -> None:
    for index_name, table_name, _columns in REDUNDANT_INDEXES:
        if _has_index(table_name, index_name):
            op.drop_index(index_name, table_name=table_name)


def downgrade() -> None:
    for index_name, table_name, columns in reversed(REDUNDANT_INDEXES):
        if not _has_index(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)
