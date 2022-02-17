import json

import requests
from flask.cli import AppGroup
from sqlalchemy import and_, select

from application.models import (
    Collection,
    Dataset,
    Endpoint,
    Organisation,
    Pipeline,
    Resource,
    Source,
    Typology,
    resource_endpoint,
    source_pipeline,
)

management_cli = AppGroup("manage")

digital_land_datasette = "https://datasette.digital-land.info/digital-land"

model_classes = {
    "organisation": Organisation,
    "source": Source,
    "endpoint": Endpoint,
    "typology": Typology,
    "collection": Collection,
    "dataset": Dataset,
    "resource": Resource,
    "resource_endpoint": resource_endpoint,
    "pipeline": Pipeline,
    "source_pipeline": source_pipeline,
}


ordered_tables = [
    "organisation",
    "typology",
    "collection",
    "dataset",
    "endpoint",
    "source",
    "resource",
    "resource_endpoint",
    "pipeline",
    "source_pipeline",
]


@management_cli.command("load-data")
def load_data():

    for table in ordered_tables:
        url = f"{digital_land_datasette}/{table}.json"
        print(f"loading from {url}")

        has_next = True
        while has_next:
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()

            if data.get("next") is None:
                has_next = False

            columns = data["columns"]
            table = data["table"]
            rows = data["rows"]

            _load_data(columns, table, rows)
            url = data.get("next_url")
            if url is None:
                has_next = False


@management_cli.command("drop-data")
def drop_data():
    from application.extensions import db

    for table in reversed(ordered_tables):

        model_class = model_classes.get(table)
        if model_class is not None:
            db.session.query(model_class).delete()
            db.session.commit()


def _load_data(columns, table, rows):

    from application.extensions import db

    model_class = model_classes.get(table)

    if model_class is None:
        raise Exception(f"Can't load data for {table}")

    inserts = []
    for row in rows:
        r = [None if not item else item for item in row]
        inserts.append(dict(zip(columns, r)))

    if table == "dataset":
        for insert in inserts:
            if "paint_options" in insert:
                insert["paint_options"] = (
                    json.loads(insert["paint_options"])
                    if insert["paint_options"]
                    else None
                )

    if table == "resource_endpoint" or table == "source_pipeline":
        for insert in inserts:
            del insert["rowid"]

    for i in inserts:

        if table == "resource_endpoint":
            ins = model_class.insert().values(**i)
            conn = db.engine.connect()
            s = select(model_class).where(
                and_(
                    model_class.c.resource == i["resource"],
                    model_class.c.endpoint == i["endpoint"],
                )
            )
            result = conn.execute(s).fetchone()
            if not result:
                conn.execute(ins)
            else:
                print(f"{i} already in db")

        elif table == "source_pipeline":
            ins = model_class.insert().values(**i)
            conn = db.engine.connect()
            s = select(model_class).where(
                and_(
                    model_class.c.source == i["source"],
                    model_class.c.pipeline == i["pipeline"],
                )
            )
            result = conn.execute(s).fetchone()
            if not result:
                conn.execute(ins)
            else:
                print(f"{i} already in db")

        else:
            try:
                if table == "source":
                    endpoint_id = i.pop("endpoint")
                    if endpoint_id is not None:
                        endpoint = Endpoint.query.get(endpoint_id)
                        i["endpoint"] = endpoint
                    organisation_id = i.pop("organisation")
                    if organisation_id is not None:
                        organisation = Organisation.query.get(organisation_id)
                        i["organisation"] = organisation

                obj = model_class(**i)
                db.session.add(obj)
                db.session.commit()

            except Exception as e:
                print(f"error loading {obj}")
                print(e)
