import os
import requests
import tomlkit
from pathlib import Path
from packaging.version import Version


def get_latest_published_version(package: str) -> Version:
    url = f"https://pypi.org/pypi/{package}/json"
    resp = requests.get(url, timeout=5)
    if resp.status_code == 404:
        return
    resp.raise_for_status()
    data = resp.json()
    versions = list(data["releases"].keys())
    versions.sort(key=Version, reverse=True)
    return Version(versions[0]) if len(versions) else None


def increment_version(current: Version, branch: str) -> str:
    if not current:
        current = Version(f"0.0.0")

    if "alpha" in branch or "beta" in branch:
        pre = "a" if "alpha" in branch else "b"
        if current.pre and current.pre[0] == pre:
            return Version(
                f"{current.base_version}{current.pre[0]}{current.pre[1] + 1}"
            )
        elif current.pre and current.pre[0] < pre:
            # Promote to the next pre-release stage of the same version,
            # e.g. 8.2.0a17 -> 8.2.0b0
            return Version(f"{current.base_version}{pre}0")
        else:
            return Version(f"{current.major}.{current.minor + 1}.{0}{pre}0")
    else:
        match branch:
            case "release_major":
                return Version(f"{current.major + 1}.{0}.{0}")
            case "release_minor":
                return Version(f"{current.major}.{current.minor + 1}.{0}")
            case "release_patch":
                return Version(f"{current.major}.{current.minor}.{current.micro + 1}")
            case _:
                raise ValueError("Unable to identify release version")


def update_pyproject():
    toml_file = Path("pyproject.toml")
    pyproject = tomlkit.parse(toml_file.read_text())
    project = pyproject["project"]
    classifiers = project.get("classifiers", [])
    current_branch = os.getenv("BRANCH_NAME")

    dev_status_index = next(
        (
            idx
            for idx, string in enumerate(classifiers)
            if "Development Status" in string
        ),
        None,
    )

    if (
        dev_status_index is not None
        and classifiers[dev_status_index] != "Development Status :: 7 - Inactive"
    ):
        match current_branch:
            case "release_alpha":
                dev_status = "Development Status :: 3 - Alpha"
            case "release_beta":
                dev_status = "Development Status :: 4 - Beta"
            case _:
                dev_status = "Development Status :: 5 - Production/Stable"
        classifiers[dev_status_index] = dev_status

    latest_published_version = get_latest_published_version(project["name"])
    new_version = increment_version(latest_published_version, current_branch)
    project["version"] = str(new_version)

    toml_file.write_text(tomlkit.dumps(pyproject))
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        print(f"new_version={new_version}", file=output)


if __name__ == "__main__":
    update_pyproject()
