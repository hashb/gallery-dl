# -*- coding: utf-8 -*-

# Copyright 2015-2021 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Downloader modules"""

import shutil
from .. import config

modules = [
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
    if scheme == "https":
        scheme = "http"

    if scheme == "http" and _aria2c_available():
        from . import aria2c
        cls = aria2c.__downloader__
    elif scheme in modules:  # prevent unwanted imports
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


def _aria2c_available():
    """Return True if aria2c is enabled and its executable can be found"""
    if not config.get(("downloader", "aria2c"), "enabled", True):
        return False
    path = config.get(("downloader", "aria2c"), "path", "aria2c")
    return shutil.which(path) is not None


# --------------------------------------------------------------------
# internals

_cache = {}
