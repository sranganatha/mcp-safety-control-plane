PYTHON ?= python

.PHONY: check demo test test-container

check:
	$(PYTHON) -m compileall -q mcp_control_plane tests
	$(PYTHON) -m mcp_control_plane.config config/demo.json

demo:
	$(PYTHON) -m mcp_control_plane.demo

test:
	$(PYTHON) -m unittest discover -s tests -v

test-container:
	podman build --tag mcp-safety-control-plane:test .
	podman run --rm mcp-safety-control-plane:test
