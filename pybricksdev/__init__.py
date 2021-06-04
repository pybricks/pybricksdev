# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

from importlib.metadata import version

try:
    __version__ = version(__name__)
except Exception:  # pragma: no cover
    pass

del version
