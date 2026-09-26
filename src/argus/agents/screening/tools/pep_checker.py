"""pep_checker — checks the entity against the politically exposed persons in the data plane."""

from argus.data_plane import DataPlaneUnavailable, get_data_plane
from argus.utils.structured_logger import get_logger

logger = get_logger("tool.pep_checker")


async def pep_checker(entity_name: str, dob: str, nationality: str) -> dict:
    plane = get_data_plane()
    try:
        pep = await plane.entities.find_pep(entity_name)
    except DataPlaneUnavailable as exc:
        logger.warning("tool.fallback", extra={"tool": "pep_checker", "reason": str(exc)})
        return {"hit": False, "findings": [], "source": "fallback"}

    if not pep:
        return {"hit": False, "findings": [], "source": plane.backend}
    country = pep.get("country") or pep.get("nationality") or nationality
    return {
        "hit": True,
        "findings": [
            {
                "type": "pep",
                "match": (
                    f"{pep.get('name')} — {pep.get('role', 'Unknown role')} "
                    f"({country}, {pep.get('period', 'Unknown period')})"
                ),
                "confidence": 0.92,
                "source": f"{plane.backend}_entities",
            }
        ],
        "source": plane.backend,
    }
