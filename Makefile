PYTHON ?= .venv/bin/python
NODE_IMAGE ?= node:22-alpine
ADMIN_WEB_NODE_MODULES_VOLUME ?= cronolex-admin-web-node-modules-ci
CLIENT_WEB_NODE_MODULES_VOLUME ?= cronolex-client-web-node-modules-ci
ADMIN_WEB_COVERAGE_DIR ?= /tmp/cronolex-admin-coverage
CLIENT_WEB_COVERAGE_DIR ?= /tmp/cronolex-client-coverage

.PHONY: \
	admin_api_tests \
	admin_web_tests \
	backend_core_tests \
	backend_tests \
	check-python \
	client_api_tests \
	client_web_tests \
	ci_config_check \
	frontend_clean \
	frontend_tests \
	lint-python \
	telegram_flow_tests \
	test \
	test-python

lint-python:
	$(PYTHON) -m ruff check app tests word_base

test-python:
	$(PYTHON) -m pytest

check-python: lint-python test-python

ci_config_check:
	$(PYTHON) -c "from pathlib import Path; import yaml; yaml.safe_load(Path('.gitlab-ci.yml').read_text())"

admin_api_tests:
	$(PYTHON) -m pytest $$($(PYTHON) scripts/list_backend_tests.py admin_api)

client_api_tests:
	$(PYTHON) -m pytest $$($(PYTHON) scripts/list_backend_tests.py client_api)

telegram_flow_tests:
	$(PYTHON) -m pytest $$($(PYTHON) scripts/list_backend_tests.py telegram_flow)

backend_core_tests:
	$(PYTHON) -m pytest $$($(PYTHON) scripts/list_backend_tests.py backend_core)

backend_tests: lint-python test-python

admin_web_tests:
	docker run --rm -v "$(PWD):/work" -v $(ADMIN_WEB_NODE_MODULES_VOLUME):/work/admin_web/node_modules -w /work/admin_web $(NODE_IMAGE) sh -c 'npm ci && npm run lint && npm run typecheck && npm run test:coverage -- --coverage.reportsDirectory=$(ADMIN_WEB_COVERAGE_DIR)'

client_web_tests:
	docker run --rm -v "$(PWD):/work" -v $(CLIENT_WEB_NODE_MODULES_VOLUME):/work/client_web/node_modules -w /work/client_web $(NODE_IMAGE) sh -c 'npm ci && npm run lint && npm run typecheck && npm run test:coverage -- --coverage.reportsDirectory=$(CLIENT_WEB_COVERAGE_DIR)'

frontend_tests: admin_web_tests client_web_tests

frontend_clean:
	docker run --rm -v "$(PWD):/work" -w /work alpine:3.20 sh -c 'rm -rf admin_web/node_modules admin_web/coverage admin_web/dist client_web/node_modules client_web/coverage client_web/dist'

test: backend_tests frontend_tests
