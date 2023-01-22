"""some changes 2

Revision ID: a89ac583cd67
Revises: 815433af8fde
Create Date: 2023-01-21 22:50:58.346375

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a89ac583cd67'
down_revision = '815433af8fde'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('bucket', sa.String(length=255), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.drop_constraint('assignments_slug_key', type_='unique')
        batch_op.drop_column('slug')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.VARCHAR(length=100), autoincrement=False, nullable=False))
        batch_op.create_unique_constraint('assignments_slug_key', ['slug'])

    op.drop_table('file')
    # ### end Alembic commands ###
