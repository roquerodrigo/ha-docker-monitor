"""Address of the Docker Engine the integration talks to."""

from __future__ import annotations

from urllib.parse import urlsplit

from homeassistant.util import slugify

from .const import SUPPORTED_DOCKER_HOST_SCHEMES


class DockerHost:
    """
    A Docker Engine address: a local socket or a remote daemon.

    Accepts the ``DOCKER_HOST`` forms (``unix:///var/run/docker.sock``,
    ``tcp://192.168.1.10:2375``) plus a bare socket path, which is read as a
    ``unix://`` URL so a path and its URL identify the same daemon.
    """

    def __init__(self, address: str) -> None:
        """Initialize."""
        address = address.strip()
        self._url = f"unix://{address}" if address.startswith("/") else address

    @property
    def url(self) -> str:
        """Return the normalized URL."""
        return self._url

    @property
    def unique_id(self) -> str:
        """Return the config entry unique ID for this daemon."""
        return slugify(self._url)

    @property
    def is_supported(self) -> bool:
        """Return True when the URL uses a scheme the client can connect to."""
        parts = urlsplit(self._url)
        if parts.scheme not in SUPPORTED_DOCKER_HOST_SCHEMES:
            return False
        return bool(parts.path) if parts.scheme == "unix" else bool(parts.hostname)
