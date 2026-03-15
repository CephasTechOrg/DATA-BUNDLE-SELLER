# GHDataConnect supported bundles: capacity (MB) -> cost price (GHS)
# From their portal – only these sizes are accepted by their API.
MTN_BUNDLES = {
    1000: 3.90,   # 1 GB
    2000: 7.90,   # 2 GB
    3000: 11.80,  # 3 GB
    4000: 15.90,  # 4 GB
    5000: 19.90,  # 5 GB
    6000: 23.70,  # 6 GB
    8000: 31.80,  # 8 GB
    10000: 38.90,  # 10 GB
    15000: 57.20,  # 15 GB
    20000: 76.20,  # 20 GB
    25000: 96.20,  # 25 GB
    30000: 116.50,  # 30 GB
    40000: 153.00,  # 40 GB
    50000: 193.00,  # 50 GB
}

# Telecel: GHDataConnect supported bundles (capacity MB -> cost GHS from their portal)
TELECEL_BUNDLES = {
    2000: 9.00,    # 2 GB
    3000: 13.40,   # 3 GB
    5000: 18.90,   # 5 GB
    10000: 35.90,  # 10 GB
    15000: 52.90,  # 15 GB
    20000: 70.00,  # 20 GB
    25000: 86.00,  # 25 GB
    30000: 103.00, # 30 GB
    35000: 122.00, # 35 GB
    40000: 137.00, # 40 GB
    50000: 171.00, # 50 GB
    100000: 345.00, # 100 GB
}

# Networks: both MTN and Telecel; capacity sent to GHDataConnect as per their API (MB).
BUNDLES_BY_NETWORK = {
    "MTN": MTN_BUNDLES,
    "Telecel": TELECEL_BUNDLES,
}




def get_cost_price(network: str, capacity: int) -> float | None:
    """Return GHDataConnect cost price for this network and capacity, or None if not supported."""
    if not network:
        return None
    # Case-insensitive lookup so "Telecel" / "TELECEL" both match
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
    """True if GHDataConnect supports this network + capacity."""
    return get_cost_price(network, capacity) is not None


# Legacy names for compatibility (used in webhook for wallet check)
def calculate_bundle_price(network: str, capacity: int) -> float:
    """Cost price from GHDataConnect; 0 if not supported."""
    return get_cost_price(network, capacity) or 0.0


def calculate_selling_price(network: str, capacity: int, markup_ghs: float = 1.0) -> float:
    """Selling price = cost + markup; 0 if not supported."""
    return get_selling_price(network, capacity, markup_ghs) or 0.0
