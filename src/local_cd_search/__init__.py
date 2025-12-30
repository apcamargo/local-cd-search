"""
Package initializer for the local_cd_search package.

This module exposes commonly used submodules and convenience symbols
so callers can do:

    from local_cd_search import run_pipeline, prepare_databases, parse_rpsbproc, console

The pipeline functionality was split into separate `download` and `annotate`
modules; this initializer re-exports the commonly used helpers for convenience.
"""

from . import annotate, download, logger, main, parser
from .annotate import run_pipeline
from .download import prepare_databases
from .logger import console, set_quiet
from .parser import parse_rpsbproc

__all__ = [
    "main",
    "parser",
    "download",
    "annotate",
    "logger",
    "prepare_databases",
    "run_pipeline",
    "parse_rpsbproc",
    "console",
    "set_quiet",
]
