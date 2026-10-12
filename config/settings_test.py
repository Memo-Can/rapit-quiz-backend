import os

os.environ["DEBUG"] = "True"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite://:memory:")

from .settings import *  # noqa: E402,F401,F403

THROTTLE_SESSION_START = "1000/min"
THROTTLE_SCORE_SUBMIT = "1000/min"
