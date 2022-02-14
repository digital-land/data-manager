"""initial migration

Revision ID: a5ca0f24dd45
Revises:
Create Date: 2022-02-14 16:55:29.099961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a5ca0f24dd45"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "endpoint",
        sa.Column("endpoint", sa.TEXT(), nullable=False),
        sa.Column("endpoint_url", sa.TEXT(), nullable=True),
        sa.Column("parameters", sa.TEXT(), nullable=True),
        sa.Column("plugin", sa.TEXT(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("endpoint"),
    )
    op.create_table(
        "organisation",
        sa.Column("organisation", sa.TEXT(), nullable=False),
        sa.Column("name", sa.TEXT(), nullable=True),
        sa.Column("official_name", sa.TEXT(), nullable=True),
        sa.Column("addressbase_custodian", sa.TEXT(), nullable=True),
        sa.Column("billing_authority", sa.TEXT(), nullable=True),
        sa.Column("census_area", sa.TEXT(), nullable=True),
        sa.Column("combined_authority", sa.TEXT(), nullable=True),
        sa.Column("company", sa.TEXT(), nullable=True),
        sa.Column("entity", sa.BIGINT(), nullable=True),
        sa.Column("esd_inventory", sa.TEXT(), nullable=True),
        sa.Column("local_authority_type", sa.TEXT(), nullable=True),
        sa.Column("local_resilience_forum", sa.TEXT(), nullable=True),
        sa.Column("opendatacommunities_area", sa.TEXT(), nullable=True),
        sa.Column("opendatacommunities_organisation", sa.TEXT(), nullable=True),
        sa.Column("region", sa.TEXT(), nullable=True),
        sa.Column("shielding_hub", sa.TEXT(), nullable=True),
        sa.Column("statistical_geography", sa.TEXT(), nullable=True),
        sa.Column("twitter", sa.TEXT(), nullable=True),
        sa.Column("website", sa.TEXT(), nullable=True),
        sa.Column("wikidata", sa.TEXT(), nullable=True),
        sa.Column("wikipedia", sa.TEXT(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("organisation"),
    )
    op.create_table(
        "source",
        sa.Column("source", sa.TEXT(), nullable=False),
        sa.Column("documentation_url", sa.TEXT(), nullable=True),
        sa.Column("attribution", sa.TEXT(), nullable=True),
        sa.Column("licence", sa.TEXT(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("endpoint", sa.TEXT(), nullable=True),
        sa.Column("organisation", sa.TEXT(), nullable=True),
        sa.Column("collection", sa.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(
            ["endpoint"],
            ["endpoint.endpoint"],
        ),
        sa.ForeignKeyConstraint(
            ["organisation"],
            ["organisation.organisation"],
        ),
        sa.PrimaryKeyConstraint("source"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("source")
    op.drop_table("organisation")
    op.drop_table("endpoint")
    # ### end Alembic commands ###