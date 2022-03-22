import csv
import os
import tempfile
from collections import namedtuple
from itertools import islice

from digital_land.api import DigitalLandApi
from flask import Blueprint, abort, current_app, jsonify, request

from application.models import Organisation, Source
from application.utils import login_required

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/pipeline")

Workspace = namedtuple(
    "Workspace",
    [
        "collection_dir",
        "endpoint_csv",
        "pipeline_dir",
        "specification_dir",
        "resource_dir",
        "transformed_dir",
        "column_field_dir",
        "issue_dir",
        "dataset_resource_dir",
        "organisation_path",
    ],
)


@pipeline_bp.get("/<string:source>")
@login_required
def run(source):
    source_obj = Source.query.get(source)
    if source_obj is None:
        return abort(404)

    # TODO what happens in cases where more than one dataset? which name do we use? which fields?
    dataset_obj = source_obj.datasets[0]
    dataset = dataset_obj.dataset
    expected_fields = [field.field for field in dataset_obj.fields]

    with tempfile.TemporaryDirectory() as temp_dir:

        workspace = _setup_workspace(
            source_obj, dataset_obj, temp_dir, current_app.config["PROJECT_ROOT"]
        )
        api = DigitalLandApi(
            False, dataset, workspace.pipeline_dir, workspace.specification_dir
        )

        api.collect_cmd(workspace.endpoint_csv, workspace.collection_dir)

        resources = os.listdir(workspace.resource_dir)

        if not resources:
            print("No resource collected")
            return abort(400)
        else:
            resource_hash = resources[0]
            # convert - discard anything over 20 lines
            limit = int(request.args.get("limit")) if request.args.get("limit") else 10
            limit += 1  # for header row
            resource_fields, input_path, output_path = _convert_and_truncate_resource(
                api, workspace, resource_hash, limit
            )

            api.pipeline_cmd(
                input_path,
                output_path,
                workspace.collection_dir,
                None,
                workspace.issue_dir,
                workspace.organisation_path,
                column_field_dir=workspace.column_field_dir,
                dataset_resource_dir=workspace.dataset_resource_dir,
            )

            transformed = []
            with open(output_path) as file:
                reader = csv.DictReader(file)
                for row in reader:
                    transformed.append(row)

            issues = []
            issue_file = os.path.join(workspace.issue_dir, f"{resource_hash}.csv")
            with open(issue_file) as file:
                reader = csv.DictReader(file)
                for row in reader:
                    issues.append(row)

    return jsonify(
        {
            "transformed": transformed,
            "issues": issues,
            "resource_fields": resource_fields,
            "expected_fields": expected_fields,
        }
    )


