# For MCP directories that start the server in a container to list its tools.
# The key is passed at run time (docker run -e OKDATA_API_KEY=...), never baked into the image.
FROM python:3.12-slim
WORKDIR /app
COPY server.py .
USER nobody
ENTRYPOINT ["python", "server.py"]
