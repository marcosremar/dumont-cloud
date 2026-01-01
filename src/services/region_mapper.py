"""
Region Mapper Service for Multi-Region GPU Instance Management.

This module provides utilities for parsing Vast.ai geolocation strings
and mapping them to standardized region identifiers. It supports:
- Parsing geolocation strings like "US, California" into structured data
- Mapping to GCP zones for consistency with existing infrastructure
- Identifying EU regions for GDPR compliance
- Country and continent classification
"""

import logging
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# EU countries for GDPR compliance tagging
EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # Also include EEA countries
    "IS", "LI", "NO",
    # UK (post-Brexit, still relevant for data protection)
    "GB", "UK",
}

# Country code to full name mapping
COUNTRY_CODES = {
    # Americas
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",

    # Europe
    "DE": "Germany",
    "FR": "France",
    "GB": "United Kingdom",
    "UK": "United Kingdom",
    "NL": "Netherlands",
    "BE": "Belgium",
    "ES": "Spain",
    "IT": "Italy",
    "PL": "Poland",
    "CZ": "Czechia",
    "AT": "Austria",
    "CH": "Switzerland",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "DK": "Denmark",
    "IE": "Ireland",
    "PT": "Portugal",
    "RO": "Romania",
    "BG": "Bulgaria",
    "HU": "Hungary",
    "GR": "Greece",
    "HR": "Croatia",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "LT": "Lithuania",
    "LV": "Latvia",
    "EE": "Estonia",
    "LU": "Luxembourg",
    "MT": "Malta",
    "CY": "Cyprus",
    "IS": "Iceland",
    "LI": "Liechtenstein",
    "RU": "Russia",
    "UA": "Ukraine",
    "BY": "Belarus",

    # Asia
    "JP": "Japan",
    "KR": "South Korea",
    "CN": "China",
    "TW": "Taiwan",
    "HK": "Hong Kong",
    "SG": "Singapore",
    "IN": "India",
    "TH": "Thailand",
    "VN": "Vietnam",
    "ID": "Indonesia",
    "MY": "Malaysia",
    "PH": "Philippines",
    "PK": "Pakistan",
    "BD": "Bangladesh",
    "AE": "United Arab Emirates",
    "IL": "Israel",
    "SA": "Saudi Arabia",
    "TR": "Turkey",

    # Oceania
    "AU": "Australia",
    "NZ": "New Zealand",

    # Africa
    "ZA": "South Africa",
    "EG": "Egypt",
    "NG": "Nigeria",
    "KE": "Kenya",
}

# Full name to country code mapping (reverse lookup)
COUNTRY_NAMES_TO_CODES = {v.lower(): k for k, v in COUNTRY_CODES.items()}
# Add common variations
COUNTRY_NAMES_TO_CODES.update({
    "united states": "US",
    "usa": "US",
    "united kingdom": "GB",
    "britain": "GB",
    "great britain": "GB",
    "holland": "NL",
    "czech republic": "CZ",
    "south korea": "KR",
    "korea": "KR",
    "republic of korea": "KR",
})

# Continent mapping
COUNTRY_TO_CONTINENT = {
    # Americas
    "US": "NA", "CA": "NA", "MX": "NA",
    "BR": "SA", "AR": "SA", "CL": "SA", "CO": "SA",

    # Europe
    "DE": "EU", "FR": "EU", "GB": "EU", "UK": "EU", "NL": "EU", "BE": "EU",
    "ES": "EU", "IT": "EU", "PL": "EU", "CZ": "EU", "AT": "EU", "CH": "EU",
    "SE": "EU", "NO": "EU", "FI": "EU", "DK": "EU", "IE": "EU", "PT": "EU",
    "RO": "EU", "BG": "EU", "HU": "EU", "GR": "EU", "HR": "EU", "SK": "EU",
    "SI": "EU", "LT": "EU", "LV": "EU", "EE": "EU", "LU": "EU", "MT": "EU",
    "CY": "EU", "IS": "EU", "LI": "EU", "RU": "EU", "UA": "EU", "BY": "EU",

    # Asia
    "JP": "AS", "KR": "AS", "CN": "AS", "TW": "AS", "HK": "AS", "SG": "AS",
    "IN": "AS", "TH": "AS", "VN": "AS", "ID": "AS", "MY": "AS", "PH": "AS",
    "PK": "AS", "BD": "AS", "AE": "AS", "IL": "AS", "SA": "AS", "TR": "AS",

    # Oceania
    "AU": "OC", "NZ": "OC",

    # Africa
    "ZA": "AF", "EG": "AF", "NG": "AF", "KE": "AF",
}

