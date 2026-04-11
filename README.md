# Laws Agent

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Adding a new dependency

```sh
pip install <package>
pip freeze > requirements.txt
```

### Removing a dependency

```sh
pip uninstall <package>
pip freeze > requirements.txt
```

## Run

```sh
source .venv/bin/activate
python main.py
```
