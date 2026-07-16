"""Enable the pgvector extension.

Revision ID: 46feab49b164
Revises:
Create Date: 2026-07-16 18:28:19.995512

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46feab49b164"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pgvector."""
    op.execute("CREATE EXTENSION vector")


def downgrade() -> None:
    """Disable pgvector."""
    op.execute("DROP EXTENSION vector")
