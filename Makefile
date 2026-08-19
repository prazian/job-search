PYTHON := python3
TODAY := $(shell date +%Y-%m-%d)

.PHONY: help hn hn-force hn-json oss oss-force oss-json remotive remotive-force remotive-json scan tracker clean

help:
	@echo "Job search playbook, available commands:"
	@echo ""
	@echo "  make hn              Scan HN's hiring + freelancer threads. If scan-results/hn-scan-$(TODAY).md"
	@echo "                       already exists, does nothing to it, your edits are safe."
	@echo "  make hn-force        Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make hn-json         Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make oss             Check OSS target repos for open help-wanted work (~2 min, rate-limited)."
	@echo "                       If scan-results/oss-scan-$(TODAY).md already exists, does nothing to it."
	@echo "  make oss-force       Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make oss-json        Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make remotive        Scan Remotive for contract/freelance leads (EMEA/APAC preferred, US-only auto-skipped)."
	@echo "                       If scan-results/remotive-scan-$(TODAY).md already exists, does nothing to it."
	@echo "  make remotive-force  Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make remotive-json   Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make scan            Run hn, oss, and remotive back to back"
	@echo "  make tracker         Open tracker.csv in the default app"
	@echo "  make clean           Remove __pycache__ and other build junk (keeps scan-results/, that's your history)"
	@echo ""
	@echo "Applied somewhere? Just open the report and tick its checkbox, [ ] to [x], then save. It's never re-parsed until a new day's file is created."
	@echo "Any scan's fetch fails partway (rate limit, network), the whole run aborts and writes nothing, exit code 1, so nothing broken gets persisted."

hn:
	$(PYTHON) scripts/hn_scan.py

hn-force:
	$(PYTHON) scripts/hn_scan.py --force

hn-json:
	$(PYTHON) scripts/hn_scan.py --json

oss:
	$(PYTHON) scripts/oss_scan.py

oss-force:
	$(PYTHON) scripts/oss_scan.py --force

oss-json:
	$(PYTHON) scripts/oss_scan.py --json

remotive:
	$(PYTHON) scripts/remotive_scan.py

remotive-force:
	$(PYTHON) scripts/remotive_scan.py --force

remotive-json:
	$(PYTHON) scripts/remotive_scan.py --json

scan: hn oss remotive

tracker:
	open tracker.csv

clean:
	rm -rf scripts/__pycache__ scripts/*.pyc
