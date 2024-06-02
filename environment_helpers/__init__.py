"""Collection of helpers for managing Python environments."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import venv

from collections.abc import Sequence
from typing import Any, Collection, Literal, Optional, Protocol

import environment_helpers.build
import environment_helpers.install
import environment_helpers.introspect


__version__ = '0.1.3'


class Environment(Protocol):
    """Object representing a Python environment."""

    @property
    def base(self) -> pathlib.Path: ...

    @property
    def interpreter(self) -> pathlib.Path: ...

    @property
    def scripts(self) -> pathlib.Path: ...

    @property
    def scheme(self) -> environment_helpers.introspect.SchemeDict:
        """Default install scheme for the environment."""

    @property
    def introspectable(self) -> environment_helpers.introspect.Introspectable:
        """Introspectable object for the environment."""
        return environment_helpers.introspect.Introspectable(self.interpreter)

    def run_interpreter(self, *args: Sequence[str], **kwargs: Any) -> bytes:
        return subprocess.check_output([os.fspath(self.interpreter), *args], **kwargs)

    def run_script(self, name: str, *args: Sequence[str]) -> bytes:
        return subprocess.check_output([os.fspath(self.scripts / name), *args])

    def install_wheel(self, path: os.PathLike[str], scheme: Optional[str] = None) -> None:
        if not os.path.isfile(path):
            raise ValueError(f"{os.fspath(path)} isn't a file")
        environment_helpers.install.install_wheel(path, self.interpreter, scheme)

    def install_from_path(
        self,
        path: os.PathLike[str],
        scheme: Optional[str] = None,
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
        method: Optional[Literal['pip', 'uv', 'pip-local']] = None,
    ) -> None:
        if not method:
            if (self.scripts / 'pip').is_file():
                method = 'pip-local'
            elif shutil.which('pip'):
                method = 'pip'
            elif shutil.which('uv'):
                method = 'uv'
            else:
                raise ValueError('No valid install method found.')

        if method == 'pip':
            cmd = ['pip', 'install', '--python', os.fspath(self.interpreter), 'install']
        elif method == 'pip-local':
            cmd = [os.fspath(self.interpreter), '-m', 'pip', 'install']
        elif method == 'uv':
            cmd = ['uv', 'pip', '--python', os.fspath(self.interpreter), 'install']

        subprocess.check_call([*cmd, *requirements])


class VirtualEnvironment(Environment):
    """Object representing a virtual environment (using the ``venv`` scheme)."""

    def __init__(self, path: os.PathLike[str]) -> None:
        self._base = os.fspath(path)
        self._scheme = environment_helpers.introspect.get_virtual_environment_scheme(path)
        assert self.interpreter.is_file()

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
    def scheme(self) -> environment_helpers.introspect.SchemeDict:
        return self._scheme


def create_venv(path: os.PathLike[str], **kwargs: Any) -> Environment:
    venv.create(path, **kwargs)
    return VirtualEnvironment(path)
