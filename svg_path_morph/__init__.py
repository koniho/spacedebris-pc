"""Small, dependency-free SVG path interpolation utility."""

from .morph import CompiledPaths, compile, morph

__all__ = ["compile", "morph", "CompiledPaths"]