CONTINENT_NAMES = {
    "NA": "North America",
    "SA": "South America",
    "EU": "Europe",
    "AS": "Asia",
    "OC": "Oceania",
    "AF": "Africa",
    "AN": "Antarctica",
}

# US state abbreviations
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

# Reverse lookup for state names
US_STATE_NAMES_TO_ABBREV = {v.lower(): k for k, v in US_STATES.items()}


@dataclass
class ParsedGeolocation:
    """Structured representation of a parsed geolocation."""
    raw: str
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    continent_code: Optional[str] = None
    continent_name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    is_eu: bool = False
    region_id: Optional[str] = None  # Standardized region identifier

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "raw": self.raw,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "continent_code": self.continent_code,
            "continent_name": self.continent_name,
            "state": self.state,
            "city": self.city,
            "is_eu": self.is_eu,
            "region_id": self.region_id,
        }


class RegionMapper:
    """
    Maps Vast.ai geolocation strings to standardized region identifiers.

    Vast.ai returns geolocation in various formats:
    - "US, California"
    - "Texas, US"
    - "Germany"
    - "DE"
    - "Poland, EU"
    - "Warsaw, PL"

    This class normalizes these into structured ParsedGeolocation objects.
    """

    def __init__(self):
        """Initialize the RegionMapper with lookup tables."""
        self._country_codes = COUNTRY_CODES
        self._country_names = COUNTRY_NAMES_TO_CODES
        self._eu_countries = EU_COUNTRIES
        self._continents = COUNTRY_TO_CONTINENT
        self._us_states = US_STATES
        self._us_state_names = US_STATE_NAMES_TO_ABBREV

    def parse_geolocation(self, geolocation: str) -> Optional[ParsedGeolocation]:
        """
        Parse a Vast.ai geolocation string into structured data.

        Args:
            geolocation: Raw geolocation string from Vast.ai API

        Returns:
            ParsedGeolocation object or None if parsing fails
        """
        if not geolocation or not isinstance(geolocation, str):
            return None

        geolocation = geolocation.strip()
        if not geolocation:
            return None

        result = ParsedGeolocation(raw=geolocation)

        # Split by comma and clean up parts
        parts = [p.strip() for p in geolocation.split(",")]
        parts = [p for p in parts if p]  # Remove empty parts

        if not parts:
            return None

        # Try to identify country code and location from parts
        country_code = None
        state = None
        city = None

        for i, part in enumerate(parts):
            part_upper = part.upper()
            part_lower = part.lower()

            # Check if it's a country code (2 letters)
            if len(part) == 2 and part_upper in self._country_codes:
                country_code = part_upper
                continue

            # Check if it's a full country name
            if part_lower in self._country_names:
                country_code = self._country_names[part_lower]
                continue

            # Check if it's a US state
            if part_upper in self._us_states:
                state = self._us_states[part_upper]
                if not country_code:
                    country_code = "US"
                continue

            if part_lower in self._us_state_names:
                state = part
                if not country_code:
                    country_code = "US"
                continue

            # Otherwise, treat as city or region name
            if not city:
                city = part
            elif not state:
                state = part

        # If we still don't have a country, try common patterns
        if not country_code:
            country_code = self._infer_country_from_geolocation(geolocation)

        if country_code:
            result.country_code = country_code
            result.country_name = self._country_codes.get(country_code)
            result.continent_code = self._continents.get(country_code)
            if result.continent_code:
                result.continent_name = CONTINENT_NAMES.get(result.continent_code)
            result.is_eu = country_code in self._eu_countries

        result.state = state
        result.city = city

        # Generate standardized region ID
        result.region_id = self._generate_region_id(result)

        return result

    def _infer_country_from_geolocation(self, geolocation: str) -> Optional[str]:
        """
        Try to infer country code from geolocation string using heuristics.

        Args:
            geolocation: Raw geolocation string

        Returns:
            Country code or None
        """
        geo_lower = geolocation.lower()

        # Check for explicit country mentions
        for name, code in self._country_names.items():
            if name in geo_lower:
                return code

        # Check for US state names (implies US)
        for state_name in self._us_state_names.keys():
            if state_name in geo_lower:
                return "US"

        # Check for common city names and their countries
        city_to_country = {
            "london": "GB", "manchester": "GB", "birmingham": "GB",
            "paris": "FR", "lyon": "FR", "marseille": "FR",
            "berlin": "DE", "munich": "DE", "frankfurt": "DE", "hamburg": "DE",
            "amsterdam": "NL", "rotterdam": "NL",
            "warsaw": "PL", "krakow": "PL", "wroclaw": "PL",
            "prague": "CZ", "brno": "CZ",
            "vienna": "AT", "zurich": "CH", "geneva": "CH",
            "stockholm": "SE", "oslo": "NO", "helsinki": "FI", "copenhagen": "DK",
            "dublin": "IE", "lisbon": "PT", "madrid": "ES", "barcelona": "ES",
            "rome": "IT", "milan": "IT",
            "tokyo": "JP", "osaka": "JP",
            "seoul": "KR", "busan": "KR",
            "singapore": "SG",
            "sydney": "AU", "melbourne": "AU",
            "toronto": "CA", "montreal": "CA", "vancouver": "CA",
            "sao paulo": "BR", "rio": "BR",
        }

        for city, code in city_to_country.items():
            if city in geo_lower:
                return code

        return None

    def _generate_region_id(self, parsed: ParsedGeolocation) -> Optional[str]:
        """
        Generate a standardized region ID from parsed geolocation.

        Format: {continent}-{country}[-{state}]
        Examples: "na-us-ca", "eu-de", "as-jp"

        Args:
            parsed: ParsedGeolocation object

        Returns:
            Standardized region ID or None
        """
        if not parsed.country_code:
            return None

        parts = []

        # Add continent prefix
        if parsed.continent_code:
            parts.append(parsed.continent_code.lower())

        # Add country code
        parts.append(parsed.country_code.lower())

        # Add state abbreviation for US
        if parsed.country_code == "US" and parsed.state:
            state_lower = parsed.state.lower()
            if state_lower in self._us_state_names:
                parts.append(self._us_state_names[state_lower].lower())

        return "-".join(parts) if parts else None

    def is_eu_region(self, geolocation: str) -> bool:
        """
        Check if a geolocation is in an EU/GDPR-compliant region.

        Args:
            geolocation: Raw geolocation string

        Returns:
            True if the region is in the EU/EEA
        """
        parsed = self.parse_geolocation(geolocation)
        return parsed.is_eu if parsed else False

    def get_country_code(self, geolocation: str) -> Optional[str]:
        """
        Extract country code from a geolocation string.

        Args:
            geolocation: Raw geolocation string

        Returns:
            Two-letter country code or None
        """
        parsed = self.parse_geolocation(geolocation)
        return parsed.country_code if parsed else None

    def get_region_id(self, geolocation: str) -> Optional[str]:
        """
        Get standardized region ID from a geolocation string.

        Args:
            geolocation: Raw geolocation string

        Returns:
            Standardized region ID or None
        """
        parsed = self.parse_geolocation(geolocation)
        return parsed.region_id if parsed else None

    def normalize_region_filter(self, region: str) -> List[str]:
        """
        Normalize a region filter to a list of search patterns.

        This handles various region filter formats:
        - Country codes: "US", "DE"
        - Continent codes: "EU", "NA"
        - Region names: "Europe", "North America"
        - State/city names: "California", "Texas"

        Args:
            region: Region filter string

        Returns:
            List of patterns to match against geolocation strings
        """
        patterns = []
        region_upper = region.upper()
        region_lower = region.lower()

        # Check if it's a country code
        if len(region) == 2 and region_upper in self._country_codes:
            patterns.append(region_upper)
            patterns.append(self._country_codes[region_upper])
            return patterns

        # Check if it's a continent code (EU, NA, SA, AS, OC, AF)
        continent_countries = {
            "EU": ["DE", "FR", "GB", "UK", "NL", "BE", "ES", "IT", "PL", "CZ",
                   "AT", "CH", "SE", "NO", "FI", "DK", "IE", "PT", "RO", "BG",
                   "HU", "GR", "HR", "SK", "SI", "LT", "LV", "EE", "LU"],
            "NA": ["US", "CA", "MX"],
            "SA": ["BR", "AR", "CL", "CO"],
            "AS": ["JP", "KR", "CN", "TW", "HK", "SG", "IN", "TH", "VN", "ID"],
            "OC": ["AU", "NZ"],
            "AF": ["ZA", "EG", "NG", "KE"],
        }

        if region_upper in continent_countries:
            for code in continent_countries[region_upper]:
                patterns.append(code)
                if code in self._country_codes:
                    patterns.append(self._country_codes[code])
            return patterns

        # Check if it's a country name
        if region_lower in self._country_names:
            code = self._country_names[region_lower]
            patterns.append(code)
            patterns.append(region)
            return patterns

        # Check if it's a US state
        if region_upper in self._us_states:
            patterns.append(region_upper)
            patterns.append(self._us_states[region_upper])
            patterns.append("US")
            return patterns

        if region_lower in self._us_state_names:
            patterns.append(region)
            patterns.append(self._us_state_names[region_lower])
            patterns.append("US")
            return patterns

        # Check for continent names
        continent_name_to_code = {
            "europe": "EU",
            "north america": "NA",
            "south america": "SA",
            "asia": "AS",
            "oceania": "OC",
            "africa": "AF",
        }

        if region_lower in continent_name_to_code:
            continent_code = continent_name_to_code[region_lower]
            return self.normalize_region_filter(continent_code)

        # Default: return the original string as-is for partial matching
        patterns.append(region)
        return patterns

    def match_geolocation_to_region(
        self,
        geolocation: str,
        region_filter: str
    ) -> bool:
        """
        Check if a geolocation matches a region filter.

        Args:
            geolocation: Raw geolocation string from Vast.ai
            region_filter: Region filter to match against

        Returns:
            True if the geolocation matches the filter
        """
        if not geolocation or not region_filter:
            return False

        patterns = self.normalize_region_filter(region_filter)
        geolocation_upper = geolocation.upper()

        for pattern in patterns:
            if pattern.upper() in geolocation_upper:
                return True

        return False

    def get_compliance_tags(self, geolocation: str) -> List[str]:
        """
        Get compliance tags for a geolocation.

        Args:
            geolocation: Raw geolocation string

        Returns:
            List of compliance tags (e.g., ["GDPR", "EU_DATA_RESIDENCY"])
        """
        parsed = self.parse_geolocation(geolocation)
        tags = []

        if parsed and parsed.is_eu:
            tags.append("GDPR")
            tags.append("EU_DATA_RESIDENCY")

        if parsed and parsed.country_code == "US":
            tags.append("CCPA")  # California Consumer Privacy Act (may apply)

        return tags

    def get_all_regions(self) -> Dict[str, Dict]:
        """
        Get all known regions with metadata.

        Returns:
            Dictionary of region_id -> region metadata
        """
        regions = {}

        for code, name in self._country_codes.items():
            continent_code = self._continents.get(code)
            region_id = f"{continent_code.lower()}-{code.lower()}" if continent_code else code.lower()

            regions[region_id] = {
                "region_id": region_id,
                "country_code": code,
                "country_name": name,
                "continent_code": continent_code,
                "continent_name": CONTINENT_NAMES.get(continent_code),
                "is_eu": code in self._eu_countries,
                "compliance_tags": ["GDPR", "EU_DATA_RESIDENCY"] if code in self._eu_countries else [],
            }

        return regions


# Singleton instance
_region_mapper: Optional[RegionMapper] = None


def get_region_mapper() -> RegionMapper:
    """
    Get the global RegionMapper instance.

    Returns:
        RegionMapper singleton instance
    """
    global _region_mapper

    if _region_mapper is None:
        _region_mapper = RegionMapper()

    return _region_mapper
