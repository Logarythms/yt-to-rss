from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance - shared across the application
limiter = Limiter(key_func=get_remote_address)
