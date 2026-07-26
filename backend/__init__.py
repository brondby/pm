"""Backend package marker for relative imports in tests.
This file enables the test suite to import ``backend.main`` using a
relative import (``from ..main import app``) without raising an ImportError.
"""
