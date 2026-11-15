from __future__ import annotations

import pytest

from custom_components.docker_monitor.image_reference import DockerImageReference


@pytest.mark.parametrize(
    ("reference", "repository", "tag"),
    [
        ("nginx:1.27", "nginx", "1.27"),
        ("nginx", "nginx", "latest"),
        ("prom/prometheus:v2.53.0", "prom/prometheus", "v2.53.0"),
        (
            "ghcr.io/owner/app:latest",
            "ghcr.io/owner/app",
            "latest",
        ),
        ("localhost:5000/app", "localhost:5000/app", "latest"),
        ("localhost:5000/app:2.0", "localhost:5000/app", "2.0"),
        ("nginx:1.27@sha256:abc123", "nginx", "1.27"),
        ("nginx@sha256:abc123", "nginx", None),
        ("sha256:0123456789abcdef", "sha256:0123456789abcdef", None),
    ],
)
def test_parse(reference, repository, tag):
    assert DockerImageReference.parse(reference) == DockerImageReference(
        repository=repository, tag=tag
    )
