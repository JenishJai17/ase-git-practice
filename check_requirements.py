"""Check every line of a requirements.txt against PyPI.

Usage: python check_requirements.py [requirements.txt]
"""
import json
import sys
import urllib.error
import urllib.request

PYPI_URL = "https://pypi.org/pypi/{}/json"
PYPI_VERSION_URL = "https://pypi.org/pypi/{}/{}/json"


def fetch_json(url, retries=3):
    """Return parsed JSON for url, or None if PyPI answers 404."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == retries - 1:
                raise


def parse_line(line):
    """Split 'name==version' into (name, version). Version may be None."""
    if "==" in line:
        name, version = line.split("==", 1)
        return name.strip(), version.strip()
    return line.strip(), None


def check(path):
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

    missing_packages = 0
    missing_versions = 0
    oldest = None  # (upload_time, name, version)

    for line in lines:
        name, version = parse_line(line)

        if fetch_json(PYPI_URL.format(name)) is None:
            missing_packages += 1
            continue
        if version is None:
            continue

        release = fetch_json(PYPI_VERSION_URL.format(name, version))
        if release is None:
            missing_versions += 1
            continue

        urls = release.get("urls") or []
        if not urls:
            continue
        upload_time = urls[0]["upload_time"]  # first file listed under urls
        if oldest is None or upload_time < oldest[0]:
            oldest = (upload_time, name, version)

    print(f"Dependencies checked: {len(lines)}")
    print(f"Packages not on PyPI: {missing_packages}")
    print(f"Versions not on PyPI: {missing_versions}")
    if oldest:
        print(f"Oldest pinned release: {oldest[1]}=={oldest[2]} ({oldest[0][:4]})")
    else:
        print("Oldest pinned release: none")


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "requirements.txt")
