import json
from pathlib import Path

OPENAPI_JSON = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def test_committed_openapi_schema_is_up_to_date(app):
    # The frontend's generated types (src/types/openapi.ts) are built from this file.
    assert json.loads(OPENAPI_JSON.read_text(encoding="utf-8")) == app.openapi(), (
        "frontend/openapi.json is stale: run `python -m vms.cli openapi` then "
        "`npm run gen:api` in frontend/"
    )
