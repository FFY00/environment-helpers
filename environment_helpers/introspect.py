import functools
import json
import os
import pickle
import subprocess
import sys
import sysconfig
import warnings

from collections.abc import Sequence
from typing import Any, Callable, Dict, Literal, NamedTuple, Optional, TypedDict, TypeVar


if sys.version_info >= (3, 9):
    import importlib.resources as importlib_resources
else:
    import importlib_resources


LauncherKind = Literal['posix', 'win-ia32', 'win-amd64', 'win-arm', 'win-arm64']

T = TypeVar('T')


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


class Introspectable:
    def __init__(self, interpreter: os.PathLike[str]) -> None:
        self._interpreter = interpreter

    def _run_script(self, name: str, **kwargs: Any) -> Any:
        script = importlib_resources.files('environment_helpers._scripts') / f'{name}.py'
        with importlib_resources.as_file(script) as script_path:
            data = subprocess.check_output(
                [os.fspath(self._interpreter), os.fspath(script_path)], **kwargs
            )
        return json.loads(data)

    def get_version(self, interpreter: os.PathLike[str]) -> PythonVersion:
        data = self._run_script('version', interpreter)
        return PythonVersion(**data)

    @functools.lru_cache
    def get_scheme(self, interpreter: os.PathLike[str], scheme: Optional[str] = None) -> SchemeDict:
        """Finds the installation paths for a certain Python install scheme.

        This helper needs to run the Python interpreter for the target environment.

        :param interpreter: Path to the Python interpreter to introspect.
        :param scheme: Name of the target scheme name. If None, it uses the default scheme.
        """
        return self._run_script('scheme', interpreter)

    @functools.lru_cache
    def get_system_scheme(self, interpreter: os.PathLike[str]) -> SchemeDict:
        """Finds the installation paths for the system Python install scheme.

        Certain vendors, such as Debian, have a different scheme for system packages.
        This function finds the install scheme for system packages.

        This helper needs to run the Python interpreter for the target environment.

        :param interpreter: Path to the Python interpreter to introspect.
        """
        # Fedora automatically changes the default scheme unless RPM_BUILD_ROOT is set
        environment = os.environ.copy()
        environment['RPM_BUILD_ROOT'] = None
        return self._run_script('system-scheme', interpreter, env=environment)

    @functools.lru_cache
    def get_launcher_kind(self, interpreter: os.PathLike[str]) -> Optional[LauncherKind]:
        """Find the launcher kind.

        This helper needs to run the Python interpreter for the target environment.

        :param interpreter: Path to the Python interpreter to introspect.
        """
        return self._run_script('launcher-kind', interpreter)

    def call(self, func: Callable[[Any], T], *args: Sequence[Any], **kwargs: Dict[str, Any]) -> T:
        """Call the a function in the target environment.

        :param interpreter: Path to the Python interpreter to introspect.
        :param func: Function to call.
        :param args: Positional arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        """
        args_dict = {'args': args, 'kwargs': kwargs}
        pickled_args_dict = pickle.dumps(args_dict)

        script = importlib_resources.files('environment_helpers._scripts') / 'call.py'
        with importlib_resources.as_file(script) as script_path:
            data = subprocess.check_output(
                [
                    os.fspath(self._interpreter),
                    os.fspath(script_path),
                    func.__module__,
                    func.__qualname__,
                ],
                input=pickled_args_dict,
            )

        return pickle.loads(data)
