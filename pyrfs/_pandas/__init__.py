"""Optional pandas integration layer.

Imported by ``pyrfs/__init__`` inside a ``try/except ImportError`` — importing
this package registers the ExtensionDtypes (``bytes``/``perms``/``path``) and
the ``Series.fs`` accessor. Everything here depends inward on the engine and
the typed scalars; the engine never depends on this package.
"""

from pyrfs._pandas import accessor, arrays, dtypes, frames

__all__ = ["accessor", "arrays", "dtypes", "frames"]
