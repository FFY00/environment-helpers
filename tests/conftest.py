import concurrent.futures
import os
import pathlib

import podman
import pytest

import environment_helpers
import environment_helpers.build


@pytest.fixture(scope='session')
def root_path():
    return pathlib.Path(__file__).parent.parent


@pytest.fixture(scope='session')
def packages_path():
    return pathlib.Path(__file__).parent / 'packages'


@pytest.fixture(scope='session')
def example_wheel(packages_path, tmp_path_factory):
    return environment_helpers.build.build_wheel(
        packages_path / 'example',
        tmp_path_factory.mktemp('example-wheel'),
    )


@pytest.fixture
def venv(tmp_path):
    return environment_helpers.create_venv(tmp_path)


@pytest.fixture(scope='session')
def podman_client():
    return podman.from_env()


@pytest.fixture(scope='session')
def container_mount(tmp_path_factory):
    return tmp_path_factory.mktemp('container-mount')


@pytest.fixture(scope='session')
def containers(podman_client, root_path, container_mount):
    debian_setup = ['apt-get update', 'apt-install -y python3 python3-distutils']
    fedora_setup = ['dnf upgrade --refresh', 'dnf install python3 -y']
    container_setup = {
        'debian:10': debian_setup,
        'debian:11': debian_setup,
        'debian:12': debian_setup,
        'ubuntu:20.04': debian_setup,
        'ubuntu:22.04': debian_setup,
        'ubuntu:24.04': debian_setup,
        'fedora:38': fedora_setup,
        'fedora:39': fedora_setup,
        'fedora:40': fedora_setup,
    }

    def run_setup(name, setup_commands):
        podman_client.images.pull(name)
        writable_mount_path = container_mount / name
        writable_mount_path.mkdir()
        container = podman_client.containers.run(
            name,
            ['sh', '-c', 'sleep infinity'],
            detach=True,
            mounts=[
                {
                    'type': 'bind',
                    'source': os.fspath(root_path),
                    'target': '/source',
                    'read_only': True,
                },
                {
                    'type': 'bind',
                    'source': os.fspath(writable_mount_path),
                    'target': '/output',
                    'read_only': False,
                },
            ]
        )
        for command in setup_commands:
            container.exec_run(command)
        return name, container

    containers = {}

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(run_setup, name, setup_commands)
                for name, setup_commands in container_setup.items()
            ]
            for future in concurrent.futures.as_completed(futures):
                name, container = future.result()
                containers[name] = container

        yield containers
    finally:
        # stop the containers
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(container.stop)
                for container in containers.values()
            ]
            concurrent.futures.wait(futures)
