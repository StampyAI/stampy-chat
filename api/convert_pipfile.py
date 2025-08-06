try:
    import tomllib
except ImportError:
    import tomli as tomllib


def parse_package_spec(name, spec):
    """Parse a package specification into name and version."""
    if isinstance(spec, str):
        # Simple version string like "==1.1.2" or "*"
        if spec == "*":
            return f"{name}\n"
        else:
            return f"{name}{spec}\n"
    elif isinstance(spec, dict):
        # Complex specification with version and/or extras
        version = spec.get("version", "*")
        extras = spec.get("extras", [])
        
        # Format extras for requirements.txt
        if extras:
            extras_str = f"[{','.join(extras)}]"
        else:
            extras_str = ""
        
        if version == "*":
            return f"{name}{extras_str}\n"
        else:
            return f"{name}{extras_str}{version}\n"
    else:
        # Fallback for any other format
        return f"{name}\n"


if __name__ == "__main__":
    with open("Pipfile", "rb") as f:
        pipfile_data = tomllib.load(f)
    
    with open("output-requirements.txt", "w") as output:
        # Process packages section
        packages = pipfile_data.get("packages", {})
        for name, spec in packages.items():
            output.write(parse_package_spec(name, spec))
