"""Merge migration heads

Revision ID: 77dfa962f8bb
Revises: fa59fa0aa19d, b3c3da2079c0
Create Date: 2025-05-22 14:53:51.246233

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77dfa962f8bb'
down_revision = ('fa59fa0aa19d', 'b3c3da2079c0')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
