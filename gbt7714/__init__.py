"""GB/T 7714-2015 reference formatting utilities.

Public API:
	- format_reference(entry)
	- parse_reference(raw)
	- data models in .models

__version__ is used by packaging / build scripts.
"""

__all__ = [
	'format_reference', 'parse_reference'
]

__version__ = '0.1.0'

from .models import *  # noqa: F401,F403
from .formatters import format_reference  # noqa: F401
from .parser import parse_reference  # noqa: F401
