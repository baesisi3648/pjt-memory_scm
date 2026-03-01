# @TASK RATE-LIMIT - IP-based rate limiting via slowapi
# @SPEC docs/planning/02-trd.md#rate-limiting

"""
Rate-limiting configuration using slowapi (Starlette-compatible wrapper around
limits/ratelimit).

Two limiters are exported:

  limiter        -- attached to the FastAPI app; provides the default
                    100 requests / minute / IP for every route that uses
                    @limiter.limit("100/minute").

  LOGIN_LIMIT    -- string constant used on the login endpoint to enforce a
                    stricter 5 requests / minute / IP anti-brute-force policy.

Usage in main.py
----------------
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.core.rate_limit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Usage on a route
----------------
    from app.core.rate_limit import limiter, DEFAULT_LIMIT, LOGIN_LIMIT

    @router.post("/login")
    @limiter.limit(LOGIN_LIMIT)
    def login(request: Request, ...):
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function: identify clients by their real IP address.
# get_remote_address reads X-Forwarded-For when present (reverse-proxy aware),
# falling back to the direct peer address.
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Human-readable limit strings used as decorator arguments.
DEFAULT_LIMIT: str = "100/minute"
LOGIN_LIMIT: str = "5/minute"
