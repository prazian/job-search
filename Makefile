PYTHON := python3

.PHONY: help hn hn-json oss oss-json scan tracker clean

help:
	@echo "Job search playbook, available commands:"
	@echo ""
	@echo "  make hn         Scan HN's current hiring + freelancer threads for fresh leads"
	@echo "  make hn-json    Same, machine-readable JSON output"
	@echo "  make oss        Check the OSS target repos for open help-wanted work (~2 min, rate-limited)"
	@echo "  make oss-json   Same, machine-readable JSON output"
	@echo "  make scan       Run hn then oss back to back"
	@echo "  make tracker    Open tracker.csv in the default app"
	@echo "  make clean      Remove __pycache__ and other build junk"

hn:
	$(PYTHON) scripts/hn_scan.py

hn-json:
	$(PYTHON) scripts/hn_scan.py --json

oss:
	$(PYTHON) scripts/oss_scan.py

oss-json:
	$(PYTHON) scripts/oss_scan.py --json

scan: hn oss

tracker:
	open tracker.csv

clean:
	rm -rf scripts/__pycache__ scripts/*.pyc
