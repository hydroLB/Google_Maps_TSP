.PHONY: setup dev run demo build test lint format check bench bench-compare profile

setup:
	./scripts/bootstrap_venv.sh >/dev/null

run:
	./start

demo:
	./start --demo

dev:
	FASTEST_ROUTE_LIVE_RELOAD=1 ./start

build:
	./scripts/build.sh

test:
	./scripts/test.sh

lint:
	./scripts/lint.sh

format:
	./scripts/format.sh

check:
	./scripts/check.sh

bench:
	./scripts/bench.sh

bench-compare:
	./scripts/benchmark_compare.sh

profile:
	./scripts/bootstrap_venv.sh >/dev/null && PYTHONPATH=TSP_GOOGLE_MAPS ./.venv/bin/python scripts/profile_hot_paths.py
