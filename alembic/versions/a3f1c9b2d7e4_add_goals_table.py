"""add goals table

Revision ID: a3f1c9b2d7e4
Revises: f95b4c67e645
Create Date: 2026-07-08 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9b2d7e4'
down_revision: Union[str, None] = 'f95b4c67e645'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'goals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('student_id', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_goals_student_id'), 'goals', ['student_id'], unique=False)

    op.add_column('interventions', sa.Column('goal_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_interventions_goal_id'), 'interventions', ['goal_id'], unique=False)
    op.create_foreign_key(
        'fk_interventions_goal_id_goals', 'interventions', 'goals', ['goal_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_interventions_goal_id_goals', 'interventions', type_='foreignkey')
    op.drop_index(op.f('ix_interventions_goal_id'), table_name='interventions')
    op.drop_column('interventions', 'goal_id')

    op.drop_index(op.f('ix_goals_student_id'), table_name='goals')
    op.drop_table('goals')