def _setup_workspace(source, dataset, temp_dir, project_root_dir):

    pipeline_file_fields = {
        "column": ["dataset", "resource", "column", "field"],
        "concat": [
            "pipeline",
            "resource",
            "field",
            "fields",
            "separator",
            "entry-date",
            "start-date",
            "end-date",
        ],
        "convert": ["pipeline", "resource", "script"],
        "default": [
            "pipeline",
            "resource",
            "field",
            "default-field",
            "entry-date",
            "start-date",
            "end-date",
        ],
        "filter": ["dataset", "resource", "field", "pattern"],
        "lookup": ["prefix", "reference", "entity"],
        "patch": ["pipeline", "resource", "field", "pattern,value"],
        "skip": ["pipeline", "resource", "pattern"],
        "transform": ["pipeline", "field", "replacement-field"],
    }

    pipeline_dirs = [
        "transformed",
        "issue",
        "var/column-field",
        "var/dataset-resource",
    ]

    other_pipeline_files = {
        "column": dataset.columns,
        "concat": dataset.concats,
        "default": dataset.defaults,
    }

    collection_dir = os.path.join(temp_dir, "collection")
    if not os.path.exists(collection_dir):
        os.makedirs(collection_dir)

    endpoint_csv = os.path.join(collection_dir, "endpoint.csv")
    endpoint_data = source.endpoint.to_csv_dict()

    with open(endpoint_csv, "w") as csvfile:
        fieldnames = endpoint_data.keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(endpoint_data)

    source_csv = os.path.join(collection_dir, "source.csv")
    source_data = source.to_csv_dict()
    with open(source_csv, "w") as csvfile:
        fieldnames = source_data.keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(source_data)

    pipeline_dir = os.path.join(temp_dir, "pipeline")
    if not os.path.exists(pipeline_dir):
        os.makedirs(pipeline_dir)

    for directory in pipeline_dirs:
        d = os.path.join(temp_dir, directory)
        if not os.path.exists(d):
            os.makedirs(d)

    # TODO build from db data instead of fetch from github
    # for not create default empty files for those we don't
    # have in db yet
    for filename, fields in pipeline_file_fields.items():
        if filename not in other_pipeline_files.keys():
            file = os.path.join(pipeline_dir, f"{filename}.csv")
            with open(file, "w") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()

    for filename, collection in other_pipeline_files.items():
        file = os.path.join(pipeline_dir, f"{filename}.csv")
        rows = [item.to_csv_dict() for item in collection]
        if rows:
            fieldnames = rows[0].keys()
        else:
            fieldnames = pipeline_file_fields[filename]
        with open(file, "w") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

    transformed_dir = os.path.join(temp_dir, "transformed", dataset.dataset)
    if not os.path.exists(transformed_dir):
        os.makedirs(transformed_dir)

    specification_dir = os.path.join(project_root_dir, "specification")

    resource_dir = os.path.join(collection_dir, "resource")
    if not os.path.exists(resource_dir):
        os.makedirs(resource_dir)

    column_field_dir = os.path.join(temp_dir, "var/column-field", dataset.dataset)
    if not os.path.exists(column_field_dir):
        os.makedirs(column_field_dir)

    issue_dir = os.path.join(temp_dir, "issue", dataset.dataset)
    if not os.path.exists(issue_dir):
        os.makedirs(issue_dir)

    dataset_resource_dir = os.path.join(
        temp_dir, "var/dataset-resource", dataset.dataset
    )
    if not os.path.exists(dataset_resource_dir):
        os.makedirs(dataset_resource_dir)

    organisation_dir = os.path.join(
        temp_dir,
        "var/cache",
    )
    if not os.path.exists(organisation_dir):
        os.makedirs(organisation_dir)

    organisation_path = os.path.join(organisation_dir, "organisation.csv")

    organisations = [org.to_csv_dict() for org in Organisation.query.all()]
    with open(organisation_path, "w") as csvfile:
        fieldnames = organisations[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for org in organisations:
            writer.writerow(org)

    return Workspace(
        collection_dir=collection_dir,
        endpoint_csv=endpoint_csv,
        pipeline_dir=pipeline_dir,
        specification_dir=specification_dir,
        resource_dir=resource_dir,
        transformed_dir=transformed_dir,
        column_field_dir=column_field_dir,
        issue_dir=issue_dir,
        dataset_resource_dir=dataset_resource_dir,
        organisation_path=organisation_path,
    )


def _convert_and_truncate_resource(api, workspace, resource_hash, limit=10):
    input_path = os.path.join(workspace.resource_dir, resource_hash)
    output_path = os.path.join(workspace.resource_dir, f"{resource_hash}_converted.csv")

    api.convert_cmd(input_path, output_path)

    with open(output_path) as file:
        reader = csv.DictReader(file)
        resource_fields = reader.fieldnames
        truncated_resource_rows = list(islice(reader, limit))

    # overwrite resource with first n rows of converted data
    with open(input_path, "w") as file:
        writer = csv.DictWriter(file, fieldnames=resource_fields)
        writer.writeheader()
        for row in truncated_resource_rows:
            writer.writerow(row)

    output_path = os.path.join(workspace.transformed_dir, f"{resource_hash}.csv")
    return resource_fields, input_path, output_path