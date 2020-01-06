"""Add start time to Repository object

Revision ID: d95efca6f334
Revises: 
Create Date: 2020-01-06 16:24:08.055349

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd95efca6f334'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('repositories', sa.Column('start_time', sa.DateTime(), nullable=True))
    op.add_column('repositories', sa.Column('start_time_utc_offset', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('repositories', 'start_time_utc_offset')
    op.drop_column('repositories', 'start_time')
