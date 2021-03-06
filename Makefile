init::
	python -m pip install --upgrade pip
	python -m pip install pip-tools
	python -m piptools sync requirements/requirements.txt requirements/dev-requirements.txt
	python -m pre_commit install
	npm install

black:
	black .

black-check:
	black --check .

flake8:
	flake8 .

isort:
	isort --profile black .

lint: black-check flake8

run::
	flask run

watch:
	npm run watch

upgrade-db:
	flask db upgrade

downgrade-db:
	flask db downgrade

load-data:
	flask manage load-data

load-test-data:
	flask manage load-data --test=true

drop-data:
	flask manage drop-data

test-functional:
	python -m playwright install chromium
	python -m pytest -p no:warnings tests/functional

test-visual:
	python -m playwright install chromium
	pytest tests/functional/test_application.py  --headed --slowmo 1000

test:
	python -m pytest --ignore=tests/functional
