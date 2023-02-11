"""removing useless unit field

Revision ID: 94666c3b3245
Revises: f2579f82ee46
Create Date: 2023-02-09 22:34:43.730510

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '94666c3b3245'
down_revision = 'f2579f82ee46'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('units', schema=None) as batch_op:
        batch_op.drop_constraint('units_school_id_fkey', type_='foreignkey')
        batch_op.drop_column('school_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('units', schema=None) as batch_op:
        batch_op.add_column(sa.Column('school_id', sa.INTEGER(), autoincrement=False, nullable=True))
        batch_op.create_foreign_key('units_school_id_fkey', 'schools', ['school_id'], ['id'])

    # ### end Alembic commands ###