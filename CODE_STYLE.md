# Code Style Guide

Style conventions for the `ha-docker-monitor` project. Before committing,
run `scripts/lint` — or the underlying commands directly:
`uv run ruff format --check .`, `uv run ruff check .`,
`uv run mypy custom_components/docker_monitor` and `uv run pytest`
(with the 90 % coverage gate). All must exit cleanly.

**Always read this file before adding or restructuring code.**

## Quality scale target

This integration applies the pertinent **Bronze/Silver/Gold** rules of the
[Home Assistant Integration Quality
Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/);
Platinum is an aspiration, not a claim. Each tier inherits every rule from the
previous one:

- **Bronze** — UI setup via `config_flow`, config-flow tests, user-facing docs.
- **Silver** — active code owner, automatic recovery from connection errors,
  no log spam on transient failures.
- **Gold** — full test coverage, entity translations, reconfigure flow,
  diagnostics download, optional discovery.
- **Platinum** — strict typing, fully async code base, efficient data handling
  (no redundant polling or state-machine writes).

The `custom_components/docker_monitor/quality_scale.yaml` file lists each rule
as `done` / `todo` / `exempt` (with a reason). Its claims must stay honest:
update the file in the same PR that satisfies a new rule, and never mark a
rule `done` ahead of the code.

## Language

- Code is written in **English**: file names, class names, function names,
  variable names, dictionary keys, identifier strings.
- The conversation language with the user can be Portuguese or anything else;
  what is committed to disk stays English.
- User-facing strings live in `custom_components/docker_monitor/translations/{en,pt-BR}.json`
  only — never hardcoded in Python.

## File organization

- **One top-level class per file.** Multiple semantically related classes (e.g.
  exception families, sensor entities for one platform) get grouped into a
  package directory with one class per submodule and an `__init__.py`
  re-exporting the public symbols.
  - Example: `exceptions/` contains `api_client_error.py` and
    `api_client_communication_error.py`, plus `__init__.py`; the shared typed
    contracts live in the `data/` package, one shape per submodule.
- **TypedDicts and `type` aliases do not count as "classes"** for this rule.
  Shared shapes get their own `data/` submodule; a TypedDict or alias with a
  single consumer may live directly in the module that uses it.
- **Helper functions** may live in the same file as the single class that uses
  them (e.g. `_is_anonymous` and the stats calculators in `api.py`).
- **`__init__.py` of the integration package** wires the entry lifecycle hooks
  Home Assistant looks up by name — `async_setup_entry`, `async_unload_entry`,
  `async_reload_entry`, `async_remove_config_entry_device` — and nothing else.

## Entities: one class per entity

- **One class per entity.** Every entity gets its own dedicated class — never
  share a generic class parameterized by an `EntityDescription` subclass with
  callable fields like `value_fn` or `action_fn`. Encode the entity's behaviour
  directly in its class via `@property` and class-level `_attr_*` constants
  (or a plain `EntityDescription` instance assigned at the class level).
  - Don't write an `<DOMAIN><Platform>Description` subclass with a
    `value_fn` / `action_fn` field.
  - Do write `<DOMAIN><Name><Platform>` (e.g. `DockerMonitorCpuSensor`,
    `DockerMonitorMemorySensor`, `DockerMonitorHealthBinarySensor`).
- The reason: each entity is a discrete contract; mixing them through a
  generic class hides the contract behind indirection and discourages per-entity
  refinement (icons, state attributes, custom logic).

## Naming

- Public classes are prefixed with `DockerMonitor` (rename to
  `<YourDomain>` when forking).
- Concrete platform entities end with the entity type:
  `DockerMonitorCpuSensor`, `DockerMonitorMemorySensor`,
  `DockerMonitorHealthBinarySensor`.
- Exception classes end with `Error`: `DockerMonitorApiClientError`,
  `…CommunicationError`.
- Private attributes / functions are prefixed with `_`.

## Typing

**Strict typing. No generics, no `Any`.** Mypy (`uv run mypy custom_components/docker_monitor`) enforces this.

Banned: `typing.Any`, `object` as a value type, bare `dict` / `list` / `tuple` /
`set`, `dict[str, Any]`, `Mapping[str, Any]`.

Required:

- `TypedDict` for known dict / JSON shapes (see the `data/` package for the
  canonical examples: `DockerMonitorConfigData`, `DockerMonitorOptionsData`,
  `DockerMonitorContainerData`, `DockerMonitorPayload`,
  `DockerMonitorDiagnosticsPayload`).
- `@dataclass` for structured records (`DockerMonitorData` in
  `data/runtime.py`).
- Named `type` aliases for recursive / shared shapes (e.g. JSON value
  aliases for payloads whose schema is not ours to pin down).
