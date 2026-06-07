.PHONY: bootstrap test eval-smoke eval pycompile review-ready

PYTHON ?= python3
VENV ?= .venv
VENV_PY := $(VENV)/bin/python
PIP := $(VENV_PY) -m pip
RUN_PY ?= $(PYTHON)

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e ".[dev,agents,synth]"

test:
	$(RUN_PY) -m pytest -q

eval-smoke:
	$(RUN_PY) -m praxis_evals.run_local --case praxis_evals/cases/smoke.yaml

pycompile:
	$(RUN_PY) -m py_compile run.py praxis_gui.py $$(find src praxis_agents praxis_evals scripts tests -name '*.py' -print)

eval: pycompile test eval-smoke

review-ready: pycompile test
	$(RUN_PY) scripts/reproduce_review_package.py --max-cases-per-condition 1 --skip-checks
