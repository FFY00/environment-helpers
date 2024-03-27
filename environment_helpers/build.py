import os
import pathlib
import tarfile
import tempfile

from typing import Optional

import build
import build.env


def build_sdist(
    srcdir: os.PathLike[str],
    outdir: os.PathLike[str],
    config_settings: Optional[build.ConfigSettingsType] = None,
) -> pathlib.Path:
    with build.env.DefaultIsolatedEnv() as env:
        builder = build.ProjectBuilder.from_isolated_env(env, srcdir)
        env.install(builder.build_system_requires)
        env.install(builder.get_requires_for_build('sdist', config_settings or {}))
        sdist_name = builder.build('sdist', outdir, config_settings or {})
    return pathlib.Path(outdir, sdist_name)


def build_wheel_via_sdist(
    srcdir: os.PathLike[str],
    outdir: os.PathLike[str],
    config_settings: Optional[build.ConfigSettingsType] = None,
) -> pathlib.Path:
    sdist = build_sdist(srcdir, outdir, config_settings or {})
    with tempfile.TemporaryDirectory(prefix='environment-helpers-') as workdir:
        # Extract sdist
        with tarfile.TarFile.open(sdist) as t:
            t.extractall(workdir)
        sdist_dir = os.path.join(workdir, sdist.name[: -len('.tar.gz')])
        # Build wheel from sdist source
        with build.env.DefaultIsolatedEnv() as env:
            builder = build.ProjectBuilder.from_isolated_env(env, sdist_dir)
            env.install(builder.build_system_requires)
            env.install(builder.get_requires_for_build('wheel', config_settings or {}))
            wheel_name = builder.build('wheel', outdir, config_settings or {})
    return pathlib.Path(outdir, wheel_name)
