"""
FASE 2: Geolocalização Automática para Mapeamento de Regiões
Detecta a zona GCP mais próxima via coordenadas geográficas e
fornece detecção de localização de usuário por IP.
"""

import requests
import math
import logging
import time
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# In-memory cache for IP geolocation to avoid rate limiting (50k/month on ipinfo.io)
# Cache entries expire after 24 hours
_ip_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
_CACHE_TTL_SECONDS = 86400  # 24 hours

# Coordenadas de todas as zonas GCP
GCP_ZONES_COORDINATES = {
    # AMERICAS
    'northamerica-northeast1-a': (45.5017, -73.5673),  # Montreal, Canada
    'northamerica-northeast2-a': (43.6532, -79.3832),  # Toronto, Canada
    'us-central1-a': (41.2619, -95.8608),  # Iowa, US
    'us-east1-a': (33.1960, -80.0131),  # South Carolina, US
    'us-east4-a': (37.4316, -78.6569),  # Virginia, US
    'us-east5-a': (39.0469, -77.4903),  # Ohio, US
    'us-south1-a': (32.7767, -96.7970),  # Dallas, Texas, US
    'us-west1-a': (45.6387, -121.1807),  # Oregon, US
    'us-west2-a': (34.0522, -118.2437),  # Los Angeles, US
    'us-west3-a': (43.8041, -111.7798),  # Utah, US
    'us-west4-a': (36.1699, -115.1398),  # Nevada, US
    'southamerica-east1-a': (-23.5505, -46.6333),  # São Paulo, Brazil
    'southamerica-west1-a': (-33.4489, -70.6693),  # Chile
    
    # EUROPE
    'europe-central2-a': (52.2297, 21.0122),  # Warsaw, Poland
    'europe-north1-a': (60.5693, 27.1878),  # Finland
    'europe-southwest1-a': (40.4168, -3.7038),  # Madrid, Spain
    'europe-west1-a': (50.4501, 3.8196),  # Belgium
    'europe-west2-a': (51.5074, -0.1278),  # London, UK
    'europe-west3-a': (50.1109, 8.6821),  # Frankfurt, Germany
    'europe-west4-a': (52.3676, 4.9041),  # Netherlands
    'europe-west6-a': (47.3769, 8.5417),  # Zurich, Switzerland
    'europe-west8-a': (45.4642, 9.1900),  # Milan, Italy
    'europe-west9-a': (48.8566, 2.3522),  # Paris, France
    'europe-west10-a': (52.5200, 13.4050),  # Berlin, Germany
    'europe-west12-a': (45.0781, 7.6761),  # Turin, Italy
    
    # ASIA
    'asia-east1-a': (24.0518, 120.5161),  # Taiwan
    'asia-east2-a': (22.3193, 114.1694),  # Hong Kong
    'asia-northeast1-a': (35.6762, 139.6503),  # Tokyo, Japan
    'asia-northeast2-a': (34.6937, 135.5023),  # Osaka, Japan
    'asia-northeast3-a': (37.5665, 126.9780),  # Seoul, South Korea
    'asia-south1-a': (19.0760, 72.8777),  # Mumbai, India
    'asia-south2-a': (28.7041, 77.1025),  # Delhi, India
    'asia-southeast1-a': (1.3521, 103.8198),  # Singapore
    'asia-southeast2-a': (-6.2088, 106.8456),  # Jakarta, Indonesia
    
    # OCEANIA
    'australia-southeast1-a': (-33.8688, 151.2093),  # Sydney, Australia
    'australia-southeast2-a': (-37.8136, 144.9631),  # Melbourne, Australia
    
    # MIDDLE EAST
    'me-central1-a': (25.2048, 55.2708),  # Dubai, UAE
    'me-west1-a': (32.0853, 34.7818),  # Tel Aviv, Israel
}


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calcula distância em km entre dois pontos usando fórmula de Haversine.
    
    Args:
        lat1, lng1: Coordenadas do ponto 1
        lat2, lng2: Coordenadas do ponto 2
        
    Returns:
        Distância em quilômetros
    """
    R = 6371  # Raio da Terra em km
    
    # Converter para radianos
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Diferenças
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    # Fórmula de Haversine
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def get_coordinates_from_ip(ip_address: str) -> Optional[Tuple[float, float]]:
    """
    Obtém coordenadas geográficas a partir de IP.
    
    Args:
        ip_address: Endereço IP da GPU
        
    Returns:
        Tupla (latitude, longitude) ou None se falhar
    """
    try:
        # Usar ipinfo.io (grátis até 50k requests/mês)
        response = requests.get(
            f'https://ipinfo.io/{ip_address}/json',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if 'loc' in data:
                # loc format: "latitude,longitude"
                lat, lng = map(float, data['loc'].split(','))
                
                city = data.get('city', 'Unknown')
                region = data.get('region', 'Unknown')
                country = data.get('country', 'Unknown')
                
                logger.info(f"📍 IP {ip_address} → {city}, {region}, {country} ({lat}, {lng})")
                
                return (lat, lng)
        
        logger.warning(f"⚠️  Falha ao obter localização do IP {ip_address}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao consultar geolocalização: {e}")
        return None


def find_closest_gcp_zone(lat: float, lng: float, max_distance_km: int = 10000) -> Tuple[Optional[str], float]:
    """
    Encontra a zona GCP mais próxima das coordenadas dadas.
    
    Args:
        lat: Latitude
        lng: Longitude
        max_distance_km: Distância máxima aceitável (default: 10000km)
        
    Returns:
        Tupla (zona, distância_km) ou (None, inf) se não encontrar
    """
    closest_zone = None
    min_distance = float('inf')
    
    for zone, (zone_lat, zone_lng) in GCP_ZONES_COORDINATES.items():
        distance = haversine_distance(lat, lng, zone_lat, zone_lng)
        
        if distance < min_distance:
            min_distance = distance
            closest_zone = zone
    
    if min_distance > max_distance_km:
        logger.warning(f"⚠️  Zona mais próxima está a {min_distance:.0f}km (limite: {max_distance_km}km)")
        return (None, min_distance)
    
    logger.info(f"✅ Zona mais próxima: {closest_zone} ({min_distance:.0f}km)")
    
    return (closest_zone, min_distance)


def get_gcp_zone_by_geolocation(ip_address: str) -> Tuple[Optional[str], float]:
    """
    Detecta zona GCP mais próxima usando geolocalização por IP.
    
    Esta é a CAMADA 2 do sistema de mapeamento.
    Usa quando REGION_MAP não tem a região.
    
    Args:
        ip_address: IP da GPU
        
    Returns:
        Tupla (zona, distância_km) ou (None, inf) se falhar
    """
    logger.info(f"🌍 Iniciando geolocalização para IP {ip_address}")
    
    # 1. Obter coordenadas do IP
    coords = get_coordinates_from_ip(ip_address)
    
    if not coords:
        logger.error("❌ Falha ao obter coordenadas")
        return (None, float('inf'))
    
    lat, lng = coords
    
    # 2. Encontrar zona GCP mais próxima
    zone, distance = find_closest_gcp_zone(lat, lng)
    
    if zone:
        logger.info(f"✅ Geolocalização: IP {ip_address} → {zone} ({distance:.0f}km)")
    else:
        logger.error(f"❌ Nenhuma zona GCP encontrada próxima")
    
    return (zone, distance)


@dataclass
class UserLocation:
    """
    Structured representation of a user's location detected from IP.

    This class provides all location data needed for region suggestions
    and GDPR compliance checks.
    """
    ip_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    region: Optional[str] = None  # State/Province
    country: Optional[str] = None
    country_code: Optional[str] = None
    continent: Optional[str] = None
    timezone: Optional[str] = None
    is_eu: bool = False
    nearest_gcp_zone: Optional[str] = None
    nearest_gcp_distance_km: Optional[float] = None
    suggested_regions: List[str] = None  # Top 3 closest region IDs

    def __post_init__(self):
        if self.suggested_regions is None:
            self.suggested_regions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return asdict(self)


# EU country codes for GDPR compliance detection
EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # EEA countries
    "IS", "LI", "NO",
    # UK (post-Brexit, still relevant for data protection)
    "GB", "UK",
}

# Continent mapping by country code
COUNTRY_TO_CONTINENT = {
    # Americas
    "US": "North America", "CA": "North America", "MX": "North America",
    "BR": "South America", "AR": "South America", "CL": "South America",
    "CO": "South America", "PE": "South America", "VE": "South America",
    # Europe
    "DE": "Europe", "FR": "Europe", "GB": "Europe", "UK": "Europe",
    "NL": "Europe", "BE": "Europe", "ES": "Europe", "IT": "Europe",
    "PL": "Europe", "CZ": "Europe", "AT": "Europe", "CH": "Europe",
    "SE": "Europe", "NO": "Europe", "FI": "Europe", "DK": "Europe",
    "IE": "Europe", "PT": "Europe", "RO": "Europe", "BG": "Europe",
    "HU": "Europe", "GR": "Europe", "HR": "Europe", "SK": "Europe",
    "SI": "Europe", "LT": "Europe", "LV": "Europe", "EE": "Europe",
    "LU": "Europe", "MT": "Europe", "CY": "Europe", "IS": "Europe",
    "LI": "Europe", "RU": "Europe", "UA": "Europe", "BY": "Europe",
    # Asia
    "JP": "Asia", "KR": "Asia", "CN": "Asia", "TW": "Asia", "HK": "Asia",
    "SG": "Asia", "IN": "Asia", "TH": "Asia", "VN": "Asia", "ID": "Asia",
    "MY": "Asia", "PH": "Asia", "PK": "Asia", "BD": "Asia", "AE": "Asia",
    "IL": "Asia", "SA": "Asia", "TR": "Asia",
    # Oceania
    "AU": "Oceania", "NZ": "Oceania",
    # Africa
    "ZA": "Africa", "EG": "Africa", "NG": "Africa", "KE": "Africa",
}


def _get_cached_location(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    Get cached location data for an IP address.

    Args:
        ip_address: IP address to look up

    Returns:
        Cached location data or None if not found/expired
    """
    if ip_address in _ip_cache:
        data, cached_at = _ip_cache[ip_address]
        if time.time() - cached_at < _CACHE_TTL_SECONDS:
            logger.debug(f"Cache hit for IP {ip_address}")
            return data
        else:
            # Expired, remove from cache
            del _ip_cache[ip_address]
    return None


