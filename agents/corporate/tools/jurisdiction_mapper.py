"""jurisdiction_mapper — maps ISO country codes to FATF risk tiers."""

# FATF risk classification (simplified, based on public FATF lists)
FATF_HIGH_RISK = {
    "KP", "IR",                                          # FATF blacklist (public)
    "PA", "KY", "BVI", "VG", "AI", "TC", "VU", "WS",   # Common offshore (grey area)
    "SY", "YE", "SD", "LY", "SO", "MM", "PK", "HT",
}
FATF_MEDIUM_RISK = {
    "NG", "KE", "ZA", "MA", "TN", "GH", "TZ",
    "PH", "VN", "ID", "TH", "KH",
    "UA", "MD", "BY", "AL", "BA",
}

async def jurisdiction_mapper(country_code: str) -> dict:
    code = (country_code or "").upper().strip()
    if not code:
        return {"country_code": code, "fatf_risk_tier": "unknown", "special_measures": []}

    if code in FATF_HIGH_RISK:
        tier = "high"
        measures = ["Enhanced Due Diligence required", "FATF special measures may apply"]
    elif code in FATF_MEDIUM_RISK:
        tier = "medium"
        measures = ["Elevated monitoring recommended"]
    else:
        tier = "low"
        measures = []

    return {
        "country_code":    code,
        "fatf_risk_tier":  tier,
        "special_measures":measures,
    }
