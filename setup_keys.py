"""Interactive key setup. Run:  python setup_keys.py

Shows what's already set (masked), prompts for each key with hidden typing,
Enter keeps the current value, '-' clears it. Writes .env, then verifies
the Zen key loads. Full keys are never printed.
"""
import argparse
import getpass
import os

FIELDS = [
    ("OPENCODE_API_KEY", "OpenCode Zen key (AI brain)", True),
    ("BINANCE_API_KEY", "Binance API key (crypto + meme live)", False),
    ("BINANCE_API_SECRET", "Binance API secret", True),
    ("KITE_API_KEY", "Zerodha Kite key (NSE live, optional)", False),
    ("KITE_API_SECRET", "Zerodha Kite secret", True),
    ("KITE_ACCESS_TOKEN", "Zerodha access token (daily, via kite_token.py)", True),
]


def mask(v):
    v = (v or "").strip()
    if not v:
        return "(not set)"
    return "..." + v[-4:] if len(v) > 4 else "..."


def load_env(path):
    d = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip()
    return d


def save_env(path, d):
    lines = []
    if os.path.exists(path):
        with open(path) as f:
            lines = f.read().splitlines()
    seen = set()
    out = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in d:
                out.append(f"{k}={d[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in d.items():
        if k not in seen:
            out.append(f"{k}={v}")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")


def main(path=".env"):
    vals = load_env(path)
    print("Current keys (masked):")
    for key, label, _ in FIELDS:
        print(f"  {label}: {mask(vals.get(key))}")
    print(f"  Testnet: {vals.get('BINANCE_TESTNET', '1')}  "
          f"Live armed: {'YES' if vals.get('LIVE_TRADING') == 'I_UNDERSTAND' else 'no'}")
    for key, label, secret in FIELDS:
        prompt = f"{label} [{mask(vals.get(key))}] (Enter=keep, -=clear): "
        ans = (getpass.getpass(prompt) if secret else input(prompt)).strip()
        if not ans:
            continue
        vals[key] = "" if ans == "-" else ans
    t = input(f"Use Binance testnet? 1=yes 0=real [{vals.get('BINANCE_TESTNET', '1')}]: ").strip()
    if t in ("0", "1"):
        vals["BINANCE_TESTNET"] = t
    arm = getpass.getpass("Arm LIVE trading? type I_UNDERSTAND to arm (Enter=leave): ").strip()
    if arm:
        vals["LIVE_TRADING"] = arm
    save_env(path, vals)
    os.environ["OPENCODE_API_KEY"] = vals.get("OPENCODE_API_KEY", "")
    from brain import get_client
    print("Zen key loads:", "OK" if get_client() else "MISSING")
    print("Saved", path, "- full keys were never shown above.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=".env")
    main(ap.parse_args().file)
