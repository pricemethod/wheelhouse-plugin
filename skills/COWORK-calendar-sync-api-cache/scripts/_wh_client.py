#!/usr/bin/env python3
"""
Minimal shared HTTP client for the Wheelhouse RM API (direct, no MCP/Claude
in the loop). Used by sync_calendar.py in this skill.

Why this exists: doing bulk portfolio syncs by having an LLM call an MCP tool
once per listing per data type is enormously more expensive in Claude usage
than a plain script hitting the REST API directly -- the LLM has to receive,
read, and reason about every single response just to decide "write this to
disk." A script does the identical HTTP calls and file writes without any of
that per-record reasoning cost. Claude's job becomes: run this script once,
read its short summary. That's the entire point of this file's existence.

This is a copy of the sibling wheelhouse-data-sync-api / wheelhouse-
reservations-sync-api skills' _wh_client.py, duplicated here (not imported
cross-skill) so this skill stays self-contained and installable on its own.

Auth: reads the API key from a file path (never accept it as a literal
argument or environment value typed in a chat message -- the user creates the
key file themselves in their own file manager). Sent as the
X-Integration-Api-Key header -- confirmed directly against the live RM API
reference at api.usewheelhouse.com/wheelhouse_rm_api ("send an RM API key in
the X-Integration-Api-Key header... a single key that authenticates both the
integration and user context -- no separate user key is required").

Base URL, rate limit (60 req/min, rolling one-minute window, 429 on breach),
and pagination (page 1-based or offset 0-based -- never both -- per_page up
to 100, stop when a page returns fewer than per_page) are all confirmed
directly against that same live reference. /listings and its query params
(exclude_inactive default true, include_managed_listings default false) are
confirmed too.

/listings/{listing_id}/price_calendar -- confirmed directly against the
connected Wheelhouse MCP's live tool schema and a real test call against a
real account on 2026-08-04: requires listing_id (path) + channel (query),
accepts optional start_date/end_date (YYYY-MM-DD). When start_date/end_date
are omitted the API defaults to today through its maximum calendar horizon
(1.5 years out); the total requested range (start_date to end_date) may not
exceed 3 years. Confirmed real response is a list of per-stay-date rows, one
row per unit per date for multi-unit listings, with fields: stay_date,
price, currency, is_available, is_booked, block_time, reservation_id,
created_at, unit_number. No pagination params on this endpoint -- the whole
requested range comes back in one call.
"""
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.usewheelhouse.com/ss_api/v1"

# 60 req/min confirmed current limit. Pace at ~50/min (1.2s between calls) to
# leave headroom for retries and any other concurrent use of the same key.
SECONDS_BETWEEN_CALLS = 1.2
MAX_BACKOFF_SECONDS = 60


def load_api_key(key_file_path):
    if not os.path.exists(key_file_path):
        sys.exit(
            f"API key file not found at {key_file_path}. Create it yourself "
            f"(one line, just the key, no quotes) -- this script will never "
            f"print its contents, and you should never paste the key into a "
            f"chat message."
        )
    with open(key_file_path, "r") as f:
        key = f.read().strip()
    if not key:
        sys.exit(f"API key file at {key_file_path} is empty.")
    return key


class WheelhouseClient:
    def __init__(self, api_key, verbose=False):
        self.api_key = api_key
        self.verbose = verbose
        self._last_call = 0.0

    def _pace(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < SECONDS_BETWEEN_CALLS:
            time.sleep(SECONDS_BETWEEN_CALLS - elapsed)
        self._last_call = time.monotonic()

    def get(self, path, params=None):
        """GET a path relative to BASE_URL. Returns parsed JSON.
        Raises RuntimeError with a clear message on non-2xx after retries."""
        params = params or {}
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{BASE_URL}{path}"
        if query:
            url += f"?{query}"

        backoff = 1.0
        attempt = 0
        while True:
            attempt += 1
            self._pace()
            req = urllib.request.Request(
                url, headers={"X-Integration-Api-Key": self.api_key, "Accept": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read()
                    return json.loads(body) if body else None
            except urllib.error.HTTPError as e:
                body_text = e.read().decode("utf-8", errors="replace")
                if e.code == 429:
                    if self.verbose:
                        print(f"  429 rate-limited on {path}, backing off {backoff:.1f}s", file=sys.stderr)
                    time.sleep(min(backoff, MAX_BACKOFF_SECONDS) + random.uniform(0, 0.5))
                    backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
                    if attempt <= 6:
                        continue
                    raise RuntimeError(f"429 persisted after {attempt} attempts on {url}: {body_text}")
                if e.code == 401:
                    raise RuntimeError(
                        f"401 Unauthorized on {url} -- API key missing/invalid. "
                        f"Check the key file has no extra spaces/newlines and hasn't been revoked."
                    )
                if e.code == 403:
                    raise RuntimeError(
                        f"403 Forbidden on {url} -- key is valid but not scoped to this "
                        f"resource. Body: {body_text}"
                    )
                if e.code == 404:
                    raise RuntimeError(
                        f"404 Not Found on {url} -- likely an incorrect endpoint path. "
                        f"Body: {body_text}"
                    )
                if e.code == 422:
                    raise RuntimeError(f"422 Unprocessable Entity on {url}: {body_text}")
                raise RuntimeError(f"HTTP {e.code} on {url}: {body_text}")
            except urllib.error.URLError as e:
                if attempt <= 3:
                    time.sleep(2 * attempt)
                    continue
                raise RuntimeError(f"Network error calling {url}: {e}")

    def get_paginated(self, path, params=None, per_page=100):
        """Yields items across all pages of a list endpoint."""
        params = dict(params or {})
        params["per_page"] = per_page
        page = 1
        while True:
            params["page"] = page
            batch = self.get(path, params)
            items = batch if isinstance(batch, list) else batch.get("data", batch.get("result", []))
            if not items:
                return
            for item in items:
                yield item
            if len(items) < per_page:
                return
            page += 1
