import os

import nox
from nox import options

PROJECT_PATH = os.path.join(".", "src")
SCRIPT_PATHS = [PROJECT_PATH, "noxfile.py"]

VENV_BACKEND_ARGS = ["--clear"]

options.default_venv_backend = "uv"
options.sessions = ["format_fix", "pyright"]


@nox.session(venv_params=VENV_BACKEND_ARGS)
def format_fix(session: nox.Session) -> None:
    session.run_install("uv", "sync", "-q", "--only-dev", "--active")
    session.run("uv", "run", "--active", "ruff", "format", *SCRIPT_PATHS)
    session.run("uv", "run", "--active", "ruff", "check", *SCRIPT_PATHS, "--fix")


@nox.session(venv_params=VENV_BACKEND_ARGS)
def format_check(session: nox.Session) -> None:
    session.run_install("uv", "sync", "-q", "--only-dev", "--active")
    session.run("uv", "run", "--active", "ruff", "format", *SCRIPT_PATHS, "--check")
    session.run("uv", "run", "--active", "ruff", "check", *SCRIPT_PATHS)


@nox.session(venv_params=VENV_BACKEND_ARGS)
def pyright(session: nox.Session) -> None:
    session.run_install("uv", "sync", "-q", "--dev", "--group", "nox", "--active")
    session.run("uv", "run", "--active", "pyright", *SCRIPT_PATHS)
