import json
import os
import sys
import sysconfig


class Debian:
    @classmethod
    def is_distutils_pkg_missing(cls):
        """
        Debian partially splits the distutils module from the python3, they
        keep distutils and distutils.version in python3 and put the rest of
        the submodules in python3-distutils.
        """
        try:
            import distutils.version  # isort: skip
            import distutils.core  # noqa: F401
        except ModuleNotFoundError as e:
            if e.name == 'distutils.core':
                return True
        return False

    @classmethod
    def get_scheme_names(cls):
        if sys.version_info >= (3, 12):
            return sysconfig.get_scheme_names()
        if cls.is_distutils_pkg_missing():
            raise Exception("The python3-distutils package is required but it's missing.")
        import distutils.command.install

        return distutils.command.install.INSTALL_SCHEMES.keys()

    @classmethod
    def probe(cls):
        """Are we in Debian Python?"""
        return 'deb_system' in cls.get_scheme_names()

    @classmethod
    def get_system_scheme_paths(cls):
        if sys.version_info >= (3, 12):
            return sysconfig.get_paths('deb_system')
        import distutils.dist

        distribution = distutils.dist.Distribution()
        install_cmd = distribution.get_command_obj('install')
        install_cmd.select_scheme('deb_system')
        install_cmd.finalize_options()
        paths = sysconfig.get_paths()
        paths.update(
            {
                'purelib': install_cmd.install_purelib,
                'platlib': install_cmd.install_platlib,
                'include': os.path.dirname(install_cmd.install_headers),
                'scripts': install_cmd.install_scripts,
                'data': install_cmd.install_data,
            }
        )
        return paths


if Debian.probe():
    paths = Debian.get_system_scheme_paths()
else:
    paths = sysconfig.get_paths()


json.dump(obj=paths, fp=sys.stdout)
