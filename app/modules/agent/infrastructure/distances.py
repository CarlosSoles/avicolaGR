# ==============================================================================
# MATRIZ DE DISTANCIAS Y COSTOS LOGÍSTICOS - AVÍCOLA GR
# Archivo: backend/app/modules/agent/infrastructure/distances.py
# ==============================================================================

from typing import Dict, Any, Optional, Tuple
from math import radians, sin, cos, asin, sqrt

# Costo promedio logístico de flete por kilómetro recorrido (combustible, peajes, desgaste camión 3 ejes)
COST_PER_KM_SOLES = 4.50

# Matriz de distancias reales estimadas (en kilómetros) desde las 23 granjas oficiales
# hacia las 4 zonas comerciales principales de Lima Metropolitana
FARM_TO_ZONE_DISTANCES_KM: Dict[str, Dict[str, float]] = {
    # Granjas Cuenca Norte / Carabayllo / Ancón
    "PACI1": {"NORTE": 22.0, "CENTRO": 36.5, "SUR": 58.0, "METROPOLITANA": 33.0},
    "PACI2": {"NORTE": 24.5, "CENTRO": 38.0, "SUR": 60.5, "METROPOLITANA": 35.0},
    "PACI5": {"NORTE": 26.0, "CENTRO": 39.5, "SUR": 62.0, "METROPOLITANA": 36.5},
    "PACI6": {"NORTE": 21.0, "CENTRO": 35.0, "SUR": 56.5, "METROPOLITANA": 32.0},
    "PACI7": {"NORTE": 23.0, "CENTRO": 37.0, "SUR": 59.0, "METROPOLITANA": 34.0},
    "PAC67": {"NORTE": 25.0, "CENTRO": 38.5, "SUR": 61.0, "METROPOLITANA": 35.5},

    # Granjas Cuenca Centro / Huachipa / Chosica / Ate
    "TRAD1": {"NORTE": 42.0, "CENTRO": 19.5, "SUR": 38.0, "METROPOLITANA": 24.0},
    "TRAD2": {"NORTE": 44.0, "CENTRO": 21.0, "SUR": 40.0, "METROPOLITANA": 25.5},
    "SISA1": {"NORTE": 31.0, "CENTRO": 28.0, "SUR": 45.0, "METROPOLITANA": 29.0},
    "SISA2": {"NORTE": 33.5, "CENTRO": 30.0, "SUR": 47.0, "METROPOLITANA": 31.0},
    "SISA3": {"NORTE": 35.0, "CENTRO": 32.0, "SUR": 49.0, "METROPOLITANA": 33.0},
    "SEMIA": {"NORTE": 38.0, "CENTRO": 34.0, "SUR": 52.0, "METROPOLITANA": 36.0},
    "SEMIB": {"NORTE": 40.0, "CENTRO": 36.0, "SUR": 54.0, "METROPOLITANA": 38.0},

    # Granjas Cuenca Sur / Lurín / Chilca / Cañete
    "MORI2": {"NORTE": 68.0, "CENTRO": 48.0, "SUR": 22.0, "METROPOLITANA": 42.0},
    "QBAGA": {"NORTE": 72.0, "CENTRO": 52.0, "SUR": 26.0, "METROPOLITANA": 46.0},
    "NUC-9": {"NORTE": 65.0, "CENTRO": 45.0, "SUR": 25.0, "METROPOLITANA": 40.0},
    "NUC-B": {"NORTE": 66.5, "CENTRO": 46.5, "SUR": 26.5, "METROPOLITANA": 41.5},
    "ESMER": {"NORTE": 74.0, "CENTRO": 55.0, "SUR": 28.0, "METROPOLITANA": 49.0},

    # Granjas de Reserva & Periféricas
    "R4G-A": {"NORTE": 48.0, "CENTRO": 42.0, "SUR": 55.0, "METROPOLITANA": 44.0},
    "R4G-B": {"NORTE": 50.0, "CENTRO": 44.0, "SUR": 57.0, "METROPOLITANA": 46.0},
    "R4G-C": {"NORTE": 52.0, "CENTRO": 46.0, "SUR": 59.0, "METROPOLITANA": 48.0},
    "507":   {"NORTE": 55.0, "CENTRO": 49.0, "SUR": 62.0, "METROPOLITANA": 51.0},
    "HARC2": {"NORTE": 58.0, "CENTRO": 52.0, "SUR": 65.0, "METROPOLITANA": 54.0},
}


def haversine_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Distancia en línea recta (km) entre dos coordenadas WGS84."""
    r = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return round(2 * r * asin(sqrt(a)), 2)


def distance_to_delivery_point(
    farm_coords: Optional[Tuple[float, float]],
    delivery_coords: Optional[Tuple[float, float]],
    farm_code: str,
    zone_code: str,
) -> Tuple[float, str]:
    """
    Distancia granja → punto de entrega.
    Usa coordenadas reales cuando ambas están disponibles; si no, cae a la matriz por zona.

    Devuelve (km, origen) donde origen es 'COORDENADAS' o 'ZONA'.
    """
    if farm_coords and delivery_coords:
        km = haversine_km(farm_coords[0], farm_coords[1], delivery_coords[0], delivery_coords[1])
        return km, "COORDENADAS"

    return get_farm_distance_km(farm_code, zone_code), "ZONA"


def get_farm_distance_km(farm_code: str, zone_code: str) -> float:
    """
    Retorna la distancia en kilómetros desde una granja a la zona comercial solicitada.
    Si no se encuentra en el mapa exacto, calcula un valor por defecto realista (45 km).
    """
    clean_farm = (farm_code or "").upper().strip()
    clean_zone = (zone_code or "CENTRO").upper().strip()

    farm_distances = FARM_TO_ZONE_DISTANCES_KM.get(clean_farm)
    if not farm_distances:
        return 45.0

    return farm_distances.get(clean_zone, 40.0)


def calculate_freight_cost_soles(distance_km: float) -> float:
    """Calcula el costo logístico estimado de ida y vuelta para una distancia determinada."""
    return round(distance_km * COST_PER_KM_SOLES, 2)

