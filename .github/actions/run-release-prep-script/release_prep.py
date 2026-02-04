import os
import requests
from pathlib import Path
from packaging.version import Version
from pyproject_parser import PyProject


def get_latest_published_version(package: str) -> Version:
    url = f"https://pypi.org/pypi/{package}/json"
    resp = requests.get(url, timeout=5)
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
        else:
            return Version(f"{current.base_version}{pre}0")
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
    pyproject = PyProject.load(toml_file)
    current_branch = os.getenv("BRANCH_NAME")

    match current_branch:
        case "release_alpha":
            dev_status = "Development Status :: 3 - Alpha"
        case "release_beta":
            dev_status = "Development Status :: 4 - Beta"
        case _:
            dev_status = "Development Status :: 5 - Production/Stable"

    dev_status_index = next(
        (
            idx
            for idx, string in enumerate(pyproject.project["classifiers"])
            if "Development Status" in string
        ),
        0,
    )
    pyproject.project["classifiers"][dev_status_index] = dev_status
    latest_published_version = get_latest_published_version(pyproject.project["name"])
    pyproject.project["version"] = increment_version(
        latest_published_version, current_branch
    )
    pyproject.dump(toml_file)
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        print(f"new_version={pyproject.project["version"]}", file=output)


if __name__ == "__main__":
    update_pyproject()
