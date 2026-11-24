# Contributing

Bug reports, ideas and pull requests are welcome.

## Reporting a bug

Open an [issue](https://github.com/roquerodrigo/ha-docker-monitor/issues/new/choose) with:

- the Home Assistant version and the integration version;
- what you did, what you expected and what happened;
- the debug log and the diagnostics downloaded from the integration's menu. The diagnostics hold the Docker host address and the names and images of your containers, so review them before attaching.

## Development setup

The project uses [uv](https://docs.astral.sh/uv/) and [Node.js](https://nodejs.org/) for the card's syntax check.

```bash
scripts/setup      # install the dependencies into .venv
scripts/develop    # run Home Assistant at http://localhost:8123 with this integration loaded
```

`scripts/develop` uses the configuration in [`config/`](config/). To have containers to monitor, give that Home Assistant access to a Docker socket or a read-only proxy, as described in the README.

## Checks

Run these before opening a pull request. CI runs the same ones, plus the Home Assistant Marketplace validation. `scripts/lint` runs all five in order.

```bash
uv run ruff format .                                                     # format
uv run ruff check . --fix                                                # lint
uv run mypy custom_components/docker_monitor                             # type-check
uv run pytest                                                            # tests, coverage must stay at 90 % or more
node --check custom_components/docker_monitor/www/docker-monitor-card.js # card syntax
```

`pre-commit install` runs the first three on every commit, along with whitespace, line ending and YAML, JSON and TOML checks.

Read [CODE_STYLE.md](CODE_STYLE.md) before adding or restructuring code.

## Pull requests

1. Fork the repository and branch from `main`.
2. Write commit messages as [Conventional Commits](https://www.conventionalcommits.org/). Releases and their notes are generated from them. Mark breaking changes with `!` or a `BREAKING CHANGE:` footer.
3. Update `translations/en.json` and `translations/pt-BR.json` together when you change user-facing strings. `tests/test_translations.py` fails when their keys differ. The card keeps its own English and Portuguese (Brazil) strings in `www/docker-monitor-card.js`.
4. Update the README when behaviour, configuration, entities or card options change.
5. Fill in the pull request template.

## License

Contributions are released under the project's [MIT License](LICENSE).
