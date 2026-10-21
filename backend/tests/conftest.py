import os
import tempfile

# Antes de importar la app: una base de datos temporal, una clave de prueba y sin avisar a n8n
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["API_KEY"] = "test"
os.environ["N8N_WEBHOOK_URL"] = ""
os.environ["SEED"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture
def cliente():
    """Un cliente que ya envía la clave de la API, como hace n8n."""
    return TestClient(app, headers={"X-API-Key": "test"})


@pytest.fixture
def anonimo():
    return TestClient(app)
