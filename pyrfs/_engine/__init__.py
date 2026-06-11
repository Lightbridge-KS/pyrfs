"""pyrfs engine — the single implementation behind all three surfaces.

Invariant: nothing under ``pyrfs._engine`` (nor ``pyrfs.values`` /
``pyrfs.display``) may import pandas. The optional ``pyrfs._pandas`` layer
depends inward on the engine, never the reverse.
"""
