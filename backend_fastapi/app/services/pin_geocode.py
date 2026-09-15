"""Approximate lat/lng for an India PIN code, for a map view — not a real geocoder.

India has no free, no-key postal geocoding API, so this looks up increasingly coarse
prefixes of the PIN against small built-in tables: exact 6-digit PINs we know precisely,
then the 3-digit sub-district prefix (city-level), then the 1-digit postal zone
(state-cluster level) as a last resort. Good enough to place a task on a map at roughly
the right city; not accurate enough for turn-by-turn or delivery routing.
"""

from __future__ import annotations

# Exact PINs used in the closed beta and other well-known ones — city-centre precision.
_EXACT: dict[str, tuple[float, float]] = {
    "248001": (30.3165, 78.0322),  # Dehradun
    "110001": (28.6139, 77.2090),  # New Delhi
    "560001": (12.9716, 77.5946),  # Bengaluru
}

# 3-digit prefix -> a representative city centroid for that postal sub-district.
_PREFIX3: dict[str, tuple[float, float]] = {
    "110": (28.6139, 77.2090),  # Delhi
    "121": (28.4595, 77.0266),  # Gurugram
    "122": (28.4595, 77.0266),  # Gurugram
    "201": (28.5355, 77.3910),  # Noida
    "160": (30.7333, 76.7794),  # Chandigarh
    "173": (31.1048, 77.1734),  # Shimla
    "180": (32.7266, 74.8570),  # Jammu
    "190": (34.0837, 74.7973),  # Srinagar
    "248": (30.3165, 78.0322),  # Dehradun
    "302": (26.9124, 75.7873),  # Jaipur
    "313": (24.5854, 73.7125),  # Udaipur
    "380": (23.0225, 72.5714),  # Ahmedabad
    "395": (21.1702, 72.8311),  # Surat
    "400": (19.0760, 72.8777),  # Mumbai
    "411": (18.5204, 73.8567),  # Pune
    "440": (21.1458, 79.0882),  # Nagpur
    "452": (22.7196, 75.8577),  # Indore
    "462": (23.2599, 77.4126),  # Bhopal
    "500": (17.3850, 78.4867),  # Hyderabad
    "520": (16.5062, 80.6480),  # Vijayawada
    "560": (12.9716, 77.5946),  # Bengaluru
    "570": (12.2958, 76.6394),  # Mysuru
    "600": (13.0827, 80.2707),  # Chennai
    "625": (9.9252, 78.1198),  # Madurai
    "641": (11.0168, 76.9558),  # Coimbatore
    "682": (9.9312, 76.2673),  # Kochi
    "695": (8.5241, 76.9366),  # Thiruvananthapuram
    "700": (22.5726, 88.3639),  # Kolkata
    "751": (20.2961, 85.8245),  # Bhubaneswar
    "781": (26.1445, 91.7362),  # Guwahati
    "800": (25.5941, 85.1376),  # Patna
    "834": (23.3441, 85.3096),  # Ranchi
    "500001": (17.3850, 78.4867),
}

# 1-digit postal zone -> a fallback point roughly in that zone (India has zones 1-8 + 9 APS).
_ZONE1: dict[str, tuple[float, float]] = {
    "1": (28.6139, 77.2090),  # Delhi / Haryana / Punjab / HP / J&K
    "2": (26.8467, 80.9462),  # UP / Uttarakhand
    "3": (26.9124, 75.7873),  # Rajasthan / Gujarat
    "4": (19.0760, 72.8777),  # Maharashtra / MP / Chhattisgarh / Goa
    "5": (17.3850, 78.4867),  # Telangana / AP / Karnataka
    "6": (13.0827, 80.2707),  # Tamil Nadu / Kerala / Puducherry
    "7": (22.5726, 88.3639),  # West Bengal / Odisha / NE states
    "8": (25.5941, 85.1376),  # Bihar / Jharkhand
    "9": (28.6139, 77.2090),  # Army Postal Service
}


def geocode_india_pin(pin: str | None) -> tuple[float, float] | None:
    """Best-effort (lat, lng) for a 6-digit India PIN, or None if it doesn't look like one."""
    if not pin:
        return None
    digits = "".join(c for c in pin if c.isdigit())
    if len(digits) != 6:
        return None
    if digits in _EXACT:
        return _EXACT[digits]
    if digits[:3] in _PREFIX3:
        return _PREFIX3[digits[:3]]
    if digits[0] in _ZONE1:
        return _ZONE1[digits[0]]
    return None
