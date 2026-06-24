"""One-time interactive script to authenticate with Monarch Money and save the session."""

import asyncio
import os
import sys

from dotenv import load_dotenv
from monarchmoney import MonarchMoney, RequireMFAException

load_dotenv()


async def main():
    if os.environ.get("DEMO_MODE", "").strip().lower() == "true":
        sys.exit("Refusing to log in: DEMO_MODE is enabled (this instance is demo-only).")

    session_file = os.environ.get("MONARCH_SESSION_FILE", ".monarch_session")

    mm = MonarchMoney()

    print("=== Monarch Money Login ===")
    email = input("Email: ")
    password = input("Password: ")

    try:
        await mm.login(email, password)
    except RequireMFAException:
        print("\nMFA required. Check your authenticator app or email.")
        mfa_code = input("MFA code: ")
        await mm.multi_factor_authenticate(email, password, mfa_code)
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        sys.exit(1)

    mm.save_session(session_file)
    print(f"\nSession saved to {session_file}")

    # Verify by fetching accounts
    accounts = await mm.get_accounts()
    count = len(accounts.get("accounts", []))
    print(f"Verified: found {count} accounts")


if __name__ == "__main__":
    asyncio.run(main())
