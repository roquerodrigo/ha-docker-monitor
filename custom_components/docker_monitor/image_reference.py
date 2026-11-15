"""Docker image reference value object."""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_TAG = "latest"
_IMAGE_ID_PREFIX = "sha256:"


@dataclass(frozen=True)
class DockerImageReference:
    """The repository and tag a container was created from."""

    repository: str
    tag: str | None

    @classmethod
    def parse(cls, reference: str) -> DockerImageReference:
        """
        Split an image reference such as ``ghcr.io:443/owner/app:1.2@sha256:…``.

        A colon only separates the tag when it follows the last slash, since a
        registry host may carry a port. A reference without a tag implies
        ``latest`` unless it is pinned to a digest, and a container created
        from a bare image ID has no tag at all.
        """
        if reference.startswith(_IMAGE_ID_PREFIX):
            return cls(repository=reference, tag=None)
        name, _, digest = reference.partition("@")
        tag_separator = name.rfind(":")
        if tag_separator > name.rfind("/"):
            return cls(
                repository=name[:tag_separator],
                tag=name[tag_separator + 1 :],
            )
        return cls(repository=name, tag=None if digest else _DEFAULT_TAG)
