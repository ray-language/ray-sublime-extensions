"""What the index's tools share: reading the entries and checking one."""
import hashlib
import io
import json
import os
import re
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSIONS = os.path.join(ROOT, "extensions")

ID = re.compile(r"^[a-z0-9][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)+$")
VERSION = re.compile(r"^\d+\.\d+\.\d+([-+].*)?$")
KEYS = {"any", "macos-aarch64", "macos-x86_64", "linux-x86_64", "linux-aarch64", "windows-x86_64"}
SHA = re.compile(r"^[0-9a-f]{64}$")


def entries():
    out = []
    for name in sorted(os.listdir(EXTENSIONS)):
        if name.endswith(".json"):
            with open(os.path.join(EXTENSIONS, name), encoding="utf-8") as f:
                out.append((name, json.load(f)))
    return out


def shape(name, e):
    """Everything that can be said without downloading anything."""
    problems = []
    ident = e.get("id", "")
    if not ID.match(ident):
        problems.append(f"{name}: '{ident}' is not an id (publisher.name, lower case)")
    if name != f"{ident}.json":
        problems.append(f"{name}: the file must be named {ident}.json")
    if not e.get("name"):
        problems.append(f"{name}: no name")
    versions = e.get("versions") or []
    if not versions:
        problems.append(f"{name}: no versions")
    seen = set()
    for v in versions:
        number = v.get("version", "")
        where = f"{name} {number}"
        if not VERSION.match(number):
            problems.append(f"{where}: '{number}' is not major.minor.patch")
        if number in seen:
            problems.append(f"{where}: listed twice")
        seen.add(number)
        if not isinstance(v.get("permissions", []), list):
            problems.append(f"{where}: permissions is not a list")
        artifacts = v.get("artifacts") or {}
        if not artifacts:
            problems.append(f"{where}: no artifacts")
        for key, a in artifacts.items():
            if key not in KEYS:
                problems.append(f"{where}: '{key}' is not a platform key")
            if not str(a.get("url", "")).startswith("https://"):
                problems.append(f"{where} {key}: the url is not https")
            if not SHA.match(str(a.get("sha256", ""))):
                problems.append(f"{where} {key}: sha256 is not 64 lower-case hex digits")
            if not isinstance(a.get("size"), int) or a["size"] <= 0:
                problems.append(f"{where} {key}: size is not a positive number")
    return problems


def artifact(name, e, v, key, a):
    """Downloads one zip and checks it against the entry."""
    where = f"{name} {v.get('version')} {key}"
    try:
        with urllib.request.urlopen(a["url"], timeout=120) as r:
            data = r.read()
    except Exception as err:  # noqa: BLE001 - said as it is
        return [f"{where}: cannot download {a['url']}: {err}"]
    problems = []
    if len(data) != a["size"]:
        problems.append(f"{where}: {len(data)} bytes, the entry says {a['size']}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != a["sha256"]:
        problems.append(f"{where}: sha256 is {digest}, the entry says {a['sha256']}")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return problems + [f"{where}: not a zip"]
    names = z.namelist()
    for n in names:
        if n.startswith("/") or ".." in n.split("/") or ":" in n:
            problems.append(f"{where}: the entry {n} reaches outside the extension")
    tops = [n for n in names if n == "extension.json" or (n.count("/") == 1 and n.endswith("/extension.json"))]
    if len(tops) != 1:
        return problems + [f"{where}: there must be one extension.json, at the top or in one folder"]
    manifest = json.loads(z.read(tops[0]))
    if manifest.get("id") != e.get("id"):
        problems.append(f"{where}: its extension.json says id {manifest.get('id')}")
    if manifest.get("version") != v.get("version"):
        problems.append(f"{where}: its extension.json says version {manifest.get('version')}")
    if sorted(manifest.get("permissions", [])) != sorted(v.get("permissions", [])):
        problems.append(f"{where}: it asks for {manifest.get('permissions', [])}, the entry shows {v.get('permissions', [])}")
    return problems
