# ResellerXpress dealer prices: capacity (MB) -> dealer/API cost (GHS).
#
# These are SEED/FALLBACK values only. ResellerXpress is the source of truth:
# the /plans sync (app/plans_sync.py) overwrites cost_price_ghs and sets
# provider_plan_id from the live API. Prices below mirror the integration docs
# (documentation/resellerxpress_bundle_integration_docs.md, section 7) so a fresh
# install has sensible defaults before the first sync runs.
#
# Network names here are our INTERNAL display names (title-case). The lowercase
# codes the provider expects are mapped via PROVIDER_NETWORK_CODES below.

MTN_BUNDLES = {
    1000: 4.00,    # 1 GB
    2000: 8.75,    # 2 GB
    3000: 13.30,   # 3 GB
    4000: 17.00,   # 4 GB
    5000: 20.90,   # 5 GB
    6000: 24.80,   # 6 GB
    8000: 32.50,   # 8 GB
    10000: 39.80,  # 10 GB
    15000: 58.00,  # 15 GB
    20000: 77.00,  # 20 GB
    25000: 96.50,  # 25 GB
    30000: 116.50, # 30 GB
    40000: 154.50, # 40 GB
    50000: 185.50, # 50 GB
    100000: 360.00, # 100 GB
}

AIRTELTIGO_BUNDLES = {
    1000: 5.80,    # 1 GB
    2000: 9.60,    # 2 GB
    3000: 13.50,   # 3 GB
    4000: 17.30,   # 4 GB
    5000: 21.20,   # 5 GB
    6000: 25.00,   # 6 GB
    7000: 29.00,   # 7 GB
    8000: 32.80,   # 8 GB
    10000: 40.30,  # 10 GB
    15000: 59.00,  # 15 GB
    20000: 78.00,  # 20 GB
}

TELECEL_BUNDLES = {
    10000: 39.00,  # 10 GB
    15000: 55.00,  # 15 GB
    20000: 74.00,  # 20 GB
    25000: 91.00,  # 25 GB
    30000: 108.00, # 30 GB
    40000: 143.00, # 40 GB
    50000: 178.00, # 50 GB
    100000: 350.00, # 100 GB
}

# Internal display name -> capacity/cost map.
BUNDLES_BY_NETWORK = {
    "MTN": MTN_BUNDLES,
    "AirtelTigo": AIRTELTIGO_BUNDLES,
    "Telecel": TELECEL_BUNDLES,
}

# Internal display name -> ResellerXpress network code (used for /plans filter
# and to match synced plans back to our bundles).
PROVIDER_NETWORK_CODES = {
    "MTN": "mtn",
    "AIRTELTIGO": "airteltigo",
    "TELECEL": "telecel",
}

# Reverse map: provider code -> internal display name.
INTERNAL_NETWORK_NAMES = {
    "mtn": "MTN",
    "airteltigo": "AirtelTigo",
    "telecel": "Telecel",
}


def provider_network_code(network: str) -> str | None:
    """Map our internal network name to the ResellerXpress code, or None if unknown."""
    if not network:
        return None
    return PROVIDER_NETWORK_CODES.get(network.upper())


def internal_network_name(provider_code: str) -> str | None:
    """Map a ResellerXpress network code back to our internal display name."""
    if not provider_code:
        return None
    return INTERNAL_NETWORK_NAMES.get(provider_code.strip().lower())


def get_cost_price(network: str, capacity: int) -> float | None:
    """Return dealer cost price for this network and capacity, or None if not supported."""
    if not network:
        return None
    # Case-insensitive lookup so "Telecel" / "TELECEL" both match.
    network_upper = network.upper()
    bundles = next((v for k, v in BUNDLES_BY_NETWORK.items() if k.upper() == network_upper), None)
    if not bundles:
        return None
    return bundles.get(capacity)


def get_selling_price(network: str, capacity: int, markup_ghs: float = 1.0) -> float | None:
    """Selling price = cost + markup. Returns None if bundle not supported."""
    cost = get_cost_price(network, capacity)
    if cost is None:
        return None
    return round(cost + markup_ghs, 2)


def is_supported(network: str, capacity: int) -> bool:
    """True if this network + capacity exists in the seed price list."""
    return get_cost_price(network, capacity) is not None


# Legacy names for compatibility.
def calculate_bundle_price(network: str, capacity: int) -> float:
    """Dealer cost price; 0 if not supported."""
    return get_cost_price(network, capacity) or 0.0


def calculate_selling_price(network: str, capacity: int, markup_ghs: float = 1.0) -> float:
    """Selling price = cost + markup; 0 if not supported."""
    return get_selling_price(network, capacity, markup_ghs) or 0.0