- `frozenset[str]` / `tuple[str, ...]` for fixed string collections.
- `cast("TypedDictName", value)` at HA framework boundaries that hand us a
  permissive type (e.g. `entry.data` is `MappingProxyType[str, Any]`).

When narrowing an HA-provided callback signature (e.g. `async_step_user`),
mypy reports `[override]` (Liskov violation). Add `# type: ignore[override]`
with a one-line comment explaining the deliberate narrowing — see
`config_flow.py` for the canonical example.

## Properties and `__init__`

- **Always prefer `@property`** over assigning `_attr_*` values in `__init__`.
  Properties are computed lazily from backing fields stored on the parent class
  (e.g. `self.coordinator`, `self.entity_description`).
- When the body of `__init__` would only call `super().__init__(...)`, omit
  `__init__` entirely and let Python inherit the parent.
- Class-level constants like `_attr_attribution = ATTRIBUTION` and
  `_attr_has_entity_name = True` are fine — they don't depend on instance
  state.

## Imports

- Always start every module with `from __future__ import annotations` so type
  hints become lazy strings and the runtime cost of `if TYPE_CHECKING` imports
  is zero.
- Same-package relative imports (`from .module import …`) are the default.
- Move type-only imports into a `TYPE_CHECKING` block (Ruff `TC001`/`TC003`):

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from collections.abc import Mapping
      from .data import DockerMonitorConfigData
  ```

- `noqa` comments are reserved for unavoidable framework constraints (e.g.
  `# noqa: ARG001` for HA-framework callback parameters that must exist but go
  unused). Document the reason inline if non-obvious. Never silence to "make
  ruff happy" — fix the underlying code.

## Docstrings

- Every public class, function, method (including `@property`) and `__init__`
  has a docstring. Ruff enforces this via `D102`/`D107`.
- A single sentence is usually enough. Describe the *contract* or the *why*,
  not the obvious implementation.
- Module-level docstring at the top of every `.py` file.
- Avoid restating the type — the signature already does that.

## Comments

- Default to **no comments**. Add one only when the *why* is not obvious from
  the code: a hidden constraint, a workaround, a subtle invariant, or a
  deliberate type-system override.
- Never describe *what* the code does — well-named identifiers handle that.
- **No section dividers** like `# --- API payloads ---` to group related
  declarations. If a file has so many sections that you feel the need for
  visual separators, split it into multiple files instead.

## Logging

- Each module uses the package-level `LOGGER` from `const.py`
  (`LOGGER: Logger = getLogger(__package__)`); never call `logging.getLogger(...)`
  ad-hoc.
- Use **lazy `%`-formatting**, never f-strings — they force string interpolation
  even when the level is filtered:

  ```python
  LOGGER.warning("Refresh failed: %s", exception)   # ✓
  LOGGER.warning(f"Refresh failed: {exception}")    # ✗
  ```

- Levels:
  - `debug` — successful fetch summaries, every-poll diagnostics.
  - `info` — one-shot lifecycle (setup complete, entry reloaded).
  - `warning` — recoverable failures (transient API error, falling back).
  - `error` / `exception` — unrecoverable in current cycle; pair `exception`
    with caught exceptions inside `except` blocks for full tracebacks.
- Never log secrets (`token`, `password`, `key`, full headers). The
  `Coordinator → UpdateFailed` mapping should swallow the original exception's
  string form when it could expose them.

## Error messages

- Format: `"Failed to <verb> <object>: <cause>"` where `<cause>` is the
  exception or a short reason. Keep them short and grep-able.
- Validate before creating the entry: `config_flow._validate` probes the
  socket with a real connection so user-facing errors point at the bad
  socket path, not a downstream traceback.
- Custom exceptions form a hierarchy: `DockerMonitorApiClientError` (base;
  also raised when the client is used before `async_connect`) →
  `…CommunicationError` (unreachable socket, `DockerError`, `OSError`).
  There is no authentication error type — the Docker Unix socket is
  unauthenticated. Wrap raw upstream errors at the API client boundary;
  everything above only catches the custom hierarchy.

## Coordinator and runtime data

- All API state flows through `entry.runtime_data: DockerMonitorData`
  (`data/runtime.py`). Never store integration state in `hass.data` —
  `runtime_data` is auto-discarded on unload, the legacy
  `hass.data[DOMAIN][entry_id]` pattern is not.
- The coordinator is typed as `DataUpdateCoordinator[DockerMonitorPayload]`.
  `_async_update_data` returns the typed payload.
- Use `await coordinator.async_config_entry_first_refresh()` during
  `async_setup_entry` (not `async_refresh()`) — a failed first refresh raises
  `ConfigEntryNotReady` and HA retries with backoff automatically.
