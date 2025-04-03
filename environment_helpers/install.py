from __future__ import annotations

import os
import pathlib

import installer
import installer.destinations
import installer.sources
import installer.utils

import environment_helpers.introspect


def install_wheel(
    wheel: pathlib.Path,
    interpreter: pathlib.Path,
    scheme: str | None = None,
) -> None:
    """Install a wheel file to a Python environment."""
    introspectable = environment_helpers.introspect.Introspectable(interpreter)
    destination = installer.destinations.SchemeDictionaryDestination(
        scheme_dict=environment_helpers.introspect.scheme_dict_as_sysconfig(  # type: ignore[arg-type]
            introspectable.get_scheme(),  # type: ignore[arg-type]
        ),
        interpreter=os.fspath(interpreter),
        # FIXME: If the launcher kind is None, it means we don't support scripts for this platform.
        #        We set it to posix in that scenario because installer doesn't support this use-case.
        script_kind=introspectable.get_launcher_kind() or 'posix',
    )
    with installer.sources.WheelFile.open(wheel) as source:
        installer.install(source, destination, additional_metadata={})
