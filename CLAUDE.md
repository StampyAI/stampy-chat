in api/, use pipenv to run python commands. otherwise, `python` doesn't exist, `python3` isn't in venv.

tests are `cd api && pipenv run pytest`.

dev server are in readme or mprocs.yaml, but it's not convenient for claude to run them since they don't halt unless interrupted.

Code style:
- prefer putting sufficiently-short single-line if statements on the same line:

    if x: a()
    else: b()
    if condition(long_parameter=foo.bar().baz() + foo.bar(depth=-1).baz(herp="derp")):
        a()
    else:
        b()

- judiciously use short names to ease human typing, unless readability suffers. one or two acronym names per file is ok. Prefer single word names where possible.
- Don't try/except unless the error needs handling. For errors that will stop the program, just let it crash. Rare, world-stopping-anyway error handling isn't usually worth the readability cost.
