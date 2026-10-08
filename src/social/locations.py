"""Named VVN coordinates used to replace dummy lat/lng on social videos."""

from __future__ import annotations

PLACES: dict[str, tuple[float, float]] = {
    "Nalasopara West": (19.418, 72.811),
    "Nalasopara East": (19.427, 72.848),
    "Nalasopara": (19.419, 72.817),
    "Virar West": (19.455, 72.808),
    "Virar East": (19.456, 72.842),
    "Virar": (19.456, 72.811),
    "Vasai West": (19.361, 72.805),
    "Vasai East": (19.381, 72.835),
    "Vasai": (19.391, 72.839),
    "Naigaon": (19.351, 72.846),
    "Pelhar": (19.448, 72.862),
    "Vasai-Virar": (19.420, 72.820),
}

# Places outside the project study area — keep the video, mark not-relevant.
OUTSIDE: dict[str, tuple[float, float]] = {
    "Khar, Mumbai": (19.072, 72.834),
    "Mumbai Airport": (19.089, 72.868),
    "Dahanu": (19.991, 72.739),
    "Palghar": (19.697, 72.766),
    "Mumbai": (19.076, 72.877),
}
