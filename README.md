# Home Assistant Docker Monitor

[![CI](https://github.com/roquerodrigo/ha-docker-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-docker-monitor/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-db61a2?logo=githubsponsors&logoColor=white&style=for-the-badge)](https://github.com/sponsors/roquerodrigo)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-docker-monitor&category=integration)

---

Custom [Home Assistant](https://www.home-assistant.io/) integration that monitors Docker containers via the local Docker Engine API. Each named container becomes a device with CPU usage, memory usage, and health check entities.

## Installation

Install through HACS using the button above, or manually copy `custom_components/docker_monitor/` into your Home Assistant `config/custom_components/` directory.

## Prerequisites

The Docker socket (`/var/run/docker.sock`) must be mounted into the Home Assistant container. Add to your compose:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Docker Monitor**.
3. Enter the Docker socket path (default: `/var/run/docker.sock`).

The integration will automatically discover all running named containers and create a device for each one.

## Entities

For each container:

| Entity | Type | Description |
|---|---|---|
| CPU | Sensor | CPU usage percentage |
| Memory | Sensor | Memory usage in MB |
| Health | Binary Sensor | Health check status (only for containers with a health check configured) |

## Options

- **Scan interval** (default: 15 seconds, minimum: 10 seconds)

## How it works

- Connects to the Docker Engine API via Unix socket using [aiodocker](https://github.com/aio-libs/aiodocker).
- Polls all running containers at the configured interval.
- Containers are identified by name (stable across `docker compose up --force-recreate`).
- Auto-named containers (Compose one-off `run` containers and id-like hex names) are excluded.
- Stopped or removed containers become unavailable.

## Support

This integration is built and maintained on personal time, on hardware bought for the purpose. If it is useful to you, consider [sponsoring the work](https://github.com/sponsors/roquerodrigo) — it keeps the devices, the testing and the releases coming.

## License

[MIT](LICENSE)
