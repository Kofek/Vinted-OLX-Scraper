from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_runtime",
        sa.Column("bot_id",sa.String(64), sa.ForeignKey("bots.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("last_heartbeat_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_started_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stopped_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("success_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )

def downgrade() -> None:
    op.drop_table("bot_runtime")