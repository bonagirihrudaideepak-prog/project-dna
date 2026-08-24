import os

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://projectdna:projectdna@127.0.0.1:5434/projectdna"
)
os.environ["FIXTURE_ROOT"] = os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures")
os.environ["SECRET_KEY"] = "test-secret-development-only"
os.environ["ENV"] = "test"
