"""Add password reset tokens."""

import sqlalchemy as sa
from alembic import op

revision = "06ee814ba6d1"
down_revision = "238964ecd65a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "password_reset_tokens",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY")


def downgrade():
    op.drop_table("password_reset_tokens")