def _set_cached_location(ip_address: str, data: Dict[str, Any]) -> None:
    """
    Cache location data for an IP address.

    Args:
        ip_address: IP address
        data: Location data to cache
    """
    _ip_cache[ip_address] = (data, time.time())
    logger.debug(f"Cached location for IP {ip_address}")


def _fetch_ip_location(ip_address: str) -> Optional[Dict[str, Any]]:
    """
    Fetch location data from ipinfo.io API.

    Args:
        ip_address: IP address to look up

    Returns:
        Raw API response data or None if failed
    """
    try:
        response = requests.get(
            f'https://ipinfo.io/{ip_address}/json',
            timeout=5
        )

        if response.status_code == 200:
            return response.json()

        logger.warning(f"ipinfo.io returned status {response.status_code} for IP {ip_address}")
        return None

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching location for IP {ip_address}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching location for IP {ip_address}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching location for IP {ip_address}: {e}")
        return None


def _find_closest_zones(lat: float, lng: float, count: int = 3) -> List[Tuple[str, float]]:
    """
    Find the N closest GCP zones to the given coordinates.

    Args:
        lat: Latitude
        lng: Longitude
        count: Number of zones to return

    Returns:
        List of (zone_name, distance_km) tuples sorted by distance
    """
    zones_with_distance = []

    for zone, (zone_lat, zone_lng) in GCP_ZONES_COORDINATES.items():
        distance = haversine_distance(lat, lng, zone_lat, zone_lng)
        zones_with_distance.append((zone, distance))

    # Sort by distance and return top N
    zones_with_distance.sort(key=lambda x: x[1])
    return zones_with_distance[:count]


