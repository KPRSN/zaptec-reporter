# Zaptec Reporter 📰

A simple CLI utility for generating usage reports from Zaptec charger installations.

Makes exporting charge reports into a breeze:

- Energy usage. ⚡
- Number of charging sessions. 💯
- Total duration of charging sessions. 🕰️
- Aggregates usage from one or more installations into a single Excel document. 🧮

## Usage

Make sure that you have the Python package and project manager [`uv`](https://github.com/astral-sh/uv) installed, and then run:

```bash
uv run zaptec-reporter
```

## Development

To execute Python unittests run:

```bash
uv run pytest
```

To format and check the Python code using [`ruff`](https://github.com/astral-sh/ruff) run:

```bash
uv run ruff format
uv run ruff check
```
