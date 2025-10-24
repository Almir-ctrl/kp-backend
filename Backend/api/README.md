OpenAPI contract and codegen notes

This folder contains `openapi.yaml` — a minimal OpenAPI 3.0.3 description of the
backend API used for frontend integration. The file is intentionally compact and
includes examples useful for generating client types.

Quick client generation (TypeScript)

- Using openapi-typescript (generates types only):

  npm install -g openapi-typescript
  openapi-typescript api/openapi.yaml --output src/types/api.d.ts

- Using OpenAPI Generator (full client):

  # install openapi-generator-cli (Java required)
  openapi-generator-cli generate -i api/openapi.yaml -g typescript-axios -o generated/ts-client

Notes
- The API includes a BearerAuth scheme in `components.securitySchemes`.
- For reproducible generation in CI, pin the generator version and run locally in a container.

Validation

Run the repo validation script to ensure the OpenAPI file is syntactically correct:

```powershell
python scripts/check_yaml.py
```

If you change `openapi.yaml`, run the validator and update client generation steps.
