"""add endpoint and org properties to source

Revision ID: 7ed1870dd261
Revises: d09ee6215f13
Create Date: 2022-02-16 14:46:22.763855

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7ed1870dd261"
down_revision = "d09ee6215f13"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("source", "endpoint", new_column_name="_endpoint")
    op.alter_column("source", "organisation", new_column_name="_organisation")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("source", "_endpoint", new_column_name="endpoint")
    op.alter_column("source", "_organisation", new_column_name="organisation")
    # ### end Alembic commands ###
