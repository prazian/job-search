PYTHON := python3
TODAY := $(shell date +%Y-%m-%d)

.PHONY: help hn hn-json oss oss-json scan tracker clean

help:
	@echo "Job search playbook, available commands:"
	@echo ""
	@echo "  make hn         Scan HN's hiring + freelancer threads, opens scan-results/hn-scan-$(TODAY).md"
	@echo "  make hn-json    Same scan, machine-readable JSON to stdout, no file written"
	@echo "  make oss        Check OSS target repos for open help-wanted work (~2 min, rate-limited), opens scan-results/oss-scan-$(TODAY).md"
	@echo "  make oss-json   Same scan, machine-readable JSON to stdout, no file written"
	@echo "  make scan       Run hn then oss back to back"
	@echo "  make tracker    Open tracker.csv in the default app"
	@echo "  make clean      Remove __pycache__ and other build junk (keeps scan-results/, that's your history)"
	@echo ""
	@echo "Applied somewhere? Just open the report and tick its checkbox, [ ] to [x], then save. Next scan reads it back."

hn:
	$(PYTHON) scripts/hn_scan.py
	open scan-results/hn-scan-$(TODAY).md

hn-json:
	$(PYTHON) scripts/hn_scan.py --json

oss:
	$(PYTHON) scripts/oss_scan.py
	open scan-results/oss-scan-$(TODAY).md

oss-json:
	$(PYTHON) scripts/oss_scan.py --json

scan: hn oss

tracker:
	open tracker.csv

clean:
	rm -rf scripts/__pycache__ scripts/*.pyc
