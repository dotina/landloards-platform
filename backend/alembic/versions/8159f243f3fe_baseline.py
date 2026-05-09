"""baseline

Revision ID: 8159f243f3fe
Revises:
Create Date: 2026-05-09 11:09:07.364242

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "8159f243f3fe"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
