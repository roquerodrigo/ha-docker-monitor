# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read [`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for conventions: language, file organisation, naming, typing, properties vs `__init__`, imports, docstrings, comments, coordinator pattern, repairs/diagnostics layout, translations, lint workflow.

For user-facing topics (installation, configuration, entities, options), see [`README.md`](./README.md).

This file deliberately avoids restating those rules — it only adds:

1. The verification workflow agents must run after every change.
2. The architectural reasoning that is not obvious from `CODE_STYLE.md` alone.

## Verification workflow

**After every code change, always run lint then tests, in that order, before declaring the task done.** Run `scripts/lint` (a thin wrapper chaining the same five tools, but running `ruff format` and `ruff check --fix` in their auto-fixing form) or the check-only commands directly:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/docker_monitor
uv run pytest
node --check custom_components/docker_monitor/www/docker-monitor-card.js
```

- Lint runs `ruff format`, `ruff check` and `mypy` — all configured in `pyproject.toml`. Fix any failure and re-run before moving on.
- The bundled Lovelace card is plain JavaScript with no Python gate; `node --check` is its syntax check (CI runs the same command).
- `pytest` enforces a **90 % coverage gate** (`--cov-fail-under` in `pyproject.toml`).

Both gates mirror CI (`.github/workflows/ci.yml`). Skip this only when the change literally cannot affect lint or tests (e.g., README-only edits).

## Bumping the Home Assistant version

The Home Assistant version is pinned in two places and **must be updated together**, otherwise CI, HACS and the test harness drift apart:

1. `pyproject.toml` `[dependency-groups] dev` — `homeassistant==<X.Y.Z>` (runtime/CI lint + mypy) **and** `pytest-homeassistant-custom-component==<matching release>` (the test harness ships its own pinned `homeassistant`; the two pins must come from the same HA release, otherwise lint and tests resolve different cores).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (minimum HA core enforced by HACS).

Verify the pairing on PyPI before committing: the `requires_dist` of `pytest-homeassistant-custom-component` must list the same `homeassistant==<X.Y.Z>` you pinned in `pyproject.toml`.

`pytest`, `pytest-asyncio` and `pytest-cov` are not pinned directly: the harness pins them, so they move with it. Dependabot ignores both `homeassistant` and the harness.

## Architecture

The integration follows the HA `DataUpdateCoordinator` pattern; entity platforms (`sensor/`, `binary_sensor/`) hold one class per file.

### Entry typing

The `data/` package defines the shared typed contracts. `data/runtime.py` holds `DockerMonitorConfigEntry = ConfigEntry[DockerMonitorData]` and the `DockerMonitorData(client, coordinator, integration)` dataclass; `data/__init__.py` re-exports everything (config/options/container/payload/diagnostics types included). State lives on `entry.runtime_data` (auto-discarded on unload), never on `hass.data`.

### Config flow surface

`config_flow.py` implements two user-facing steps; both share the `_validate`
helper and the `_docker_host_schema` builder. There is **no** authentication —
the Docker Engine API takes no credentials over a socket or plain TCP, so there
is no reauth flow:

- `async_step_user` — initial setup; sets unique_id from `DockerHost.unique_id` (the slug of the normalized URL), aborts on duplicate. Entry title is the URL itself (so multiple hosts are distinguishable in the UI).
- `async_step_reconfigure` — lets the user edit the Docker host via the integration's three-dot menu, no delete-and-re-add cycle.
- `async_get_options_flow` — returns `DockerMonitorOptionsFlow` from `options_flow.py` (one class per file).

`_validate` rejects an address `DockerHost.is_supported` refuses with
`{"base": "invalid_host"}`, then opens a client and calls `async_connect()`
(which issues a real `version()` probe) plus `async_list_container_names()`; a
`CommunicationError` maps to `{"base": "connection"}`, anything else to
`{"base": "unknown"}`.

### Docker host

`docker_host.py` holds `DockerHost`, the address value object. The entry
stores the normalized URL under `docker_host`: a bare socket path becomes a
`unix://` URL, so a path and its URL share one unique_id. `unix`, `tcp`, `http`
and `https` are accepted; `ssh://` is refused because aiodocker needs
`asyncssh` for it, which the manifest does not require. Config entry version 1
stored `socket_path`; `async_migrate_entry` rewrites it to version 2, along with
the unique_id and the title when the title was still the path.

### Options flow

`options_flow.py` exposes `scan_interval` (seconds; min `MIN_SCAN_INTERVAL_SECONDS`
= 10, default `DEFAULT_SCAN_INTERVAL_SECONDS` = 15) and `device_name_suffix`.
Changing either triggers `async_reload_entry`, which re-instantiates the
coordinator with the new `update_interval` and re-adds the entities.

