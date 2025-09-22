from __future__ import annotations

import functools
import json
import os
import pathlib
import pickle
import subprocess
import sys
import sysconfig
import typing
import warnings

from collections.abc import Callable
from typing import Any, Generic, Literal, NamedTuple, TypeVar


LauncherKind = Literal['posix', 'win-ia32', 'win-amd64', 'win-arm', 'win-arm64']

T = TypeVar('T')


if sys.version_info >= (3, 11):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class SchemeDict(Generic[T], TypedDict):
    stdlib: T
    platstdlib: T
    purelib: T
    platlib: T
    include: T
    platinclude: T
    scripts: T
    data: T


class PythonVersion(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


def scheme_dict_as_sysconfig(scheme: SchemeDict[os.PathLike[str] | str]) -> SchemeDict[str]:
    return typing.cast(
        SchemeDict[str],
        {
            key: os.fspath(value)  # type: ignore[call-overload]
            for key, value in scheme.items()
        },
    )


def _scheme_dict(scheme: dict[str, str]) -> SchemeDict[pathlib.Path]:
    return typing.cast(
        SchemeDict[pathlib.Path], {key: pathlib.Path(value) for key, value in scheme.items()}
    )


def get_virtual_environment_scheme(path: os.PathLike[str] | str) -> SchemeDict[pathlib.Path]:
    """Calculates the installation paths for the scheme used by a certain virtual environment.

    :param path: Path of the target virtual environment.
    """
    config_vars = sysconfig.get_config_vars().copy()
    config_vars['base'] = config_vars['platbase'] = os.fspath(path)

    # Python 3.11 introduced a "venv" scheme in order to allow users to
    # calculate the paths for a virtual environment.
    # See https://github.com/python/cpython/issues/89576
    if 'venv' in sysconfig.get_scheme_names():
        scheme = 'venv'
    elif os.name == 'nt':
        scheme = 'nt'
    elif os.name == 'posix':
        scheme = 'posix_prefix'
    else:
        warnings.warn(
            f"Unknown platform '{os.name}', using the default install scheme.", stacklevel=2
        )
        return _scheme_dict(sysconfig.get_paths(vars=config_vars))
    return _scheme_dict(sysconfig.get_paths(scheme=scheme, vars=config_vars))


class Introspectable:
    def __init__(self, interpreter: os.PathLike[str] | str) -> None:
        self._interpreter = interpreter

    def _run_script(self, name: str, **kwargs: Any) -> Any:
        script = pathlib.Path(__file__).parent / '_scripts' / f'{name}.py'
        data = subprocess.check_output([os.fspath(self._interpreter), os.fspath(script)], **kwargs)
        return json.loads(data)

    def get_version(self) -> PythonVersion:
        data = self._run_script('version')
        return PythonVersion(**data)

    @functools.lru_cache
    def get_scheme(self, scheme: str | None = None) -> SchemeDict[pathlib.Path]:
        """Finds the installation paths for a certain Python install scheme.

        This helper needs to run the Python interpreter for the target environment.

        :param interpreter: Path to the Python interpreter to introspect.
        :param scheme: Name of the target scheme name. If None, it uses the default scheme.
        """
        return _scheme_dict(self._run_script('scheme'))

    @functools.lru_cache
    def get_system_scheme(self) -> SchemeDict[pathlib.Path]:
        """Finds the installation paths for the system Python install scheme.

        Certain vendors, such as Debian, have a different scheme for system packages.
        This function finds the install scheme for system packages.

        This helper needs to run the Python interpreter for the target environment.
        """
        # Fedora automatically changes the default scheme unless RPM_BUILD_ROOT is set
        environment = os.environ.copy()
        environment['RPM_BUILD_ROOT'] = ''
        return _scheme_dict(self._run_script('system-scheme', env=environment))

    @functools.lru_cache
    def get_launcher_kind(self) -> LauncherKind | None:
        """Find the launcher kind.

        This helper needs to run the Python interpreter for the target environment.
        """
        return typing.cast(LauncherKind | None, self._run_script('launcher-kind'))

    def call(self, func: str | Callable[[Any], T], *args: Any, **kwargs: Any) -> T:
        """Call the a function in the target environment.

        :param interpreter: Path to the Python interpreter to introspect.
        :param func: Function to call.
        :param args: Positional arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        """
        if isinstance(func, str):
            module, func_name = func.rsplit('.', maxsplit=1)
        else:
            module = func.__module__
            func_name = func.__qualname__

        args_dict = {'args': args, 'kwargs': kwargs}
        pickled_args_dict = pickle.dumps(args_dict)

        script = pathlib.Path(__file__).parent / '_scripts' / 'call.py'
        data = subprocess.check_output(
            [os.fspath(self._interpreter), os.fspath(script), module, func_name],
            input=pickled_args_dict,
        )

        return typing.cast(T, pickle.loads(data))