- Pass `always_update=False` to the coordinator when the payload TypedDict
  compares cleanly with `__eq__`; HA then skips listener callbacks and state
  writes when the data hasn't changed.
- Error mapping inside `_async_update_data`: every
  `DockerMonitorApiClientError` becomes `UpdateFailed`, with the message
  already sanitized at the API client boundary. There is no
  `ConfigEntryAuthFailed` path — the Docker socket has no credentials.

## Config / options / diagnostics / repairs

- `config_flow.py` carries the `user` and `reconfigure` steps, sharing one
  `_validate` helper and one `_socket_schema` builder. There is no reauth
  flow — the socket is unauthenticated.
- `options_flow.py` holds the single `DockerMonitorOptionsFlow`
  class. New options keys go into the `DockerMonitorOptionsData`
  TypedDict in `data/options_data.py`.
- `diagnostics.py` returns `DockerMonitorDiagnosticsPayload`. Sensitive
  keys go into the `TO_REDACT: frozenset[str]` constant — currently empty,
  because a socket path is not a secret.
- There is no `repairs.py`; the integration surfaces no recoverable condition
  that warrants a repair flow (see `CLAUDE.md`). Don't add one speculatively.

## Translations

- Two locales: `en.json` and `pt-BR.json`. `tests/test_translations.py`
  parametrizes over every locale and fails if their nested key sets diverge.
- Options strings live under `options.step.init.data`; flow strings under
  `config.step.<step_id>`, `config.error` and `config.abort`; entity names
  under `entity.<platform>.<key>.name`.

## HACS publishing requirements

[HACS](https://www.hacs.xyz/docs/publish/integration/) validates the repository
shape on every push via `hacs/action@main` (and HA itself runs `hassfest`).
Both gates must stay green:

- **One integration per repository**, located in `custom_components/<domain>/`.
- `manifest.json` must declare `domain`, `name`, `version`, `documentation`,
  `issue_tracker`, `codeowners`. The `version` key is **mandatory for custom
  integrations** (omit it in core integrations only) and must parse as
  `AwesomeVersion` — CalVer or SemVer.
- `hacs.json` at the repo root pins the minimum HA core via the
  `homeassistant` key. This is the third HA pin (see `CLAUDE.md`).
- Brand assets ship **in this repo** under `custom_components/<domain>/brand/`
  — `icon.png`, `logo.png` (+ `@2x` variants) and `icon.svg`. Bundling them
  in-repo means HACS installs render correctly without depending on the upstream
  [home-assistant/brands](https://github.com/home-assistant/brands) repo.
- A `README.md` at the repo root is required; HACS surfaces it as the
  integration description.

Release-please tags releases on every merge to `main`; HACS surfaces the five
most recent GitHub releases to users, so keep the changelog grep-able.

## Pre-commit hooks

`pre-commit` is a dev dependency (`pyproject.toml`) and `.pre-commit-config.yaml`
runs the lint commands (ruff format, ruff check, mypy) as local `uv run`
hooks, so the hook tools are always the versions pinned in `pyproject.toml`.
Install once per clone:

```bash
pre-commit install
```

The hooks run the same gates as CI on every commit. Skip them only on
emergency `git commit --no-verify` and immediately re-run `scripts/lint`
(or the direct commands).

## Conventional commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/),
which `release-please` parses to bump the version and generate `CHANGELOG.md`:

| Type | Meaning | Bump |
|---|---|---|
| `feat` | New feature | minor |
| `fix` | Bug fix | patch |
| `perf` | Performance improvement | patch |
| `deps` | Dependency bump | patch |
| `docs` | Documentation only | none |
| `refactor` | Refactor without behavior change | none |
| `test` | Test-only change | none |
| `ci` | CI / tooling change | none |
| `chore` | Anything else (rarely) | none |

- Subject line: imperative mood, lowercase, no trailing period.
- Use scopes when useful: `fix(sensor): map non-enum interface values to None`.
- A `BREAKING CHANGE:` footer (or `!` after type) bumps the major version.

## Linting and verification

- Ruff configuration lives in `pyproject.toml` (`[tool.ruff]`) with `select = ["ALL"]`.
- Mypy configuration lives in `pyproject.toml` (`[tool.mypy]`). Run both with
  `uv run ruff check .` and `uv run mypy custom_components/docker_monitor`.
- After every change run `scripts/lint`, or the direct commands:
  `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run mypy custom_components/docker_monitor` and `uv run pytest`.
  Both gates mirror CI.
- Tests live in `tests/`, mirroring the production layout. The 90 % coverage
  gate (`pyproject.toml`, `[tool.pytest.ini_options]`) prevents untested code
  from sneaking in. When a test
  exercises a state that is impossible under the new types, update or remove
  it — never weaken the type to satisfy the test.
