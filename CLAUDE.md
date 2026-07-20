# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read [`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for conventions: language, file organisation, naming, typing, properties vs `__init__`, imports, docstrings, comments, coordinator pattern, repairs/diagnostics layout, translations, lint workflow.

For user-facing topics (installation, configuration, entities, options), see [`README.md`](./README.md).

This file deliberately avoids restating those rules — it only adds:

1. The verification workflow agents must run after every change.
2. The architectural reasoning that is not obvious from `CODE_STYLE.md` alone.

## Verification workflow

**After every code change, always run lint then tests, in that order, before declaring the task done. Run the tools directly (no `scripts/lint` wrapper):**

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/docker_monitor
uv run pytest
```

- Lint runs `ruff format`, `ruff check` and `mypy` — all configured in `pyproject.toml`. Fix any failure and re-run before moving on.
- `pytest` enforces a **95 % coverage gate** (`--cov-fail-under` in `pyproject.toml`).

Both gates mirror CI (`.github/workflows/ci.yml`). Skip this only when the change literally cannot affect lint or tests (e.g., README-only edits).

## Bumping the Home Assistant version

The Home Assistant version is pinned in two places and **must be updated together**, otherwise CI, HACS and the test harness drift apart:

1. `pyproject.toml` `[dependency-groups] dev` — `homeassistant==<X.Y.Z>` (runtime/CI lint + mypy) **and** `pytest-homeassistant-custom-component==<matching release>` (the test harness ships its own pinned `homeassistant`; the two pins must come from the same HA release, otherwise lint and tests resolve different cores).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (minimum HA core enforced by HACS).

Verify the pairing on PyPI before committing: the `requires_dist` of `pytest-homeassistant-custom-component` must list the same `homeassistant==<X.Y.Z>` you pinned in `pyproject.toml`.

## Architecture

The integration follows the HA `DataUpdateCoordinator` pattern:

```
config_flow.py          → validates credentials and creates the ConfigEntry
__init__.py             → instantiates ApiClient + DataUpdateCoordinator, performs the first refresh
coordinator.py          → polls every scan_interval seconds; returns the typed payload
sensor/, binary_sensor/ → read coordinator.data and create the entities (one class per file)
```

### Entry typing

The `data/` package defines the shared typed contracts. `data/runtime.py` holds `DockerMonitorConfigEntry = ConfigEntry[DockerMonitorData]` and the `DockerMonitorData(client, coordinator, integration)` dataclass; `data/__init__.py` re-exports everything (config/options/container/payload/diagnostics types included). State lives on `entry.runtime_data` (auto-discarded on unload), never on `hass.data`.

### Config flow surface

`config_flow.py` implements two user-facing steps; both share the `_validate`
helper and the `_socket_schema` builder. There is **no** authentication —
the integration talks to a local Docker socket, so there is no reauth flow:

- `async_step_user` — initial setup; sets unique_id from `slugify(socket_path)`, aborts on duplicate. Entry title is the socket path itself (so multiple sockets are distinguishable in the UI).
- `async_step_reconfigure` — lets the user edit the socket path via the integration's three-dot menu, no delete-and-re-add cycle.
- `async_get_options_flow` — returns `DockerMonitorOptionsFlow` from `options_flow.py` (one class per file).

`_validate` opens a client and calls `async_connect()` (which issues a real
`version()` probe) plus `async_list_container_names()`; a
`CommunicationError` maps to `{"base": "connection"}`, anything else to
`{"base": "unknown"}`.

### Options flow

`options_flow.py` exposes `scan_interval` (seconds; min `MIN_SCAN_INTERVAL_SECONDS`
= 10, default `DEFAULT_SCAN_INTERVAL_SECONDS` = 15). Changing it triggers
`async_reload_entry`, which re-instantiates the coordinator with the new
`update_interval`.

### API client

`api.py` exposes `DockerMonitorApiClient`, a thin async wrapper over
[`aiodocker`](https://github.com/aio-libs/aiodocker). Exceptions live under
`exceptions/`:

- `DockerMonitorApiClientError` (base; also raised when the client is used before `async_connect`)
- `DockerMonitorApiClientCommunicationError` (socket unreachable, `DockerError`, `OSError`)

`aiodocker.Docker(...)` is lazy, so `async_connect` issues a `version()` call
to fail fast on a bad socket path. `async_list_container_names` reads the
public `container["Names"]` mapping and filters anonymous (hex-hash) names via
`_is_anonymous`. `async_get_container_data` gathers `stats(stream=False)` +
`show()` and derives CPU% (`_calculate_cpu_percent`, the official `docker stats`
formula) and memory in MB (`_calculate_memory`, cache-subtracted). There is no
authentication error type — Docker over a Unix socket is unauthenticated.

### Diagnostics

`diagnostics.py` returns `DockerMonitorDiagnosticsPayload` with the entry data
(socket path) and the full coordinator snapshot. `TO_REDACT` is **empty** —
a socket path is not a secret. `.github/ISSUE_TEMPLATE/bug.yml` asks users to
attach the dump.

### Repairs

There is no `repairs.py`. `quality_scale.yaml` marks `repair-issues: exempt` —
the integration (a local Docker socket poller) surfaces no recoverable
condition that would warrant a repair flow. Don't add one speculatively; if a
real recoverable failure mode shows up, flip that quality-scale entry when
adding the flow.

### Device removal

`__init__.py`'s `async_remove_config_entry_device` only allows deleting a
device from the UI once its container name is missing from the latest
coordinator payload (stopped, renamed or removed). A device backed by a
container Docker still reports is refused, since the next poll would
immediately re-create it; a container that comes back is simply registered
again. `quality_scale.yaml` marks `stale-devices: done` for this.
