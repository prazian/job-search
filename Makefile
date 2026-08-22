PYTHON := python3
TODAY := $(shell date +%Y-%m-%d)

.PHONY: help hn hn-force hn-json oss oss-force oss-json remotive remotive-force remotive-json himalayas himalayas-force himalayas-json djinni djinni-force djinni-json companies companies-force companies-json jobicy jobicy-force jobicy-json scan tracker clean

help:
	@echo "Job search playbook, available commands:"
	@echo ""
	@echo "  make hn                Scan HN's hiring + freelancer threads. If scan-results/$(TODAY)/hn-scan.md"
	@echo "                         already exists, does nothing to it, your edits are safe."
	@echo "  make hn-force          Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make hn-json           Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make oss               Check OSS target repos for open help-wanted work (~2 min, rate-limited, shows progress)."
	@echo "                         If scan-results/$(TODAY)/oss-scan.md already exists, does nothing to it."
	@echo "  make oss-force         Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make oss-json          Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make remotive          Scan Remotive for contract/freelance leads (EMEA/APAC preferred, US-only auto-skipped,"
	@echo "                         English-only). If scan-results/$(TODAY)/remotive-scan.md already exists, does nothing."
	@echo "  make remotive-force    Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make remotive-json     Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make himalayas         Crawl Himalayas (full-time + contract, ~500 pages/~10k jobs sampled, several"
	@echo "                         minutes, shows a progress bar, English-only). If scan-results/$(TODAY)/himalayas-scan.md"
	@echo "                         already exists, does nothing to it. Use HIMALAYAS_PAGES=N for a deeper crawl."
	@echo "  make himalayas-force   Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make himalayas-json    Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make djinni            Scan Djinni (Ukraine/CIS/Eastern Europe tech board, English-only, no other-language-"
	@echo "                         required listings). If scan-results/$(TODAY)/djinni-scan.md already exists, does nothing."
	@echo "  make djinni-force      Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make djinni-json       Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make companies         Check big Europe/Armenia/Georgia/Cyprus tech employers' own job boards (Greenhouse +"
	@echo "                         Sigma Software), region-filtered, no Denmark. One flaky company doesn't kill the run."
	@echo "  make companies-force   Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make companies-json    Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make jobicy            Scan Jobicy's remote-jobs API (region-tagged per listing, no free-text guessing,"
	@echo "                         100 results max, region-filtered, no Denmark). Quick, one API call."
	@echo "  make jobicy-force      Same scan, but rescans and merges fresh data into today's file even if it exists"
	@echo "  make jobicy-json       Same scan, machine-readable JSON to stdout, no file written or checked"
	@echo "  make scan              Run hn, oss, remotive, himalayas, djinni, companies, and jobicy back to back"
	@echo "  make tracker           Open tracker.csv in the default app"
	@echo "  make clean             Remove __pycache__ and other build junk (keeps scan-results/, that's your history)"
	@echo ""
	@echo "Each day's reports live together in scan-results/YYYY-MM-DD/, sorted naturally, newest folder is always the last one alphabetically."
	@echo "Applied somewhere? Just open the report and tick its checkbox, [ ] to [x], then save. It's never re-parsed until a new day's file is created."
	@echo "Any scan's fetch fails partway (rate limit, network), the whole run aborts and writes nothing, exit code 1, so nothing broken gets persisted."
	@echo "All sources (except hn.ycombinator.com, which is English by nature) filter out non-English listings and listings requiring a language other than English."

HIMALAYAS_PAGES ?= 500

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

himalayas:
	$(PYTHON) scripts/himalayas_scan.py --pages $(HIMALAYAS_PAGES)

himalayas-force:
	$(PYTHON) scripts/himalayas_scan.py --pages $(HIMALAYAS_PAGES) --force

himalayas-json:
	$(PYTHON) scripts/himalayas_scan.py --pages $(HIMALAYAS_PAGES) --json

djinni:
	$(PYTHON) scripts/djinni_scan.py

djinni-force:
	$(PYTHON) scripts/djinni_scan.py --force

djinni-json:
	$(PYTHON) scripts/djinni_scan.py --json

companies:
	$(PYTHON) scripts/company_scan.py

companies-force:
	$(PYTHON) scripts/company_scan.py --force

companies-json:
	$(PYTHON) scripts/company_scan.py --json

jobicy:
	$(PYTHON) scripts/jobicy_scan.py

jobicy-force:
	$(PYTHON) scripts/jobicy_scan.py --force

jobicy-json:
	$(PYTHON) scripts/jobicy_scan.py --json

scan: hn oss remotive himalayas djinni companies jobicy

tracker:
	open tracker.csv

clean:
	rm -rf scripts/__pycache__ scripts/*.pyc
