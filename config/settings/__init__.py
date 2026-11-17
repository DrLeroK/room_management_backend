"""
Dynamic settings loader for StayCraft Backend.
Selects settings module based on DJANGO_ENV environment variable (default: development).
"""

import os

env_name = os.environ.get("DJANGO_ENV", "development").lower()

if env_name == "production":
    from .production import *
elif env_name == "testing":
    from .testing import *
else:
    from .development import *
