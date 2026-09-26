"""Where an agent's result came from, recorded on every agent response.

- `computed`: every tool the agent ran answered from the configured data plane.
- `fallback`: at least one tool's service was unavailable, so that tool returned a result that
  asserts nothing. `fallbacks` names those tools.
- `demo_profile`: the result is a recorded demo scenario, not computed.
- `unavailable`: the agent itself could not be reached, so there is no result.
"""

COMPUTED = "computed"
FALLBACK = "fallback"
DEMO_PROFILE = "demo_profile"
UNAVAILABLE = "unavailable"


def provenance(**tool_results: dict) -> dict:
    fallbacks = sorted(name for name, r in tool_results.items() if r.get("source") == FALLBACK)
    return {"source": FALLBACK if fallbacks else COMPUTED, "fallbacks": fallbacks}


def demo_provenance() -> dict:
    return {"source": DEMO_PROFILE, "fallbacks": []}
