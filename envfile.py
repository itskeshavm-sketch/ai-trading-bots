"""Tiny .env reader/writer - no dependencies."""
import os


def load_env(path=".env"):
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    data[key.strip()] = value.strip()
    return data


def save_env(path, data):
    """Update existing keys in place, append new ones, keep comments."""
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fh:
            lines = fh.read().splitlines()

    out, seen = [], set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in data:
                out.append(f"{key}={data[key]}")
                seen.add(key)
                continue
        out.append(line)

    for key, value in data.items():
        if key not in seen:
            out.append(f"{key}={value}")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return path


def mask(value):
    value = (value or "").strip()
    if not value:
        return "(not set)"
    return "..." + value[-4:] if len(value) > 4 else "..."
