"""initial schema

Revision ID: 6082cd13e6b3
Revises: f95b4c67e645
Create Date: 2026-07-07 15:48:01.260931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6082cd13e6b3'
down_revision: Union[str, None] = 'f95b4c67e645'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
