"""What a live token is actually granted, asked of Google rather than of the token file.

token.json's own `scopes` field records the REQUEST, not the grant — measured
2026-08-10 at 11 in the file against 20 at tokeninfo — so the only honest
answer comes from oauth2.googleapis.com/tokeninfo (mise-tageda).
"""

from __future__ import annotations

from typing import Any

import httpx

TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def granted_scopes(client: Any) -> set[str]:
    """Full scope URLs Google says the client's current access token carries.

    Refreshes first if the token is stale (the same path every request takes).
    Raises httpx errors to the caller, which decides how loudly to degrade.
    """
    bearer = client._auth_headers()["Authorization"].removeprefix("Bearer ")
    response = httpx.get(TOKENINFO_URL, params={"access_token": bearer}, timeout=15)
    response.raise_for_status()
    return set(response.json().get("scope", "").split())
