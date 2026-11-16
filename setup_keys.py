"""Interactive broker-key setup. Run:  python setup_keys.py

Shows what's already set (masked), prompts for each broker key with hidden
typing, Enter keeps the current value, '-' clears it. Writes .env.
Full keys are never printed.

The AI provider (base URL + key + model) is configured separately by
setup_provider.py, because it needs a model list fetched from the provider.
"""
import argparse
import getpass
import os
import subprocess
import sys

from envfile import load_env, save_env, mask

FIELDS = [
    ("BINANCE_API_KEY", "Binance API key (crypto + meme live)", False),
    ("BINANCE_API_SECRET", "Binance API secret", True),
    ("KITE_API_KEY", "Zerodha Kite key (NSE live, optional)", False),
    ("KITE_API_SECRET", "Zerodha Kite secret", True),
    ("KITE_ACCESS_TOKEN", "Zerodha access token (daily, via kite_token.py)", True),
]


def migrate_legacy(values):
    """Old installs used OPENCODE_API_KEY for the Zen API."""
    legacy = values.pop("OPENCODE_API_KEY", None)
    if legacy and not values.get("AI_API_KEY"):
        values["AI_API_KEY"] = legacy
        if not values.get("AI_BASE_URL"):
            values["AI_BASE_URL"] = "https://opencode.ai/zen/v1"
    return values


def main(path=".env"):
    values = migrate_legacy(load_env(path))

    print("AI provider")
    print(f"  Base URL: {values.get('AI_BASE_URL') or '(not set)'}")
    print(f"  Model   : {values.get('AI_MODEL') or '(not set)'}")
    print(f"  API key : {mask(values.get('AI_API_KEY'))}")
    print("\nBroker keys (only needed for live trading)")
    for key, label, _ in FIELDS:
        print(f"  {label}: {mask(values.get(key))}")
    print(f"  Testnet: {values.get('BINANCE_TESTNET', '1')}  "
          f"Live armed: {'YES' if values.get('LIVE_TRADING') == 'I_UNDERSTAND' else 'no'}")

    for key, label, secret in FIELDS:
        prompt = f"{label} [{mask(values.get(key))}] (Enter=keep, -=clear): "
        ans = (getpass.getpass(prompt) if secret else input(prompt)).strip()
        if not ans:
            continue
        values[key] = "" if ans == "-" else ans

    testnet = input(f"Use Binance testnet? 1=yes 0=real [{values.get('BINANCE_TESTNET', '1')}]: ").strip()
    if testnet in ("0", "1"):
        values["BINANCE_TESTNET"] = testnet
    arm = getpass.getpass("Arm LIVE trading? type I_UNDERSTAND to arm (Enter=leave): ").strip()
    if arm:
        values["LIVE_TRADING"] = arm

    save_env(path, values)
    print(f"\nSaved {path} - full keys were never shown above.")

    if not values.get("AI_API_KEY"):
        print("\nNo AI provider configured yet. Running setup_provider.py now.")
        subprocess.run([sys.executable, "setup_provider.py", "--env-file", path])
    else:
        print("\nAI provider already configured. Change it any time with: python setup_provider.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=".env")
    main(ap.parse_args().file)