def _zone_to_region_id(zone: str) -> str:
    """
    Convert a GCP zone name to a region ID.

    Args:
        zone: GCP zone name (e.g., 'us-east1-a')

    Returns:
        Region ID (e.g., 'na-us' for US zones)
    """
    # Map zone prefixes to region IDs
    zone_to_region = {
        'us-': 'na-us',
        'northamerica-': 'na-ca',
        'southamerica-': 'sa-br',
        'europe-': 'eu',
        'asia-east1': 'as-tw',
        'asia-east2': 'as-hk',
        'asia-northeast1': 'as-jp',
        'asia-northeast2': 'as-jp',
        'asia-northeast3': 'as-kr',
        'asia-south1': 'as-in',
        'asia-south2': 'as-in',
        'asia-southeast1': 'as-sg',
        'asia-southeast2': 'as-id',
        'australia-': 'oc-au',
        'me-central1': 'as-ae',
        'me-west1': 'as-il',
    }

    # Try exact matches first
    for prefix, region_id in zone_to_region.items():
        if zone.startswith(prefix):
            return region_id

    # Default to generic region based on zone name
    return zone.split('-')[0]


def get_user_location(ip_address: str) -> Optional[UserLocation]:
    """
    Detect user location from IP address for region suggestions.

    This function is used on first provisioning to suggest the nearest
    GPU region to the user. It includes caching to avoid exhausting
    the ipinfo.io free tier rate limit (50k requests/month).

    Args:
        ip_address: User's IP address (IPv4 or IPv6)

    Returns:
        UserLocation object with all location details, or None if detection fails

    Example:
        >>> loc = get_user_location('8.8.8.8')
        >>> if loc:
        ...     print(f"User in {loc.city}, {loc.country}")
        ...     print(f"Nearest region: {loc.suggested_regions[0]}")
    """
    if not ip_address:
        logger.warning("Empty IP address provided to get_user_location")
        return None

    # Clean up the IP address
    ip_address = ip_address.strip()

    # Handle localhost/private IPs - return a default location
    if ip_address in ('127.0.0.1', 'localhost', '::1'):
        logger.info(f"Localhost IP detected, returning default location")
        return UserLocation(
            ip_address=ip_address,
            city="Local",
            region="Local",
            country="Local",
            country_code="US",
            continent="North America",
            is_eu=False,
            suggested_regions=["na-us", "na-ca", "sa-br"],
        )

    logger.info(f"Detecting user location for IP {ip_address}")

    # Check cache first
    cached = _get_cached_location(ip_address)
    if cached is None:
        # Fetch from API
        cached = _fetch_ip_location(ip_address)
        if cached:
            _set_cached_location(ip_address, cached)

    if not cached:
        logger.error(f"Failed to get location data for IP {ip_address}")
        return None

    # Parse coordinates if available
    lat, lng = None, None
    if 'loc' in cached:
        try:
            lat, lng = map(float, cached['loc'].split(','))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse coordinates from: {cached.get('loc')}")

    # Determine country code and EU status
    country_code = cached.get('country', '').upper()
    is_eu = country_code in EU_COUNTRY_CODES
    continent = COUNTRY_TO_CONTINENT.get(country_code)

    # Find closest GCP zones and generate region suggestions
    nearest_zone = None
    nearest_distance = None
    suggested_regions = []

    if lat is not None and lng is not None:
        closest_zones = _find_closest_zones(lat, lng, count=5)
        if closest_zones:
            nearest_zone, nearest_distance = closest_zones[0]

            # Convert zones to region IDs and deduplicate
            seen_regions = set()
            for zone, _ in closest_zones:
                region_id = _zone_to_region_id(zone)
                if region_id not in seen_regions:
                    seen_regions.add(region_id)
                    suggested_regions.append(region_id)
                    if len(suggested_regions) >= 3:
                        break

    # If we couldn't get coordinates, suggest regions based on country
    if not suggested_regions:
        if country_code == "US":
            suggested_regions = ["na-us", "na-ca", "sa-br"]
        elif country_code == "CA":
            suggested_regions = ["na-ca", "na-us", "eu"]
        elif is_eu:
            suggested_regions = ["eu", "eu", "na-us"]
        elif country_code in ("JP", "KR"):
            suggested_regions = ["as-jp", "as-kr", "as-sg"]
        elif country_code in ("AU", "NZ"):
            suggested_regions = ["oc-au", "as-sg", "as-jp"]
        else:
            suggested_regions = ["na-us", "eu", "as-sg"]

    # Build the UserLocation object
    location = UserLocation(
        ip_address=ip_address,
        latitude=lat,
        longitude=lng,
        city=cached.get('city'),
        region=cached.get('region'),
        country=cached.get('country'),
        country_code=country_code,
        continent=continent,
        timezone=cached.get('timezone'),
        is_eu=is_eu,
        nearest_gcp_zone=nearest_zone,
        nearest_gcp_distance_km=round(nearest_distance, 1) if nearest_distance else None,
        suggested_regions=suggested_regions,
    )

    logger.info(
        f"User location detected: {location.city}, {location.country} "
        f"(EU: {location.is_eu}, suggestions: {location.suggested_regions})"
    )

    return location


