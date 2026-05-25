from alembic import op
import sqlalchemy as sa

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scraper_worker",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("running", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_heartbeat_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_started_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_stopped_utc", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("INSERT INTO scraper_worker (id, running) VALUES ('main', false)")


def downgrade() -> None:
    op.drop_table("scraper_worker")
