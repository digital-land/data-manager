import json
from datetime import datetime

import click
import requests
from flask.cli import AppGroup
from sqlalchemy import and_, select

from application.models import (
    Collection,
    Column,
    Concat,
    Dataset,
    Datatype,
    Default,
    Endpoint,
    Field,
    Organisation,
    Resource,
    Source,
    SourceCheck,
    Typology,
    dataset_field,
    resource_endpoint,
    source_dataset,
)

management_cli = AppGroup("manage")

digital_land_datasette = "https://datasette.digital-land.info/digital-land"
model_classes = {
    "organisation": Organisation,
    "typology": Typology,
    "collection": Collection,
    "dataset": Dataset,
    "endpoint": Endpoint,
    "source": Source,
    "resource": Resource,
    "resource_endpoint": resource_endpoint,
    "source_pipeline": source_dataset,
    "datatype": Datatype,
    "field": Field,
    "column": Column,
    "schema_field": dataset_field,
    "_default": Default,
    "concat": Concat,
}


ordered_tables = model_classes.keys()

foreign_key_columns = [
    "organisation",
    "endpoint",
    "collection",
    "resource",
    "datatype",
    "typology",
    "dataset",
    "field",
]

test_ordered_tables = ["organisation", "typology", "collection", "dataset"]


@management_cli.command("load-data")
@click.option("--test", default=False, help="Use test ordered tables or ordered tables")
def load_data(test):

    from application.extensions import db

    if Field.query.get("IGNORE") is None:
        ignore_field = Field(field="IGNORE")
        db.session.add(ignore_field)
        db.session.commit()

    tables = ordered_tables if not test else test_ordered_tables
    for table in tables:
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

    db.session.query(SourceCheck).delete()
    db.session.commit()

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

        if i.get("rowid", None) is not None:
            i["id"] = i.pop("rowid")

        entry_date = i.get("entry_date", None)
        if entry_date is not None:
            short_date = True
            try:
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                entry_datetime = datetime.strptime(entry_date, fmt)
                short_date = False
            except Exception as e:
                print(e)

            if short_date:
                try:
                    fmt = "%Y-%m-%d"
                    entry_datetime = datetime.strptime(entry_date, fmt)
                except Exception as e:
                    print(e)

            i["entry_date"] = entry_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

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
            # note source and destination table have different names
            i["dataset"] = i.pop("pipeline")
            ins = model_class.insert().values(**i)
            conn = db.engine.connect()
            s = select(model_class).where(
                and_(
                    model_class.c.source == i["source"],
                    model_class.c.dataset == i["dataset"],
                )
            )
            result = conn.execute(s).fetchone()
            if not result:
                conn.execute(ins)
            else:
                print(f"{i} already in db")
        elif table == "schema_field":
            # note source and destination table have different names
            i["dataset"] = i.pop("schema")
            i.pop("id")
            ins = model_class.insert().values(**i)
            conn = db.engine.connect()
            s = select(model_class).where(
                and_(
                    model_class.c.dataset == i["dataset"],
                    model_class.c.field == i["field"],
                )
            )
            result = conn.execute(s).fetchone()
            if not result:
                conn.execute(ins)
            else:
                print(f"{i} already in db")

        else:
            try:
                if table in ["source", "field", "column", "concat", "_default"]:
                    for fk_col in foreign_key_columns:
                        if table != fk_col:
                            key = i.pop(fk_col, None)
                            if key is not None:
                                one_to_many_class = model_classes[fk_col]
                                related_obj = one_to_many_class.query.get(key)
                                if related_obj is not None:
                                    i[fk_col] = related_obj

                if table in ["concat", "_default"]:
                    id = i["id"]
                else:
                    id = i[table]

                if id is not None:
                    if db.session.query(model_class).get(id) is None:
                        obj = model_class(**i)
                        db.session.add(obj)
                        db.session.commit()
                    else:
                        print(f"{table}: {i[table]} already loaded")
                else:
                    print(f"Record {i} does not have primary key value")

            except Exception as e:
                print(f"error loading {i}")
                print(e)
