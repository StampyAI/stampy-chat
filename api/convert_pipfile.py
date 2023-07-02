import re


if __name__ == "__main__":
    header = re.compile("\[\[?(?P<header>[a-zA-Z]*)\]?]")
    package = re.compile("""^(?P<library>[a-z-_0-9A-Z]+)\s?=\s?"(?P<version>(?:[=><~]=[0-9.rcbetalph-]+)|\*)"$""")
    in_packages = False
    with open("output-requirements.txt", "w") as output:
        with open("Pipfile", "r") as f:
            for line in f:
                match = header.match(line)
                if match:
                    in_packages = match.groupdict()["header"] == "packages"
                    continue
                if not in_packages:
                    continue
                match = package.match(line)
                if match:
                    depend = match.groupdict()
                    if depend["version"] != "*":
                        output.write(f"{depend['library']}{depend['version']}\n")
                    else:
                        output.write(f"{depend['library']}\n")
