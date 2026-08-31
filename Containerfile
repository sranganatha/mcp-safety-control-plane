FROM docker.io/library/python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir . \
    && python -m compileall -q mcp_control_plane tests
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
