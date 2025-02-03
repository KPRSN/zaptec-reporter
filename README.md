# Zaptec Reporter 📰

A simple CLI utility for generating usage reports from Zaptec charger installations.

Makes exporting charge reports into a breeze:

- Energy usage. ⚡
- Number of charging sessions. 💯
- Total duration of charging sessions. 🕰️
- Aggregates usage from one or more installations into a single Excel document. 🧮
- Sends usage report emails. 💌

## Usage

The recommended method to generate Zaptec usage reports is by using Docker.

### Installations

To generate usage reports one or more installation IDs must be provided. The IDs of the installations that you have access to can be listed by issuing the `installations` command.

```bash
docker run ghcr.io/kprsn/zaptec-reporter:latest -u USERNAME -p PASSWORD installations
```

### Report

Usage reports may be generated and/or sent as an email by issuing the `generate` command. Make sure to create an output directory if you wish to write the usage report to file, as well as to set up a valid email configuration if you wish to automatically send the usage report as an email. See [config/email_config.yml](config/email_config.yml) for an example.


Generate a usage report using vanilla docker:

```bash
docker run --volume ./data/:/data --volume ./config:/config:ro \
        ghcr.io/kprsn/zaptec-reporter:latest -u USERNAME -p PASSWORD report \
        --excelout /data/report.xlsx --email /config/email_config.yml \
        --from-date "last month" --to-date "this month" INSTALLATIONS_ID
```

Or by using docker compose (don't forget to update your arguments in [docker-compose.yml](docker-compose.yml)):

```
docker compose up zaptec-reporter
```

### Scheduled reports

Usage reports may also be generated on a recurring schedule by the use of a third party tool such as [Ofelia](https://github.com/mcuadros/ofelia). See [docker-compose.yml](docker-compose.yml) for an example where a monthly usage report is automagically generated and sent out via email.

### Email

A usage report may be sent as an email by adding the `--email` flag to the `generate` command. SMTP configuration, sender, receivers and email contents are configured in the provided YAML file. Subject, plaintext body, HTML body and the optional usage report filename all support inclusion of usage reporting data through the [Jinja templating system](https://jinja.palletsprojects.com/en/stable/). See [config/email_config.yml](config/email_config.yml) for an example of how to include usage report data as well as metadata in the email. Note that `--excelout` also supports templating, just like its email counterparts.

|Key|Description|
|---|---|
|`Usage.Charger`|Charger name.|
|`Usage.Energy`|Total energy usage in kWh.|
|`Usage.Duration`|Combined duration of charging sessions.|
|`Usage.Sessions`|Number of charging sessions.|
|`Usage.Installation`|Name of installation in which the charger is installed.|
|`Metadata.Generated`|Time and date of when the report was generated.|
|`Metadata.From`|Start date covered in the report.|
|`Metadata.To`|End date covered in the report.|
|`Metadata.Timezone`|Timezone in which the report was generated.|

## Development

First of all, make sure that you have the Python package and project manager [`uv`](https://github.com/astral-sh/uv) installed.

To generate a report using uv run:

```bash
uv run zaptec-reporter
```

To execute Python unittests run:

```bash
uv run pytest
```

To format and check the Python code using [`ruff`](https://github.com/astral-sh/ruff) run:

```bash
uv run ruff format
uv run ruff check
```

To build Docker image:

```bash
docker build
```

## Bonus material

To work with Github Actions locally using [`act`](https://github.com/nektos/act) and [`zizmor`](https://github.com/woodruffw/zizmor?tab=readme-ov-file):

```bash
# To run actions locally using Act.
act -j test -s GITHUB_TOKEN="$(gh auth token)"

# To run static analysis using Zizmor.
zizmor .
```
