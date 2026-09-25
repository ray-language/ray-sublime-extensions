# ray-sublime extensions

The index of extensions for [ray-sublime](https://github.com/ray-language/ray-sublime):
one file per extension in `extensions/`, and `index.json` — all of them put
together — which is what the editor reads (its `extensions_index` setting;
this repo's by default).

## Publishing an extension

1. Build a zip of your extension: `extension.json` at the top of the zip, or
   inside one folder. A service or server you ship as a binary goes in one zip
   per platform (`macos-aarch64`, `macos-x86_64`, `linux-x86_64`,
   `linux-aarch64`, `windows-x86_64` — the `platform()-arch()` key raylang's
   `std/update` uses); one with no binaries is a single `any` zip.
2. Put the zips somewhere they are served over **https** and will not change
   (a GitHub release of your own repo is the usual place).
3. Add or change `extensions/<id>.json` (see below) and run
   `python3 tools/build_index.py` to regenerate `index.json`.
4. Open a pull request. The check downloads every zip it names and refuses the
   entry unless each one is exactly the size and sha256 it says, holds an
   `extension.json` with that id and version, and asks for exactly the
   permissions the entry shows.

```json
{
  "id": "acme.jira",
  "name": "Jira",
  "description": "Issues, from the editor and for the agent.",
  "publisher": "acme",
  "homepage": "https://github.com/acme/ray-jira",
  "versions": [
    {
      "version": "0.3.1",
      "engines": "^0.1.0",
      "date": "2026-09-20",
      "permissions": ["network:acme.atlassian.net", "process"],
      "artifacts": {
        "macos-aarch64": { "url": "https://…/jira-0.3.1-macos-aarch64.zip", "sha256": "…", "size": 812345 },
        "linux-x86_64": { "url": "https://…/jira-0.3.1-linux-x86_64.zip", "sha256": "…", "size": 790112 }
      }
    }
  ]
}
```

Keep old versions in the list: an editor that cannot run the newest one
installs the newest it can.

## What the editor does with it

It shows, for each extension, the newest version it can run on that machine,
and before downloading anything it shows what the extension asks for. What it
downloads is checked against this index — size, sha256, id, version,
permissions — before anything is unpacked. Nothing is updated without the
reader taking the update.

## Checking locally

    python3 tools/validate.py          # every entry, downloading every zip
    python3 tools/build_index.py --check
