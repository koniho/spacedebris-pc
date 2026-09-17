"""
SVG Path Morph - A Python library for morphing between SVG paths.

This is a Python port of the svg-path-morph JavaScript library.
https://github.com/Minibrams/svg-path-morph
"""

from .morph import compile, morph, CompiledPaths

__all__ = ["compile", "morph", "CompiledPaths"]
__version__ = "0.1.0"