`device_name_suffix` only changes the device **name**
(`DockerMonitorEntity._device_name`: `"<container> @ <suffix>"`, blank means
none); the identifiers stay the bare container name, so devices, unique_ids
and the stale-device logic are unaffected. Entity names follow the device name
(`has_entity_name`), and Home Assistant derives the entity_id from it only when
an entity is first registered. The field uses `suggested_value`, not
`default`: with a default, clearing it would bring the old suffix back.

### API client

`api.py` exposes `DockerMonitorApiClient`, a thin async wrapper over
[`aiodocker`](https://github.com/aio-libs/aiodocker). Exceptions live under
`exceptions/`:

- `DockerMonitorApiClientError` (base; also raised when the client is used before `async_connect`)
- `DockerMonitorApiClientCommunicationError` (daemon unreachable, URL rejected by aiodocker, `DockerError`, `OSError`)

`aiodocker.Docker(...)` is lazy, so `async_connect` issues a `version()` call
to fail fast on a bad address. Every request carries `REQUEST_TIMEOUT` (30 s):
aiohttp has no default timeout, and a remote host that stops answering would
otherwise hang the coordinator; the resulting `TimeoutError` is an `OSError`. `async_list_container_states` reads the
public `container["Names"]` mapping and filters auto-generated names via
`_is_anonymous`: only fully hex, id-like names and Compose one-off
`<project>-<service>-run-<hash>` names — a user-named container that merely
ends in a hex-looking segment must stay visible. `async_get_container_data` gathers `stats(stream=False)` +
`show()` (stats only when `include_stats=True`: Docker holds a non-streamed
stats request about a second for its second CPU sample, so the coordinator's
first refresh skips stats and `async_setup_entry` schedules a full refresh in
the background — CPU and memory are `None` until it lands) and derives CPU% (`_calculate_cpu_percent`, the official `docker stats`
formula, plus `_read_online_cpus` for the CPUs the container can use) and
memory in MB (`_calculate_memory`, page cache subtracted the way `docker stats`
does: `total_inactive_file` on cgroup v1, `inactive_file` on cgroup v2, never
the legacy `cache` key). `show()` also
supplies `State.StartedAt` (`_parse_started_at`, which maps Docker's
`0001-01-01T00:00:00Z` never-started value to `None`) and `Config.Image`,
which `DockerImageReference` (`image_reference.py`) splits into repository and
tag for the image sensors and the device manufacturer: a colon only separates
the tag after the last slash (registry ports), a missing tag means `latest`
unless the reference is digest-pinned or a bare image ID. There is no
authentication error type — the Docker Engine API is unauthenticated.

### Diagnostics

`diagnostics.py` returns `DockerMonitorDiagnosticsPayload` with the entry data
(Docker host URL) and the full coordinator snapshot. `TO_REDACT` is **empty** —
a socket path or host address is not a secret. `.github/ISSUE_TEMPLATE/bug.yml` asks users to
attach the dump.

### Repairs

There is no `repairs.py`. `quality_scale.yaml` marks `repair-issues: exempt` —
the integration (a Docker Engine poller) surfaces no recoverable
condition that would warrant a repair flow. Don't add one speculatively; if a
real recoverable failure mode shows up, flip that quality-scale entry when
adding the flow.

### Bundled Lovelace card

`www/docker-monitor-card.js` is a zero-build web component that lists the
containers with health, CPU and memory. `card_registration.py`
(`DockerMonitorCardRegistration`) serves the `www/` directory under
`STATIC_URL_PREFIX` and registers the card as a Lovelace **dashboard
resource** (URL versioned with `?v=<integration version>`), falling back to
`add_extra_js_url` only when resources are YAML-managed. `async_setup_entry`
registers it before anything else; `async_remove_entry` drops the resource
once the last entry is gone. The manifest declares `http` and `lovelace` as
dependencies so both are set up first. The card discovers containers by
`hass.entities` with `platform == "docker_monitor"` and matches entities by
`translation_key` (`cpu`, `memory`, `health`), so it is language independent.
Its two bars share one scale, the share of what the container can use: the
CPU sensor value divided by its `online_cpus` attribute and the memory value
divided by its `memory_limit_mb` attribute; the warning thresholds apply to
those shares.

### Device removal

`__init__.py`'s `async_remove_config_entry_device` only allows deleting a
device from the UI once its container name is missing from the latest
coordinator payload (stopped, renamed or removed). A device backed by a
container Docker still reports is refused, since the next poll would
immediately re-create it; a container that comes back is simply registered
again. `quality_scale.yaml` marks `stale-devices: done` for this.

Devices are also removed automatically. The coordinator lists every container
(`async_list_container_states`, `all=True`) and only fetches stats for the
running ones; `DockerMonitorStaleDeviceRemover` (`stale_device_remover.py`)
then drops the device of any container Docker no longer has at all. A stopped
container still exists and keeps its device. Removal waits
`STALE_DEVICE_GRACE_PERIOD` (5 min, tracked in memory): `docker compose up`
deletes a container before recreating it, and a poll landing in that window
must not discard the device and its entity customisations.
