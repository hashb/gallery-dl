# -*- coding: utf-8 -*-

# Copyright 2015-2021 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Downloader modules"""

import importlib
import subprocess


modules = [
    "aria2c",  # Make aria2c first in the list
    "http",
    "text",
    "ytdl",
]


def find(scheme):
    """Return downloader class suitable for handling the given scheme"""
    try:
        return _cache[scheme]
    except KeyError:
        pass

    cls = None
    # Try aria2c first if available
    try:
        module = importlib.import_module(".aria2c", __package__)
        cls = module.__downloader__
        _cache["http"] = _cache["https"] = cls  # Register aria2c for http(s)
        return cls
    except (ImportError, AttributeError, subprocess.SubprocessError):
        _log.debug("aria2c not available, falling back to default downloaders")

    if scheme == "https":
        scheme = "http"
    if scheme in modules:  # prevent unwanted imports
        try:
            module = __import__(scheme, globals(), None, None, 1)
        except ImportError:
            pass
        else:
            cls = module.__downloader__

    if scheme == "http":
        _cache["http"] = _cache["https"] = cls
    else:
        _cache[scheme] = cls
    return cls


# --------------------------------------------------------------------
# internals

_cache = {}
_log = logging.getLogger("downloader")
