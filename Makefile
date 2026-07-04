PYTHON = python3
PIP = pip3
MAIN = pac-man.py
CONFIG = config.json
WHL = mazegenerator-00001-py3-none-any.whl

.PHONY: install run debug clean lint lint-strict test build

install:
	$(PIP) install -r requirements.txt
	$(PIP) install ./$(WHL)

run:
	$(PYTHON) $(MAIN) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true

lint:
	flake8 .
	mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

test:
	pytest tests/ -v

build:
	pyinstaller build.spec
