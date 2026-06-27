# import os
# import pytest
# from fastapi.testclient import TestClient
# from pathlib import Path

# # --------------------------------------------------
# # 1️⃣ Configure environment FIRST (before imports)
# # --------------------------------------------------

# @pytest.fixture(scope="session", autouse=True)
# def test_storage(tmp_path_factory):
#     tmp_dir = tmp_path_factory.mktemp("fs_data")
#     os.environ["FS_BASE_STORAGE"] = str(tmp_dir)
#     yield
#     os.environ.pop("FS_BASE_STORAGE", None)


# # --------------------------------------------------
# # 2️⃣ Import app AFTER env is ready
# # --------------------------------------------------

# @pytest.fixture(scope="session")
# def app():
#     import server  # ← delayed import
#     return server.app


# # --------------------------------------------------
# # 3️⃣ Client fixture
# # --------------------------------------------------

# @pytest.fixture
# def client(app):
#     return TestClient(app)