def clear_location_cache() -> int:
    """
    Clear the IP location cache.

    Returns:
        Number of entries cleared
    """
    global _ip_cache
    count = len(_ip_cache)
    _ip_cache = {}
    logger.info(f"Cleared {count} entries from IP location cache")
    return count


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring.

    Returns:
        Dictionary with cache stats
    """
    now = time.time()
    valid_entries = sum(
        1 for _, (_, cached_at) in _ip_cache.items()
        if now - cached_at < _CACHE_TTL_SECONDS
    )

    return {
        "total_entries": len(_ip_cache),
        "valid_entries": valid_entries,
        "expired_entries": len(_ip_cache) - valid_entries,
        "ttl_seconds": _CACHE_TTL_SECONDS,
    }


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Testar com IP de Montreal
    test_ip = "142.44.215.177"  # Exemplo: IP do Quebec

    zone, distance = get_gcp_zone_by_geolocation(test_ip)

    if zone:
        print(f"\n✅ Resultado:")
        print(f"   IP: {test_ip}")
        print(f"   Zona GCP: {zone}")
        print(f"   Distância: {distance:.0f}km")
    else:
        print(f"\n❌ Falha ao detectar zona")

    # Test get_user_location
    print("\n--- Testing get_user_location ---")

    # Test with Google's public DNS IP
    user_loc = get_user_location("8.8.8.8")
    if user_loc:
        print(f"\n✅ User Location for 8.8.8.8:")
        print(f"   City: {user_loc.city}")
        print(f"   Country: {user_loc.country} ({user_loc.country_code})")
        print(f"   Is EU: {user_loc.is_eu}")
        print(f"   Nearest GCP Zone: {user_loc.nearest_gcp_zone}")
        print(f"   Suggested Regions: {user_loc.suggested_regions}")
    else:
        print("\n❌ Failed to detect user location")
