import functools
import json
import os
import subprocess
import sys
import sysconfig
import warnings

from typing import Any, Literal, NamedTuple, Optional, TypedDict


if sys.version_info >= (3, 9):
    import importlib.resources as importlib_resources
else:
    import importlib_resources


LauncherKind = Literal['posix', 'win-ia32', 'win-amd64', 'win-arm', 'win-arm64']


class SchemeDict(TypedDict):
    stdlib: str
    platstdlib: str
    purelib: str
    platlib: str
    include: str
    platinclude: str
    scripts: str
    data: str


class PythonVersion(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


def _run_script(name: str, interpreter: os.PathLike[str], **kwargs: Any) -> Any:
    script = importlib_resources.files('environment_helpers._scripts') / f'{name}.py'
    with importlib_resources.as_file(script) as script_path:
        data = subprocess.check_output([os.fspath(interpreter), os.fspath(script_path)])
    return json.loads(data)


def get_version(interpreter: os.PathLike[str]) -> PythonVersion:
    data = _run_script('version', interpreter)
    return PythonVersion(**data)


def get_virtual_environment_scheme(path: os.PathLike[str]) -> SchemeDict:
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
        return sysconfig.get_paths(vars=config_vars)
    return sysconfig.get_paths(scheme=scheme, vars=config_vars)


@functools.lru_cache
def get_scheme(interpreter: os.PathLike[str], scheme: Optional[str] = None) -> SchemeDict:
    """Finds the installation paths for a certain Python install scheme.

    This helper needs to run the Python interpreter for the target environment.

    :param interpreter: Path to the Python interpreter to introspect.
    :param scheme: Name of the target scheme name. If None, it uses the default scheme.
    """
    return _run_script('scheme', interpreter)


@functools.lru_cache
def get_system_scheme(interpreter: os.PathLike[str]) -> SchemeDict:
    """Finds the installation paths for the system Python install scheme.

    Certain vendors, such as Debian, have a different scheme for system packages.
    This function finds the install scheme for system packages.

    This helper needs to run the Python interpreter for the target environment.

    :param interpreter: Path to the Python interpreter to introspect.
    """
    # Fedora automatically changes the default scheme if RPM_BUILD_ROOT is not set
    environment = os.environ.copy()
    environment['RPM_BUILD_ROOT'] = None
    return _run_script('system-scheme', interpreter, env=environment)


def get_launcher_kind(interpreter: os.PathLike[str]) -> Optional[LauncherKind]:
    """Find the launcher kind.

    This helper needs to run the Python interpreter for the target environment.

    :param interpreter: Path to the Python interpreter to introspect.
    """
    return _run_script('launcher-kind', interpreter)
