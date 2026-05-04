"""
Shared Flask extensions — import here, init_app() in main.py.
Keeping extensions in one place avoids circular imports between blueprints and main.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# memory:// is fine for a single-worker deployment (Render default).
# Swap to redis:// via RATELIMIT_STORAGE_URI env var for multi-worker setups.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[],  # no global default — limits are applied per-route
)
