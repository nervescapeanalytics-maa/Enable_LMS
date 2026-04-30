import os

_env = os.environ.get('DJANGO_ENV', 'production')

if _env == 'development':
    from .development import *  # noqa: F401,F403
elif _env == 'production':
    from .production import *  # noqa: F401,F403
else:
    from .base import *  # noqa: F401,F403
