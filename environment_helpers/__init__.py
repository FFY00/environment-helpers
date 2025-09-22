"""Collection of helpers for managing Python environments."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import venv

from collections.abc import Collection, Mapping
from typing import Any, Literal, Protocol

import environment_helpers.build
import environment_helpers.install
import environment_helpers.introspect


__version__ = '0.3.0'


class Environment(Protocol):
    """Object representing a Python environment."""

    @property
    def base(self) -> pathlib.Path: ...

    @property
    def interpreter(self) -> pathlib.Path: ...

    @property
    def scripts(self) -> pathlib.Path: ...

    @property
    def scheme(self) -> environment_helpers.introspect.SchemeDict[pathlib.Path]:
        """Default install scheme for the environment."""

    @property
    def env(self) -> Mapping[str, str]:
        return os.environ

    @property
    def introspectable(self) -> environment_helpers.introspect.Introspectable:
        """Introspectable object for the environment."""
        return environment_helpers.introspect.Introspectable(self.interpreter)

    def run(self, *args: str | os.PathLike[str], **kwargs: Any) -> bytes:
        default_kwargs = {
            'env': self.env,
        }
        return subprocess.check_output(args, **default_kwargs | kwargs)  # type: ignore[operator, return-value]

    def run_interpreter(self, *args: str | os.PathLike[str], **kwargs: Any) -> bytes:
        return self.run(os.fspath(self.interpreter), *args, **kwargs)

    def run_script(self, name: str | os.PathLike[str], *args: str) -> bytes:
        return self.run(os.fspath(self.scripts / name), *args)

    def install_wheel(self, path: str | os.PathLike[str], scheme: str | None = None) -> None:
        path = pathlib.Path(path)
        if not path.is_file():
            raise ValueError(f"{os.fspath(path)} isn't a file")
        environment_helpers.install.install_wheel(path, self.interpreter, scheme)

    def install_from_path(
        self,
        path: str | os.PathLike[str],
        scheme: str | None = None,
        from_sdist: bool = True,
    ) -> None:
        if not os.path.isdir(path):
            raise ValueError(f"{os.fspath(path)} isn't a directory")
        build_func = (
            environment_helpers.build.build_wheel_via_sdist
            if from_sdist
            else environment_helpers.build.build_wheel
        )
        with tempfile.TemporaryDirectory(prefix='environment-helpers-') as workdir:
            wheel = build_func(path, workdir)
            self.install_wheel(wheel)

    def install(
        self,
        requirements: Collection[str],
        method: Literal['pip', 'uv', 'pip-local'] | None = None,
    ) -> None:
        if not len(requirements):
            return

        if not method:
            if shutil.which('uv'):
                method = 'uv'
            elif (self.scripts / 'pip').is_file():
                method = 'pip-local'
            elif shutil.which('pip'):
                method = 'pip'
            else:
                raise ValueError('No valid install method found.')

        if method == 'pip':
            cmd = ['pip', '--python', os.fspath(self.interpreter), 'install']
        elif method == 'pip-local':
            cmd = [os.fspath(self.interpreter), '-m', 'pip', 'install']
        elif method == 'uv':
            cmd = ['uv', 'pip', 'install', '--python', os.fspath(self.interpreter)]

        self.run(*cmd, *requirements)


class CurrentEnvironment(Environment):
    """Object representing the current environment."""

    @property
    def base(self) -> pathlib.Path:
        return pathlib.Path(sys.prefix)

    @property
    def interpreter(self) -> pathlib.Path:
        return pathlib.Path(sys.executable)

    @property
    def scripts(self) -> pathlib.Path:
        return self.scheme['scripts']

    @property
    def scheme(self) -> environment_helpers.introspect.SchemeDict[pathlib.Path]:
        return environment_helpers.introspect._scheme_dict(sysconfig.get_paths())


class VirtualEnvironment(Environment):
    """Object representing a virtual environment (using the ``venv`` scheme)."""

    def __init__(self, path: os.PathLike[str] | str) -> None:
        self._base = pathlib.Path(path)
        self._scheme = environment_helpers.introspect.get_virtual_environment_scheme(path)
        assert self.interpreter.is_file()

    @classmethod
    def create_venv(cls, path: os.PathLike[str] | str, **kwargs: Any) -> Environment:
        venv.create(path, **kwargs)
        return cls(path)

    @property
    def base(self) -> pathlib.Path:
        return self._base

    @property
    def interpreter(self) -> pathlib.Path:
        name = 'python.exe' if os.name == 'nt' else 'python'
        return self.scripts / name

    @property
    def scripts(self) -> pathlib.Path:
        return pathlib.Path(self._scheme['scripts'])

    @property
    def scheme(self) -> environment_helpers.introspect.SchemeDict[pathlib.Path]:
        return self._scheme

    @property
    def env(self) -> Mapping[str, str]:
        return os.environ | {  # type: ignore[no-any-return, operator]
            'PATH': os.fspath(self.scheme['scripts']) + os.pathsep + os.environ.get('PATH', ''),
            'VIRTUAL_ENV': os.fspath(self.base),
        }


create_venv = VirtualEnvironment.create_venv
