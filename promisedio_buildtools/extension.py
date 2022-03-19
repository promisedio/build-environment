import pkg_resources
from setuptools.extension import Extension as _Extension


class Extension(_Extension):
    def __init__(self, name, sources, *, capsules=None, **kwargs):
        include_dirs = kwargs.pop("include_dirs", None) or []
        include_dirs.append(pkg_resources.resource_filename("promisedio_buildtools", "include"))
        if capsules:
            for capsule in capsules:
                include_dirs.append(pkg_resources.resource_filename(capsule, "capsule"))
        super().__init__(name, sources, include_dirs=include_dirs, **kwargs)
