"""Detect-then-guide dependency check for the vascii skill.

Reads the local environment only (importlib + sys.platform) and reports
each required runtime dependency as present or missing. When anything is
missing it prints the exact install commands for the current OS.

This script never installs, upgrades, or removes packages, never uses
elevated privileges, and never touches the network. It only reports.
"""

import importlib.metadata
import importlib.util
import json
import platform
import sys


DEPENDENCIES = (
    {
        "name": "Pillow",
        "imports": ("PIL",),
        "pip": "Pillow",
        "why": "image loading and the ASCII conversion core",
    },
    {
        "name": "numpy",
        "imports": ("numpy",),
        "pip": "numpy",
        "why": "pixel math for the ASCII conversion core",
    },
    {
        "name": "rapidocr",
        "imports": ("rapidocr_onnxruntime", "rapidocr"),
        "pip": "rapidocr",
        "why": "default local OCR engine on original pixels",
    },
    {
        "name": "onnxruntime",
        "imports": ("onnxruntime",),
        "pip": "onnxruntime",
        "why": "CPU runtime behind the default local OCR engine",
    },
)

PIP_BUNDLE = "Pillow numpy rapidocr onnxruntime"

SYSTEM_NOTES = {
    "linux": (
        "Optional Tesseract pre-filter path only (Debian/Ubuntu): "
        "apt install tesseract-ocr  [requires administrator privileges]"
    ),
    "macos": (
        "Optional Tesseract pre-filter path only (macOS): "
        "brew install tesseract"
    ),
    "windows": (
        "Optional Tesseract pre-filter path only (Windows): "
        "winget install UB-Mannheim.TesseractOCR"
    ),
}

PIP_COMMANDS = {
    "linux": "python3 -m pip install " + PIP_BUNDLE,
    "macos": "python3 -m pip install " + PIP_BUNDLE,
    "windows": "py -m pip install " + PIP_BUNDLE,
}


def detect_os():
    """Map sys.platform to one of linux, macos, windows, or other."""
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform in ("win32", "cygwin"):
        return "windows"
    return "other"


def check_dependency(dep):
    """Return a present|missing report entry for one dependency."""
    found_import = None
    for module_name in dep["imports"]:
        if importlib.util.find_spec(module_name) is not None:
            found_import = module_name
            break
    entry = {
        "name": dep["name"],
        "status": "present" if found_import else "missing",
        "import": found_import,
        "version": None,
        "why": dep["why"],
    }
    if found_import:
        try:
            entry["version"] = importlib.metadata.version(dep["pip"])
        except importlib.metadata.PackageNotFoundError:
            try:
                entry["version"] = importlib.metadata.version(found_import)
            except importlib.metadata.PackageNotFoundError:
                entry["version"] = "unknown"
    return entry


def main():
    os_name = detect_os()
    report = {
        "tool": "vascii-check",
        "platform": os_name,
        "sys_platform": sys.platform,
        "os_release": platform.system() + " " + platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "dependencies": [check_dependency(dep) for dep in DEPENDENCIES],
        "models": {
            "bundled": False,
            "status": (
                "OCR model files are not bundled with this skill. "
                "Place the model files in the engine cache before "
                "working offline; the OCR step cannot run until they "
                "are present."
            ),
        },
    }
    missing = [d for d in report["dependencies"] if d["status"] == "missing"]
    report["ok"] = not missing

    print(json.dumps(report, indent=2))

    if missing:
        names = ", ".join(d["name"] for d in missing)
        pip_cmd = PIP_COMMANDS.get(os_name, "python3 -m pip install " + PIP_BUNDLE)
        print("")
        print("Missing dependencies: " + names)
        print("This script does not install anything; run the following yourself:")
        print("  " + pip_cmd)
        print("Or install the pinned set with:")
        print("  python3 -m pip install -r requirements.txt")
        system_note = SYSTEM_NOTES.get(os_name)
        if system_note:
            print(system_note)
        print("Re-run this check afterwards to confirm everything is present.")
    else:
        print("")
        print("All dependencies present.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
