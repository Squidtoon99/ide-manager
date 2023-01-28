"""add featured teacher

Revision ID: 916546b5e91e
Revises: e5189cf67189
Create Date: 2023-01-22 19:40:49.495580

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '916546b5e91e'
down_revision = 'e5189cf67189'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('featured_teacher_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(None, 'users', ['featured_teacher_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('featured_teacher_id')

    # ### end Alembic commands ###
