"""Pierwsza migracja: tabela `bots` (schemat pod dane jak w data/bots/bots.json).

Po co migracja (krok D):
  Zamiast ręcznie wpisywać SQL w Neonie, opisujesz strukturę w tym pliku i
  wersjonujesz ją w Gicie. Ten plik to tylko PRZEPIS — baza zmienia się dopiero
  po: alembic upgrade head (krok E).

Jak to działa:
  - revision / down_revision: łańcuch wersji dla Alembica.
  - upgrade(): co wykonać przy upgrade (tu: CREATE TABLE).
  - downgrade(): jak cofnąć (tu: DROP TABLE).
  Alembic trzyma na serwerze tabelę alembic_version, żeby wiedzieć, które
  migracje już zostały zastosowane.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="mixed"),
        sa.Column(
            "urls_olx",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "urls_vinted",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("history_file", sa.String(512), nullable=True),
        sa.Column(
            "created_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("bots")
