from __future__ import annotations

import sysconfig

from setuptools import setup

# Windows builds leave Py_DEBUG unset; set a default to avoid setuptools warnings.
config_vars = sysconfig.get_config_vars()
config_vars.setdefault("Py_DEBUG", False)

setup()
