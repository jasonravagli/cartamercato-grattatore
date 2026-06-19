.PHONY: all $(MAKECMDGOALS)

help: # print all the available targets
	@echo "\nAvailable targets:\n"
	@grep -E '^[a-zA-Z_-]+:.*?# .*$$' $(MAKEFILE_LIST) | sed 's/:.*#/\t/' | column -t -s '	' ; echo

init: # initialize the git local and remote repository
	python -m utils.initialize

venv: # create the uv environment
	uv venv .venv

install: # install requirements without development dependencies
	uv sync

dev: install-dev  # install requirements with all dependencies that are needed for development
	uv run pre-commit install

install-uv: # install uv tool
	curl -LsSf https://astral.sh/uv/install.sh | sh

install-dev: # install dev dependencies
	uv sync --all-groups

install-release: # install release dependencies
	uv sync --group release

install-test: # install test dependencies
	uv sync --group test

format: # format the code with the ruff tool
	uv run ruff format cartamercato_grattatore tests utils

format-check: # check the formatting code with ruff
	uv run ruff format --check cartamercato_grattatore tests utils

lint: # check the code style
	uv run ruff check cartamercato_grattatore tests utils

lint-fix: # check and fix the code style
	uv run ruff check --fix cartamercato_grattatore tests utils

test: # launch the tests
	uv run pytest -v --junitxml=tests_report.xml --doctest-modules --cov=cartamercato_grattatore --cov-report xml:coverage.xml --durations=0 tests

tree: # print the structure of the repository ignoring what is declared in .gitignore
	uv run python -m utils.tree

# Create a wheel (.whl file) inside dist directory
wheel: # create a wheel to distribute this software
	uv run python -m build --wheel


