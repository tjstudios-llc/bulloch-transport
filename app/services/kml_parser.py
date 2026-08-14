# app/services/kml_parser.py

import io
import zipfile
import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, List
from app.services.geocoding import get_street_name_from_coords

logger = logging.getLogger(__name__)


def parse_kml_content(kml_bytes: bytes) -> Dict[str, Any]:
    """
    Parses a KML or KMZ file exported from Google Maps or Google My Maps.
    Extracts route name, stop waypoints, and the strict polyline coordinate path.
    Handles compressed .kmz archives and UTF-8 BOM characters automatically.
    """
    try:
        # 1. Handle KMZ (Zip archive) files
        if kml_bytes.startswith(b'PK'):
            with zipfile.ZipFile(io.BytesIO(kml_bytes)) as z:
                kml_files = [f for f in z.namelist() if f.lower().endswith('.kml')]
                if not kml_files:
                    raise ValueError("No valid .kml file found inside compressed .kmz archive.")
                kml_bytes = z.read(kml_files[0])

        # 2. Decode string and strip UTF-8 BOM characters (\xef\xbb\xbf)
        kml_text = kml_bytes.decode('utf-8-sig').strip()

        # 3. Parse XML Root
        root = ET.fromstring(kml_text)

        # Handle KML XML Namespaces
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"

        route_name = "Imported KML Route"
        
        # Extract Route Document Title
        doc_name_node = root.find(f".//{namespace}Document/{namespace}name")
        if doc_name_node is not None and doc_name_node.text:
            route_name = doc_name_node.text.strip()

        stops: List[Dict[str, Any]] = []
        # FIRESTORE FIX: Store as List of dicts to avoid 400 Nested Array errors
        path_polyline: List[Dict[str, float]] = []

        placemarks = root.findall(f".//{namespace}Placemark")

        for pm in placemarks:
            pm_name_node = pm.find(f"{namespace}name")
            pm_name = pm_name_node.text.strip() if pm_name_node is not None and pm_name_node.text else "Stop"

            # Parse Stop Placemark (Point)
            point_node = pm.find(f".//{namespace}Point/{namespace}coordinates")
            if point_node is not None and point_node.text:
                coords_str = point_node.text.strip()
                parts = coords_str.split(",")
                if len(parts) >= 2:
                    lng, lat = float(parts[0]), float(parts[1])
                    street = get_street_name_from_coords(lat, lng)
                    stops.append({
                        "name": pm_name,
                        "street_name": street,
                        "lat": lat,
                        "lng": lng,
                        "status": "pending"
                    })

            # Parse Drawn LineString Polyline
            linestring_node = pm.find(f".//{namespace}LineString/{namespace}coordinates")
            if linestring_node is not None and linestring_node.text:
                raw_coords = linestring_node.text.strip().split()
                for coord_pair in raw_coords:
                    parts = coord_pair.split(",")
                    if len(parts) >= 2:
                        lng, lat = float(parts[0]), float(parts[1])
                        # FIRESTORE FIX: Map object instead of nested list [lat, lng]
                        path_polyline.append({"lat": lat, "lng": lng})

        # Mark first stop as current
        if stops:
            stops[0]["status"] = "current"

        logger.info(f"KML parsed successfully: '{route_name}' ({len(stops)} stops, {len(path_polyline)} polyline points)")

        return {
            "name": route_name,
            "stops": stops,
            "path_polyline": path_polyline
        }

    except Exception as e:
        logger.error(f"Failed to parse KML content: {e}")
        raise ValueError(f"Invalid or corrupted KML/KMZ file structure: {e}")