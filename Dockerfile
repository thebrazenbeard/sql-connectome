FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV SQL_CONNECTOME_PROCESS=rest

EXPOSE 8080 8001

CMD ["python", "-m", "sql_connectome.entrypoint"]
