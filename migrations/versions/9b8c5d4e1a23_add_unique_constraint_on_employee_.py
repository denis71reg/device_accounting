"""add unique constraint on employee telegram

Revision ID: 9b8c5d4e1a23
Revises: e603891f1e0e
Create Date: 2025-11-27 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b8c5d4e1a23'
down_revision = 'e603891f1e0e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_employees_telegram', ['telegram'])


def downgrade():
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.drop_constraint('uq_employees_telegram', type_='unique')


