# FleetKey (Windows, Python, No External Dependencies)

A lightweight always-on-top launcher for important files, folders, and websites.

## What It Does

- Always floating window (`-topmost`)
- Gray UI theme
- Set window opacity
- Accordion-style expand/collapse button for shortcuts
- Right-click context menu for extra options
- Resize from window borders/corners
- Click a shortcut to open:
  - local file (example: PDF)
  - folder
  - URL (`https://...`)
- Quick config editing via `shortcuts.json`

## Security-First Design

- Uses Python standard library only (`tkinter`, `json`, `pathlib`, `webbrowser`, `os`)
- No third-party packages
- No `pip install` needed
- Shortcut data is plain local JSON
- Atomic config writes to reduce risk of file corruption
- Collapsed/expanded state and geometry are persisted

## Requirements

- Windows 10/11
- Python 3.11+ from official source
  - Recommended: https://www.python.org/downloads/windows/

## Quick Start (GitHub)

```powershell
git clone <your-repo-url>
cd <your-repo-folder>
python .\app.py
```

If `python` is not available:

```powershell
py .\app.py
```

## Run (Existing Local Folder)

```powershell
cd <path-to-fleetkey-folder>
python .\app.py
```

If `python` is not available:

```powershell
py .\app.py
```

Or just double-click:

- `FleetKey.bat`

## Portable Mode

FleetKey is already portable as a folder app.

1. Keep these files together:
   - `app.py`
   - `shortcuts.json`
   - `FleetKey.bat`
2. Copy the folder to USB or another machine.
3. On target machine, install Python (official source) if needed.
4. Launch with `FleetKey.bat`.

If someone downloads from GitHub as ZIP:

1. Click `Code` -> `Download ZIP` on your repository page.
2. Extract the ZIP to any folder.
3. Open the extracted folder.
4. Run `FleetKey.bat` or `python .\app.py`.

## Configure Shortcuts

Edit `shortcuts.json`:

```json
{
  "opacity": 0.92,
  "geometry": "340x420+60+60",
  "shortcuts": [
    { "label": "My PDF", "target": "C:\\Docs\\important.pdf" },
    { "label": "My Site", "target": "https://example.com" },
    { "label": "My Folder", "target": "%USERPROFILE%\\Desktop" }
  ]
}
```

Then click `Reload List` in the app.

## Simple Product Requirements (Suggested)

1. App starts in under 1 second on normal hardware.
2. Window always stays on top of other windows.
3. Window can be minimized and restored.
4. User can adjust opacity from 30% to 100%.
5. User can resize from window corners/edges.
6. Clicking a shortcut opens either:
   - URL in default browser
   - file/folder in default Windows handler
7. Config changes can be made via local JSON file.
8. No external Python package dependencies.

## Supply-Chain Safety Checklist

1. Install Python only from `python.org` or official Microsoft Store package.
2. Keep this app dependency-free (current setup already is).
3. If you later add dependencies:
   - pin exact versions in `requirements.txt`
   - use hash-checking mode (`pip install --require-hashes -r requirements.txt`)
   - review package maintainers and release history
4. Run app in a standard user account (not admin) when possible.
5. Keep Windows Defender and SmartScreen enabled.

## Code Quality (PEP 8)

- `app.py` is formatted to PEP 8 style.
- `pyproject.toml` includes Ruff settings with `line-length = 79`.
- `.gitignore` excludes `__pycache__` and bytecode files.
- `tests/test_config.py` adds core validation tests.
- `.github/workflows/ci.yml` runs compile + tests on push/PR.

Optional local check (if you install Ruff):

```powershell
ruff check .
```

Run local unit tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Performance Notes

- No external dependencies means quick startup.
- Geometry/opacity writes are debounced to reduce frequent disk writes.
- Config loading sanitizes values to prevent malformed JSON issues.
