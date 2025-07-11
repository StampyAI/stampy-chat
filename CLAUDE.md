in api/, use pipenv to run python commands. otherwise, `python` doesn't exist, `python3` isn't in venv.

tests are `cd api && pipenv run pytest`.

dev server are in readme or mprocs.yaml, but it's not convenient for claude to run them since they don't halt unless interrupted.
