# Integrators — OpenAPI and generated clients

AegisAI exposes **OpenAPI 3** automatically:

- **Interactive docs:** `/docs` (Swagger UI) and `/redoc`
- **Raw schema:** `/openapi.json` (same host as the API)

## Generate a Python client

From the repo root, with the API running (or use a saved `openapi.json`):

```bash
pip install openapi-generator-cli
# or: docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
#   -i http://127.0.0.1:8000/openapi.json -g python -o /local/out/python-client
```

With the **openapi-generator** CLI:

```bash
openapi-generator-cli generate \
  -i http://127.0.0.1:8000/openapi.json \
  -g python \
  -o ./build/aegisai-client --additional-properties=packageName=aegisai_client
```

Replace the URL with a file path if you export `openapi.json` from a deployment.

## Generate a TypeScript / fetch client

```bash
openapi-generator-cli generate \
  -i http://127.0.0.1:8000/openapi.json \
  -g typescript-fetch \
  -o ./build/aegisai-ts-client
```

## HTTP examples

See [`examples/http/smoke.http`](../../examples/http/smoke.http) for copy-paste requests (REST Client / Bruno-style).

## Authentication

When `AEGISAI_API_KEY` is set, send either:

- `Authorization: Bearer <key>`, or
- `X-API-Key: <key>`

Paths `/health`, `/live`, `/ready`, `/version`, `/metrics`, and OpenAPI UIs stay unauthenticated (see middleware).

## Redis (multi-replica)

Install `aegisai[redis]` and set `AEGISAI_REDIS_URL` so **Idempotency-Key** mappings and **optional rate limits** are consistent across replicas. See the main `README.md` configuration table.
