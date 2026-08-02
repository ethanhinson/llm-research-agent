.PHONY: test install lint

install:
	pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m py_compile agent/**/*.py cli.py
