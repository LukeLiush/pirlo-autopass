# pirlo-autopass

Autonomous browser automation and login session playbooks for [Pirlo](https://github.com/LukeLiush/pirlo).

## Installation

```bash
pip install pirlo-autopass
```

Or for local development:

```bash
pip install -e .
```

## Features

- **`pirlo autopass`**: Self-healing browser automation workflow using LLMs and CloakBrowser.
- **`pirlo login`**: Interactive browser session manager to save persistent authentication cookies.

## Usage

```bash
# Authenticate a profile
pirlo login --profile my-profile --urls https://github.com

# Execute autonomous task
pirlo autopass --task "Search for trending python repositories" --profile my-profile
```
