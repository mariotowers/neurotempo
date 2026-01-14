# neurotempo/brain/muse_scanner.py

from __future__ import annotations

from typing import List, Dict
from bleak import BleakScanner


def _looks_like_muse(name: str) -> bool:
    n = (name or "").strip().lower()
    return n.startswith("muse")


async def scan_nearby_muse(timeout_s: float = 4.0) -> List[Dict]:
    found: dict[str, Dict] = {}

    devices = await BleakScanner.discover(timeout=timeout_s)

    for d in devices:
        name = (d.name or "").strip()
        if not name:
            md = getattr(d, "metadata", {}) or {}
            name = (md.get("local_name") or "").strip()

        if not _looks_like_muse(name):
            continue

        mac = d.address
        rssi = getattr(d, "rssi", None)

        prev = found.get(mac)
        if prev is None or (rssi is not None and (prev["rssi"] is None or rssi > prev["rssi"])):
            found[mac] = {"id": mac, "name": name or "Muse", "rssi": rssi}

    return sorted(found.values(), key=lambda x: (x["rssi"] is None, -(x["rssi"] or -999)))