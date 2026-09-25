"""Get a Zerodha Kite access token (valid 1 day — regenerate daily).

Run:  python kite_token.py
1. It prints a login URL. Open it, log in with Zerodha.
2. After login the browser lands on your redirect URL with
   ?request_token=XXXX at the end. Copy XXXX.
3. Paste it here. The script prints KITE_ACCESS_TOKEN.
4. Paste that into your .env as KITE_ACCESS_TOKEN=...
"""
from dotenv import load_dotenv
load_dotenv()

import os


def main():
    from kiteconnect import KiteConnect
    key = os.getenv("KITE_API_KEY", "")
    secret = os.getenv("KITE_API_SECRET", "")
    if not key or not secret:
        print("Put KITE_API_KEY and KITE_API_SECRET in .env first (see README live section).")
        return
    kite = KiteConnect(api_key=key)
    print("Open this URL and log in:")
    print(kite.login_url())
    req = input("Paste request_token here: ").strip()
    try:
        data = kite.generate_session(req, api_secret=secret)
    except Exception as e:
        print(f"Failed: {str(e)[:200]}")
        return
    print("\nYour access token (valid till ~7:30am tomorrow):")
    print(data["access_token"])
    print("Paste into .env as:  KITE_ACCESS_TOKEN=<that token>")


if __name__ == "__main__":
    main()
