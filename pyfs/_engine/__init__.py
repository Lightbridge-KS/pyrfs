"""pyfs engine — the single implementation behind all three surfaces.

Invariant: nothing under ``pyfs._engine`` (nor ``pyfs.values`` /
``pyfs.display``) may import pandas. The optional ``pyfs._pandas`` layer
depends inward on the engine, never the reverse.
"""
