from __future__ import annotations

import pytest

from custom_components.docker_monitor.docker_host import DockerHost


@pytest.mark.parametrize(
    ("address", "url"),
    [
        ("/var/run/docker.sock", "unix:///var/run/docker.sock"),
        ("  /var/run/docker.sock ", "unix:///var/run/docker.sock"),
        ("unix:///run/docker.sock", "unix:///run/docker.sock"),
        ("tcp://192.168.1.10:2375", "tcp://192.168.1.10:2375"),
    ],
)
def test_url_is_normalized(address, url):
    assert DockerHost(address).url == url


def test_path_and_url_share_unique_id():
    assert (
        DockerHost("/var/run/docker.sock").unique_id
        == DockerHost("unix:///var/run/docker.sock").unique_id
        == "unix_var_run_docker_sock"
    )


@pytest.mark.parametrize(
    "address",
    [
        "/var/run/docker.sock",
        "unix:///var/run/docker.sock",
        "tcp://192.168.1.10:2375",
        "http://docker.local:2375",
        "https://docker.local:2376",
    ],
)
def test_supported_addresses(address):
    assert DockerHost(address).is_supported


@pytest.mark.parametrize(
    "address",
    [
        "",
        "docker.local:2375",
        "ssh://user@192.168.1.10",
        "npipe:////./pipe/docker_engine",
        "tcp://",
        "unix://",
    ],
)
def test_unsupported_addresses(address):
    assert not DockerHost(address).is_supported
