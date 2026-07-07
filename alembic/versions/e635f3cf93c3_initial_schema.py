"""initial schema

Revision ID: e635f3cf93c3
Revises: 6082cd13e6b3
Create Date: 2026-07-07 17:06:26.726106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e635f3cf93c3'
down_revision: Union[str, None] = '6082cd13e6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
