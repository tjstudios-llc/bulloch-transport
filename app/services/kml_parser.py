import io
import logging
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List
from app.services.geocoding import get_street_name_from_coords

logger = logging.getLogger("bulloch.services.kml_parser")

# Security limits for uploaded files
MAX_KMZ_UNCOMPRESSED_SIZE = 10 * 1024 * 1024  # 10 MB limit
MAX_ZIP_RATIO = 100  # Max compression ratio check


def _validate_coordinates(lat: float, lng: float) -> bool:
    """Validates latitude and longitude range limits."""
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


def parse_kml_content(kml_bytes: bytes) -> Dict[str, Any]:
    """
    Parses a KML or compressed KMZ file exported from GIS mapping tools.
    Extracts route name, stop waypoints, and polyline coordinates safely.
    """
    if not kml_bytes:
        raise ValueError("Uploaded KML content is empty.")

    try:
        # 1. Handle KMZ (Zip archive) files safely
        if kml_bytes.startswith(b"PK"):
            with zipfile.ZipFile(io.BytesIO(kml_bytes)) as z:
                kml_files = [f for f in z.namelist() if f.lower().endswith(".kml")]
                if not kml_files:
                    raise ValueError("No valid .kml file found inside compressed .kmz archive.")

                target_file = kml_files[0]
                info = z.getinfo(target_file)

                # Check uncompressed size limit to prevent Zip Bomb DoS
                if info.file_size > MAX_KMZ_UNCOMPRESSED_SIZE:
                    raise ValueError("Extracted KML file size exceeds maximum allowed limit (10MB).")

                # Check compression ratio to prevent decompression amplification attacks
                if info.compress_size > 0 and (info.file_size / info.compress_size) > MAX_ZIP_RATIO:
                    raise ValueError("Suspicious compression ratio detected in KMZ archive.")

                kml_bytes = z.read(target_file)

        # 2. Decode string and strip UTF-8 BOM characters (\xef\xbb\xbf)
        kml_text = kml_bytes.decode("utf-8-sig").strip()

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
        path_polyline: List[Dict[str, float]] = []

        placemarks = root.findall(f".//{namespace}Placemark")

        for pm in placemarks:
            pm_name_node = pm.find(f"{namespace}name")
            pm_name = (
                pm_name_node.text.strip()
                if pm_name_node is not None and pm_name_node.text
                else "Stop"
            )

            # Parse Stop Placemark (Point)
            point_node = pm.find(f".//{namespace}Point/{namespace}coordinates")
            if point_node is not None and point_node.text:
                coords_str = point_node.text.strip()
                parts = coords_str.split(",")
                if len(parts) >= 2:
                    try:
                        lng = float(parts[0])
                        lat = float(parts[1])
                        if _validate_coordinates(lat, lng):
                            street = get_street_name_from_coords(lat, lng)
                            stops.append(
                                {
                                    "name": pm_name,
                                    "street_name": street,
                                    "lat": lat,
                                    "lng": lng,
                                    "status": "pending",
                                }
                            )
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping malformed point coordinate in placemark '{pm_name}'")

            # Parse Drawn LineString Polyline
            linestring_node = pm.find(f".//{namespace}LineString/{namespace}coordinates")
            if linestring_node is not None and linestring_node.text:
                raw_coords = linestring_node.text.strip().split()
                for coord_pair in raw_coords:
                    parts = coord_pair.split(",")
                    if len(parts) >= 2:
                        try:
                            lng = float(parts[0])
                            lat = float(parts[1])
                            if _validate_coordinates(lat, lng):
                                point = {"lat": lat, "lng": lng}
                                if not path_polyline or path_polyline[-1] != point:
                                    path_polyline.append(point)
                        except (ValueError, TypeError):
                            continue

        # Mark initial stop as current
        if stops:
            stops[0]["status"] = "current"

        logger.info(
            f"KML parsed successfully: '{route_name}' ({len(stops)} stops, {len(path_polyline)} polyline points)"
        )

        return {
            "name": route_name,
            "stops": stops,
            "path_polyline": path_polyline,
        }

    except ET.ParseError as pe:
        logger.error(f"XML syntax error while parsing KML payload: {pe}")
        raise ValueError("Invalid XML syntax in KML file.") from pe
    except ValueError as ve:
        raise ve
    except Exception as e:
        logger.exception(f"Failed to parse KML content: {e}")
        raise ValueError(f"Corrupted or unsupported KML/KMZ archive: {e}") from e