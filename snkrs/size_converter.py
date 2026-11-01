"""
Comprehensive Sneaker Size Conversion Utility.
Supports US Men, US Women, EU, UK, and CM measurements for major brands (Nike, Jordan, Adidas, New Balance).
"""

from typing import Dict, Any, Optional, Tuple
import re
from .models import SizeSystem


# Nike & Jordan standard conversion mapping (US Men base)
NIKE_MENS_CHART = [
    {"us_m": 4.0, "us_w": 5.5, "eu": 36.0, "uk": 3.5, "cm": 23.0},
    {"us_m": 4.5, "us_w": 6.0, "eu": 36.5, "uk": 4.0, "cm": 23.5},
    {"us_m": 5.0, "us_w": 6.5, "eu": 37.5, "uk": 4.5, "cm": 23.5},
    {"us_m": 5.5, "us_w": 7.0, "eu": 38.0, "uk": 5.0, "cm": 24.0},
    {"us_m": 6.0, "us_w": 7.5, "eu": 38.5, "uk": 5.5, "cm": 24.0},
    {"us_m": 6.5, "us_w": 8.0, "eu": 39.0, "uk": 6.0, "cm": 24.5},
    {"us_m": 7.0, "us_w": 8.5, "eu": 40.0, "uk": 6.0, "cm": 25.0},
    {"us_m": 7.5, "us_w": 9.0, "eu": 40.5, "uk": 6.5, "cm": 25.5},
    {"us_m": 8.0, "us_w": 9.5, "eu": 41.0, "uk": 7.0, "cm": 26.0},
    {"us_m": 8.5, "us_w": 10.0, "eu": 42.0, "uk": 7.5, "cm": 26.5},
    {"us_m": 9.0, "us_w": 10.5, "eu": 42.5, "uk": 8.0, "cm": 27.0},
    {"us_m": 9.5, "us_w": 11.0, "eu": 43.0, "uk": 8.5, "cm": 27.5},
    {"us_m": 10.0, "us_w": 11.5, "eu": 44.0, "uk": 9.0, "cm": 28.0},
    {"us_m": 10.5, "us_w": 12.0, "eu": 44.5, "uk": 9.5, "cm": 28.5},
    {"us_m": 11.0, "us_w": 12.5, "eu": 45.0, "uk": 10.0, "cm": 29.0},
    {"us_m": 11.5, "us_w": 13.0, "eu": 45.5, "uk": 10.5, "cm": 29.5},
    {"us_m": 12.0, "us_w": 13.5, "eu": 46.0, "uk": 11.0, "cm": 30.0},
    {"us_m": 12.5, "us_w": 14.0, "eu": 47.0, "uk": 11.5, "cm": 30.5},
    {"us_m": 13.0, "us_w": 14.5, "eu": 47.5, "uk": 12.0, "cm": 31.0},
    {"us_m": 14.0, "us_w": 15.5, "eu": 48.5, "uk": 13.0, "cm": 32.0},
    {"us_m": 15.0, "us_w": 16.5, "eu": 49.5, "uk": 14.0, "cm": 33.0},
]


class SizeConverter:
    """Parses any size string and normalizes it to US Men and EU formats."""

    @staticmethod
    def parse_size_string(size_input: str) -> Tuple[Optional[SizeSystem], Optional[float]]:
        """
        Extracts the system and numerical value from strings like:
        'US 10', '10 US', '44 EU', 'EU 42.5', 'UK 9.5', '10.5', '43'
        """
        raw = size_input.strip().upper()
        
        # Check explicit system prefix or suffix
        system = None
        if "US W" in raw or "WMNS" in raw or "WOMEN" in raw:
            system = SizeSystem.US_WOMEN
        elif "US" in raw or "MENS" in raw:
            system = SizeSystem.US_MEN
        elif "EU" in raw or "EUR" in raw:
            system = SizeSystem.EU
        elif "UK" in raw:
            system = SizeSystem.UK
        elif "CM" in raw:
            system = SizeSystem.CM

        # Extract number
        match = re.search(r"(\d+(\.\d+)?)", raw)
        if not match:
            return None, None
        
        val = float(match.group(1))

        # If system is not explicitly specified, infer from value range:
        # Sneaker sizes: EU is typically 35-50. US is typically 4-16.
        if system is None:
            if val >= 35.0:
                system = SizeSystem.EU
            else:
                system = SizeSystem.US_MEN  # default assumption in sneaker market is US Men
                
        return system, val

    @classmethod
    def normalize(cls, size_input: str) -> Dict[str, float]:
        """
        Takes any size input (e.g. '44', 'US 10', 'EU 42.5') and returns a dictionary with:
        {'us_m': 10.0, 'us_w': 11.5, 'eu': 44.0, 'uk': 9.0, 'cm': 28.0}
        """
        system, val = cls.parse_size_string(size_input)
        if val is None or system is None:
            # Fallback to standard US 10 / EU 44
            return {"us_m": 10.0, "us_w": 11.5, "eu": 44.0, "uk": 9.0, "cm": 28.0}

        # Find closest row in chart
        key_map = {
            SizeSystem.US_MEN: "us_m",
            SizeSystem.US_WOMEN: "us_w",
            SizeSystem.EU: "eu",
            SizeSystem.UK: "uk",
            SizeSystem.CM: "cm",
        }
        target_key = key_map[system]

        closest_entry = min(
            NIKE_MENS_CHART,
            key=lambda row: abs(row[target_key] - val)
        )
        return closest_entry.copy()

    @classmethod
    def format_all_sizes(cls, size_input: str) -> str:
        """Returns readable string representation: 'US 10M / EU 44 / UK 9'"""
        norm = cls.normalize(size_input)
        return f"US {norm['us_m']}M / EU {norm['eu']} / UK {norm['uk']}"
