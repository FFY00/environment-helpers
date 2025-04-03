from __future__ import annotations

import contextlib
import os
import pathlib
import subprocess
import tarfile
import tempfile

from collections.abc import Iterable, Mapping, Sequence

import build

import environment_helpers


@contextlib.contextmanager  # type: ignore[arg-type]
def _build_env(isolated: bool = True) -> Iterable[environment_helpers.Environment]:
    if isolated:
        with tempfile.TemporaryDirectory(prefix='environment-helpers-env-') as envdir:
            yield environment_helpers.create_venv(envdir)
    else:
        yield environment_helpers.CurrentEnvironment()


@contextlib.contextmanager  # type: ignore[arg-type]
def _builder(
    srcdir: os.PathLike[str] | str,
    isolated: bool = True,
    quiet: bool = False,
) -> Iterable[tuple[environment_helpers.Environment, build.ProjectBuilder]]:
    def runner(
        cmd: Sequence[str],
        cwd: str | None,
        extra_environ: Mapping[str, str] | None = None,
    ) -> None:
        subprocess.run(cmd, check=True, capture_output=quiet, cwd=cwd, env=env.env | extra_environ)  # type: ignore[operator]

    env: environment_helpers.Environment
    with _build_env(isolated) as env:
        yield env, build.ProjectBuilder(srcdir, env.interpreter, runner)  # type: ignore[arg-type, attr-defined]


def build_sdist(
    srcdir: os.PathLike[str] | str,
    outdir: os.PathLike[str] | str,
    config_settings: build.ConfigSettingsType | None = None,
    isolated: bool = True,
    quiet: bool = False,
) -> pathlib.Path:
    env: environment_helpers.Environment
    builder: build.ProjectBuilder
    with _builder(srcdir, isolated, quiet) as (env, builder):  # type: ignore[misc]
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build('sdist', config_settings or {}))
        sdist_name = builder.build('sdist', outdir, config_settings or {})
    return pathlib.Path(outdir, sdist_name)


def build_wheel(
    srcdir: os.PathLike[str] | str,
    outdir: os.PathLike[str] | str,
    config_settings: build.ConfigSettingsType | None = None,
    isolated: bool = True,
    quiet: bool = False,
) -> pathlib.Path:
    env: environment_helpers.Environment
    builder: build.ProjectBuilder
    with _builder(srcdir, isolated, quiet) as (env, builder):  # type: ignore[misc]
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build('wheel', config_settings or {}))
        wheel_name = builder.build('wheel', outdir, config_settings or {})
    return pathlib.Path(outdir, wheel_name)


def build_wheel_via_sdist(
    srcdir: os.PathLike[str] | str,
    outdir: os.PathLike[str] | str,
    config_settings: build.ConfigSettingsType | None = None,
    isolated: bool = True,
    quiet: bool = False,
) -> pathlib.Path:
    sdist = build_sdist(srcdir, outdir, config_settings or {})
    with tempfile.TemporaryDirectory(prefix='environment-helpers-') as workdir:
        # Extract sdist
        with tarfile.TarFile.open(sdist) as t:
            t.extractall(workdir)
        sdist_dir = os.path.join(workdir, sdist.name[: -len('.tar.gz')])
        # Build wheel from sdist source
        return build_wheel(sdist_dir, outdir, config_settings, isolated, quiet)
