import concurrent.futures
import json
import os
import pathlib
import uuid

from typing import List, NamedTuple

import podman
import podman.domain.containers
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


@pytest.fixture()
def venv(tmp_path):
    return environment_helpers.create_venv(tmp_path)


@pytest.fixture(scope='session')
def podman_client():
    return podman.from_env()


@pytest.fixture(scope='session')
def container_mount(tmp_path_factory):
    return tmp_path_factory.mktemp('container-mount')


class ContainerExecutionError(Exception):
    def __init__(self, code: int, response: bytes) -> None:
        super().__init__(f'Command exited with code {code} (response: {response})')


class Container(NamedTuple):
    name: str
    handle: podman.domain.containers.Container
    writable_mount: pathlib.Path

    def __repr__(self) -> str:
        return f'Container({self.name})'

    def run(self, command: List[str]) -> None:
        code, response = self.handle.exec_run(command)
        if code != 0:
            raise ContainerExecutionError(code, response)

    def introspect(self, action: str) -> object:
        filename = f'{action}-{uuid.uuid4()}.json'
        self.run(
            [
                'python3',
                '/source/tests/helpers/introspect.py',
                f'--write-to-file=/output/{filename}',
            ]
        )
        with self.writable_mount.joinpath(filename).open('r') as f:
            return json.load(f)


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
        handle = podman_client.containers.run(
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
            ],
        )
        container = Container(name, handle, writable_mount_path)
        for command in setup_commands:
            container.run(command)
        return container

    containers = {}

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(run_setup, name, setup_commands)
                for name, setup_commands in container_setup.items()
            ]
            for future in concurrent.futures.as_completed(futures):
                container = future.result()
                containers[container.name] = container

        yield containers
    finally:
        # stop the containers
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(container.handle.stop) for container in containers.values()]
            concurrent.futures.wait(futures)
