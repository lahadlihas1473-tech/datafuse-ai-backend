# app/api/pipeline.py

import json
import re
import time
import uuid
import requests

from datetime import datetime, timezone
from typing import Any, Dict, List
from xml.etree import ElementTree as ET

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import text
from pyproj import Transformer
from shapely.geometry import Point, shape

from app.database.database import engine


router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# ============================================================
# CONFIG
# ============================================================

KOOP_URL = "https://repository.overheid.nl/sru"

PDOK_URL = (
    "https://api.pdok.nl/bzk/locatieserver/search/"
    "v3_1/free"
)

BAG_WFS_URL = (
    "https://service.pdok.nl/lv/bag/wfs/v2_0"
)

# 3DBAG
THREEDBAG_BASE_URL = (
    "https://api.3dbag.nl/collections/pand/items"
)

START_DATE = "2025-07-01"
END_DATE = "2026-07-20"

KOOP_PAGE_SIZE = 100

REQUEST_TIMEOUT = 30

BBOX_METERS = 2.0

SLEEP_SECONDS = 0.15


WGS84_TO_RD = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:28992",
    always_xy=True
)

RD_TO_WGS84 = Transformer.from_crs(
    "EPSG:28992",
    "EPSG:4326",
    always_xy=True
)


# ============================================================
# RESPONSE FORMAT
# ============================================================

def response(
    success: bool,
    status: int,
    message: str,
    data: Any = None,
    error: Any = None
):
    return {
        "success": success,
        "status": status,
        "message": message,
        "data": data,
        "error": error
    }


# ============================================================
# RUN ID
# ============================================================

def generate_run_id() -> str:

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    suffix = uuid.uuid4().hex[:8]

    return f"run-{timestamp}-{suffix}"


# ============================================================
# DATABASE SETUP
# ============================================================

def ensure_tables():

    with engine.begin() as conn:

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id BIGSERIAL PRIMARY KEY,
                run_id VARCHAR(100) NOT NULL UNIQUE,
                status VARCHAR(30) NOT NULL,
                current_stage VARCHAR(100),
                statistics JSONB DEFAULT '{}'::jsonb,
                error TEXT,
                started_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_verification (
                id BIGSERIAL PRIMARY KEY,
                pand_id TEXT,
                bouwjaar INTEGER,
                verblijfsobject_id TEXT,
                geometry JSONB,
                bag_geometry JSONB,
                bag_status TEXT,
                run_id VARCHAR(100),
                notice_id TEXT,
                title TEXT,
                publication_date TEXT,
                address TEXT,
                postal_code TEXT,
                municipality TEXT,
                city TEXT,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                location_source TEXT,

                threedbag_id TEXT,
                threedbag_match_status TEXT,
                threedbag_data JSONB,

                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        # ----------------------------------------------------
        # Add 3DBAG columns if api_verification already exists
        # ----------------------------------------------------

        conn.execute(text("""
            ALTER TABLE api_verification
            ADD COLUMN IF NOT EXISTS threedbag_id TEXT
        """))

        conn.execute(text("""
            ALTER TABLE api_verification
            ADD COLUMN IF NOT EXISTS threedbag_match_status TEXT
        """))

        conn.execute(text("""
            ALTER TABLE api_verification
            ADD COLUMN IF NOT EXISTS threedbag_data JSONB
        """))

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS
            idx_pipeline_runs_run_id
            ON pipeline_runs(run_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS
            idx_api_verification_run_id
            ON api_verification(run_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS
            idx_api_verification_notice_id
            ON api_verification(notice_id)
        """))


# ============================================================
# PIPELINE RUN RECORD
# ============================================================

def create_pipeline_run(run_id: str):

    statistics = {
        "total": 0,
        "processed": 0,
        "stored": 0,
        "failed": 0,
        "3dbag_matched": 0,
        "3dbag_unmatched": 0
    }

    with engine.begin() as conn:

        conn.execute(
            text("""
                INSERT INTO pipeline_runs (
                    run_id,
                    status,
                    current_stage,
                    statistics,
                    error
                )
                VALUES (
                    :run_id,
                    'RUNNING',
                    'STARTING',
                    CAST(:statistics AS JSONB),
                    NULL
                )
            """),
            {
                "run_id": run_id,
                "statistics": json.dumps(statistics)
            }
        )


def update_pipeline_run(
    run_id: str,
    status: str = None,
    stage: str = None,
    statistics: Dict[str, Any] = None,
    error: str = None
):

    updates = []

    params = {
        "run_id": run_id
    }

    if status is not None:

        updates.append(
            "status = :status"
        )

        params["status"] = status

    if stage is not None:

        updates.append(
            "current_stage = :stage"
        )

        params["stage"] = stage

    if statistics is not None:

        updates.append(
            "statistics = CAST(:statistics AS JSONB)"
        )

        params["statistics"] = json.dumps(
            statistics
        )

    if error is not None:

        updates.append(
            "error = :error"
        )

        params["error"] = error

    updates.append(
        "updated_at = NOW()"
    )

    query = f"""
        UPDATE pipeline_runs
        SET {", ".join(updates)}
        WHERE run_id = :run_id
    """

    with engine.begin() as conn:

        conn.execute(
            text(query),
            params
        )


# ============================================================
# KOOP XML HELPERS
# ============================================================

def local_name(tag: str) -> str:

    return tag.rsplit("}", 1)[-1]


def find_text(
    element,
    wanted_name: str
):

    for child in element.iter():

        if local_name(child.tag) == wanted_name:

            if child.text:

                return child.text.strip()

    return None


def parse_location_point(value: str):

    if not value:

        return None, None

    numbers = re.findall(
        r"-?\d+(?:\.\d+)?",
        value
    )

    if len(numbers) < 2:

        return None, None

    a = float(numbers[0])
    b = float(numbers[1])

    # KOOP locatiepunt is treated as
    # latitude, longitude

    if -90 <= a <= 90 and -180 <= b <= 180:

        return a, b

    if -90 <= b <= 90 and -180 <= a <= 180:

        return b, a

    return None, None


# ============================================================
# ADDRESS PARSER
# ============================================================

def parse_address_from_title(title: str):

    if not title:

        return None, None, None

    pattern = (
        r"(.+?)\s+\d+[A-Za-z]?,\s*"
        r"(\d{4}\s*[A-Z]{2})\s+(.+)$"
    )

    match = re.search(
        pattern,
        title
    )

    if not match:

        return None, None, None

    address = match.group(1).strip()

    postal_code = match.group(2).strip()

    municipality = match.group(3).strip()

    return (
        address,
        postal_code,
        municipality
    )


# ============================================================
# PDOK FALLBACK
# ============================================================

def pdok_coordinates(
    address,
    postal_code
):

    if not address or not postal_code:

        return None, None

    try:

        result = requests.get(
            PDOK_URL,
            params={
                "q": f"{address}, {postal_code}",
                "fq": "type:adres",
                "rows": 1,
                "fl": "centroide_ll"
            },
            timeout=REQUEST_TIMEOUT
        )

        result.raise_for_status()

        data = result.json()

        docs = data.get(
            "response",
            {}
        ).get(
            "docs",
            []
        )

        if not docs:

            return None, None

        value = docs[0].get(
            "centroide_ll"
        )

        if not value:

            return None, None

        numbers = re.findall(
            r"-?\d+(?:\.\d+)?",
            str(value)
        )

        if len(numbers) < 2:

            return None, None

        lon = float(numbers[0])
        lat = float(numbers[1])

        if (
            -90 <= lat <= 90
            and
            -180 <= lon <= 180
        ):

            return lat, lon

    except Exception:

        pass

    return None, None


# ============================================================
# KOOP SRU EXTRACTION
# ============================================================

def extract_koop_notices() -> List[Dict[str, Any]]:

    query = (
        f'(cql.textAndIndexes="sloopmelding") '
        f'AND dt.modified>={START_DATE} '
        f'AND dt.modified<={END_DATE}'
    )

    notices = []

    seen_ids = set()

    start = 1

    while True:

        response_data = requests.get(
            KOOP_URL,
            params={
                "operation": "searchRetrieve",
                "version": "2.0",
                "x-connection": "officielepublicaties",
                "query": query,
                "startRecord": start,
                "maximumRecords": KOOP_PAGE_SIZE
            },
            timeout=REQUEST_TIMEOUT
        )

        response_data.raise_for_status()

        root = ET.fromstring(
            response_data.content
        )

        records = [
            element
            for element in root.iter()
            if local_name(element.tag) == "record"
        ]

        if not records:

            break

        for record in records:

            notice_id = find_text(
                record,
                "identifier"
            )

            title = find_text(
                record,
                "title"
            )

            publication_date = find_text(
                record,
                "modified"
            )

            locatiepunt = find_text(
                record,
                "locatiepunt"
            )

            if not notice_id:

                continue

            if notice_id in seen_ids:

                continue

            seen_ids.add(notice_id)

            address, postal_code, municipality = (
                parse_address_from_title(
                    title
                )
            )

            latitude, longitude = (
                parse_location_point(
                    locatiepunt
                )
            )

            location_source = "KOOP"

            # PDOK fallback only if
            # KOOP coordinates are missing

            if (
                latitude is None
                or
                longitude is None
            ):

                pdok_lat, pdok_lon = (
                    pdok_coordinates(
                        address,
                        postal_code
                    )
                )

                if (
                    pdok_lat is not None
                    and
                    pdok_lon is not None
                ):

                    latitude = pdok_lat

                    longitude = pdok_lon

                    location_source = "PDOK"

            notices.append({

                "notice_id": notice_id,

                "title": title,

                "publication_date": (
                    publication_date[:10]
                    if publication_date
                    else None
                ),

                "address": address,

                "postal_code": postal_code,

                "municipality": municipality,

                "city": municipality,

                "latitude": latitude,

                "longitude": longitude,

                "location_source": location_source
            })

        if len(records) < KOOP_PAGE_SIZE:

            break

        start += KOOP_PAGE_SIZE

        time.sleep(
            SLEEP_SECONDS
        )

    if not notices:

        raise RuntimeError(
            f"KOOP SRU returned 0 records for "
            f"{START_DATE} to {END_DATE}"
        )

    return notices


# ============================================================
# BAG METHOD 2
#
# DEMOLITION COORDINATES
#        ↓
# WGS84 → RD
#        ↓
# BBOX
#        ↓
# BAG PAND
#        ↓
# POINT IN PAND
# ============================================================

def method2_demolition_to_pand(
    record: Dict[str, Any]
) -> Dict[str, Any]:

    latitude = record.get(
        "latitude"
    )

    longitude = record.get(
        "longitude"
    )

    if (
        latitude is None
        or
        longitude is None
    ):

        raise ValueError(
            "Latitude/longitude missing "
            "for BAG Method 2"
        )

    latitude = float(latitude)

    longitude = float(longitude)

    rd_x, rd_y = (
        WGS84_TO_RD.transform(
            longitude,
            latitude
        )
    )

    min_x = rd_x - BBOX_METERS

    min_y = rd_y - BBOX_METERS

    max_x = rd_x + BBOX_METERS

    max_y = rd_y + BBOX_METERS

    bbox = (
        f"{min_x},{min_y},"
        f"{max_x},{max_y},"
        f"EPSG:28992"
    )

    result = requests.get(
        BAG_WFS_URL,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "bag:pand",
            "outputFormat": "application/json",
            "srsName": "EPSG:28992",
            "bbox": bbox
        },
        timeout=REQUEST_TIMEOUT
    )

    result.raise_for_status()

    data = result.json()

    features = data.get(
        "features",
        []
    )

    if not features:

        raise ValueError(
            "No BAG PAND found in coordinate BBOX"
        )

    demolition_point = Point(
        rd_x,
        rd_y
    )

    matches = []

    for feature in features:

        geometry = feature.get(
            "geometry"
        )

        if not geometry:

            continue

        try:

            polygon = shape(
                geometry
            )

            # covers() includes boundary points

            if polygon.covers(
                demolition_point
            ):

                matches.append(
                    feature
                )

        except Exception:

            continue

    if len(matches) == 0:

        raise ValueError(
            "No BAG PAND contains "
            "demolition coordinate"
        )

    if len(matches) > 1:

        raise ValueError(
            f"Multiple BAG PAND polygons "
            f"contain demolition coordinate: "
            f"{len(matches)}"
        )

    feature = matches[0]

    properties = feature.get(
        "properties",
        {}
    )

    geometry = feature.get(
        "geometry"
    )

    pand_id = (
        properties.get("identificatie")
        or
        properties.get("pand_identificatie")
        or
        properties.get("pand_id")
    )

    if not pand_id:

        raise ValueError(
            "BAG PAND found but pand_id "
            "is missing"
        )

    record["pand_id"] = str(
        pand_id
    )

    record["bag_geometry"] = geometry

    bouwjaar = (
        properties.get("bouwjaar")
        or
        properties.get(
            "oorspronkelijkbouwjaar"
        )
    )

    if bouwjaar is not None:

        try:

            record["bouwjaar"] = int(
                bouwjaar
            )

        except (
            ValueError,
            TypeError
        ):

            record["bouwjaar"] = None

    else:

        record["bouwjaar"] = None

    record["bag_status"] = (
        properties.get("status")
    )

    # Keep demolition geometry as point

    if not record.get("geometry"):

        record["geometry"] = {

            "type": "Point",

            "coordinates": [
                longitude,
                latitude
            ]
        }

    return record


# ============================================================
# BAG METHOD 3
#
# VERIFIED PAND
#       ↓
# VBOs
#       ↓
# VERBLIJFSOBJECT_ID
# ============================================================

def method3_pand_to_vbo(
    record: Dict[str, Any]
) -> Dict[str, Any]:

    pand_id = record.get(
        "pand_id"
    )

    if not pand_id:

        raise ValueError(
            "pand_id missing "
            "for BAG Method 3"
        )

    escaped_pand_id = (
        str(pand_id)
        .replace("'", "''")
    )

    result = requests.get(
        BAG_WFS_URL,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "bag:verblijfsobject",
            "outputFormat": "application/json",
            "srsName": "EPSG:28992",
            "CQL_FILTER": (
                f"pand_identificatie="
                f"'{escaped_pand_id}'"
            )
        },
        timeout=REQUEST_TIMEOUT
    )

    result.raise_for_status()

    data = result.json()

    features = data.get(
        "features",
        []
    )

    if not features:

        raise ValueError(
            f"No VBO found for pand_id "
            f"{pand_id}"
        )

    vbo_ids = []

    for feature in features:

        properties = feature.get(
            "properties",
            {}
        )

        relation = (
            properties.get(
                "pand_identificatie"
            )
            or
            properties.get(
                "pand_id"
            )
        )

        # Validate relationship

        if (
            relation
            and
            str(relation) != str(pand_id)
        ):

            continue

        vbo_id = (
            properties.get(
                "identificatie"
            )
            or
            properties.get(
                "verblijfsobject_id"
            )
        )

        if vbo_id:

            vbo_ids.append(
                str(vbo_id)
            )

    if not vbo_ids:

        raise ValueError(
            "VBO records found but no valid "
            "verblijfsobject_id relationship"
        )

    # Required final field

    record["verblijfsobject_id"] = (
        vbo_ids[0]
    )

    return record


# ============================================================
# 3DBAG VALIDATION
#
# BAG pand_id
#       ↓
# NL.IMBAG.Pand.{pand_id}
#       ↓
# feature
#       ↓
# CityObjects
#       ↓
# NL.IMBAG.Pand.{pand_id}
#       ↓
# Building
#       ↓
# attributes
# ============================================================

def get_3dbag_building(
    pand_id: str
):

    if not pand_id:

        return None

    pand_id = str(
        pand_id
    ).strip()

    # --------------------------------------------------------
    # Construct exact 3DBAG identifier
    # --------------------------------------------------------

    full_3dbag_id = (
        f"NL.IMBAG.Pand.{pand_id}"
    )

    url = (
        f"{THREEDBAG_BASE_URL}/"
        f"{full_3dbag_id}"
    )

    try:

        result = requests.get(
            url,
            headers={
                "Accept": "application/json"
            },
            timeout=REQUEST_TIMEOUT
        )

        if result.status_code != 200:

            return None

        data = result.json()

    except (
        requests.RequestException,
        ValueError
    ):

        return None

    # --------------------------------------------------------
    # STEP 1
    # feature
    # --------------------------------------------------------

    feature = data.get(
        "feature"
    )

    if not isinstance(
        feature,
        dict
    ):

        return None

    # --------------------------------------------------------
    # STEP 2
    # CityObjects
    # --------------------------------------------------------

    city_objects = feature.get(
        "CityObjects"
    )

    if not isinstance(
        city_objects,
        dict
    ):

        return None

    # --------------------------------------------------------
    # STEP 3
    # Exact NL.IMBAG.Pand.{pand_id}
    # --------------------------------------------------------

    building = city_objects.get(
        full_3dbag_id
    )

    if not isinstance(
        building,
        dict
    ):

        return None

    # --------------------------------------------------------
    # STEP 4
    # Confirm Building
    # --------------------------------------------------------

    if building.get("type") != "Building":

        return None

    # --------------------------------------------------------
    # STEP 5
    # Get attributes
    # --------------------------------------------------------

    attributes = building.get(
        "attributes"
    )

    if not isinstance(
        attributes,
        dict
    ):

        attributes = {}

    return {

        "3dbag_id": full_3dbag_id,

        "building_type": (
            building.get("type")
        ),

        "attributes": attributes
    }


# ============================================================
# PROCESS ONE NOTICE
# ============================================================

def process_notice(
    notice: Dict[str, Any]
) -> Dict[str, Any]:

    # METHOD 2

    notice = (
        method2_demolition_to_pand(
            notice
        )
    )

    # METHOD 3

    notice = (
        method3_pand_to_vbo(
            notice
        )
    )

    # 3DBAG

    pand_id = notice.get(
        "pand_id"
    )

    full_3dbag_id = None

    if pand_id:

        full_3dbag_id = (
            f"NL.IMBAG.Pand.{pand_id}"
        )

    threedbag_result = (
        get_3dbag_building(
            pand_id
        )
    )

    notice["threedbag_id"] = (
        full_3dbag_id
    )

    if threedbag_result:

        notice[
            "threedbag_match_status"
        ] = "MATCHED"

        notice[
            "threedbag_data"
        ] = threedbag_result

    else:

        notice[
            "threedbag_match_status"
        ] = "UNMATCHED"

        notice[
            "threedbag_data"
        ] = None

    return notice


# ============================================================
# DB INSERT
# ONLY REQUIRED FIELDS
# ============================================================

def insert_record(
    record: Dict[str, Any],
    run_id: str
):

    sql = text("""
        INSERT INTO api_verification (
            pand_id,
            bouwjaar,
            verblijfsobject_id,
            geometry,
            bag_geometry,
            bag_status,
            run_id,
            notice_id,
            title,
            publication_date,
            address,
            postal_code,
            municipality,
            city,
            latitude,
            longitude,
            location_source,
            threedbag_id,
            threedbag_match_status,
            threedbag_data
        )
        VALUES (
            :pand_id,
            :bouwjaar,
            :verblijfsobject_id,
            CAST(:geometry AS JSONB),
            CAST(:bag_geometry AS JSONB),
            :bag_status,
            :run_id,
            :notice_id,
            :title,
            :publication_date,
            :address,
            :postal_code,
            :municipality,
            :city,
            :latitude,
            :longitude,
            :location_source,
            :threedbag_id,
            :threedbag_match_status,
            CAST(:threedbag_data AS JSONB)
        )
    """)

    params = {

        "pand_id": record.get(
            "pand_id"
        ),

        "bouwjaar": record.get(
            "bouwjaar"
        ),

        "verblijfsobject_id": (
            record.get(
                "verblijfsobject_id"
            )
        ),

        "geometry": json.dumps(
            record.get("geometry")
        ),

        "bag_geometry": json.dumps(
            record.get("bag_geometry")
        ),

        "bag_status": record.get(
            "bag_status"
        ),

        "run_id": run_id,

        "notice_id": record.get(
            "notice_id"
        ),

        "title": record.get(
            "title"
        ),

        "publication_date": (
            record.get(
                "publication_date"
            )
        ),

        "address": record.get(
            "address"
        ),

        "postal_code": record.get(
            "postal_code"
        ),

        "municipality": record.get(
            "municipality"
        ),

        "city": record.get(
            "city"
        ),

        "latitude": record.get(
            "latitude"
        ),

        "longitude": record.get(
            "longitude"
        ),

        "location_source": (
            record.get(
                "location_source"
            )
        ),

        "threedbag_id": (
            record.get(
                "threedbag_id"
            )
        ),

        "threedbag_match_status": (
            record.get(
                "threedbag_match_status"
            )
        ),

        "threedbag_data": json.dumps(
            record.get(
                "threedbag_data"
            )
        )
    }

    # IMPORTANT:
    # Every notice is committed independently.

    with engine.begin() as conn:

        conn.execute(
            sql,
            params
        )


# ============================================================
# BACKGROUND PIPELINE
# ============================================================

def run_pipeline(
    run_id: str
):

    statistics = {

        "total": 0,

        "processed": 0,

        "stored": 0,

        "failed": 0,

        "3dbag_matched": 0,

        "3dbag_unmatched": 0
    }

    try:

        # ----------------------------------------------------
        # KOOP
        # ----------------------------------------------------

        update_pipeline_run(
            run_id,
            stage="KOOP_EXTRACTION",
            statistics=statistics
        )

        notices = (
            extract_koop_notices()
        )

        statistics["total"] = (
            len(notices)
        )

        update_pipeline_run(
            run_id,
            stage="KOOP_COMPLETED",
            statistics=statistics
        )

        # ----------------------------------------------------
        # PROCESS ONE BY ONE
        # ----------------------------------------------------

        for index, notice in enumerate(
            notices,
            start=1
        ):

            try:

                update_pipeline_run(
                    run_id,
                    stage=(
                        f"PROCESSING_NOTICE_{index}"
                    ),
                    statistics=statistics
                )

                # ------------------------------------------------
                # Method 2
                # ------------------------------------------------

                update_pipeline_run(
                    run_id,
                    stage="METHOD2",
                    statistics=statistics
                )

                processed_record = (
                    method2_demolition_to_pand(
                        notice
                    )
                )

                # ------------------------------------------------
                # Method 3
                # ------------------------------------------------

                update_pipeline_run(
                    run_id,
                    stage="METHOD3",
                    statistics=statistics
                )

                processed_record = (
                    method3_pand_to_vbo(
                        processed_record
                    )
                )

                # ------------------------------------------------
                # 3DBAG VALIDATION
                # ------------------------------------------------

                update_pipeline_run(
                    run_id,
                    stage="3DBAG_VALIDATION",
                    statistics=statistics
                )

                pand_id = (
                    processed_record.get(
                        "pand_id"
                    )
                )

                full_3dbag_id = None

                if pand_id:

                    full_3dbag_id = (
                        f"NL.IMBAG.Pand.{pand_id}"
                    )

                threedbag_result = (
                    get_3dbag_building(
                        pand_id
                    )
                )

                processed_record[
                    "threedbag_id"
                ] = full_3dbag_id

                if threedbag_result:

                    processed_record[
                        "threedbag_match_status"
                    ] = "MATCHED"

                    processed_record[
                        "threedbag_data"
                    ] = threedbag_result

                    statistics[
                        "3dbag_matched"
                    ] += 1

                else:

                    processed_record[
                        "threedbag_match_status"
                    ] = "UNMATCHED"

                    processed_record[
                        "threedbag_data"
                    ] = None

                    statistics[
                        "3dbag_unmatched"
                    ] += 1

                # ------------------------------------------------
                # Store
                # ------------------------------------------------

                update_pipeline_run(
                    run_id,
                    stage="STORING",
                    statistics=statistics
                )

                insert_record(
                    processed_record,
                    run_id
                )

                # COMMITTED HERE

                statistics[
                    "stored"
                ] += 1

                statistics[
                    "processed"
                ] += 1

            except Exception as exc:

                statistics[
                    "failed"
                ] += 1

                statistics[
                    "processed"
                ] += 1

                print(
                    f"Notice failed: "
                    f"{notice.get('notice_id')} - "
                    f"{exc}"
                )

            update_pipeline_run(
                run_id,
                stage=(
                    f"NOTICE_{index}_COMPLETED"
                ),
                statistics=statistics
            )

            time.sleep(
                SLEEP_SECONDS
            )

        # ----------------------------------------------------
        # FINAL STATUS
        # ----------------------------------------------------

        if statistics["stored"] == 0:

            update_pipeline_run(
                run_id,
                status="FAILED",
                stage="FINISHED",
                statistics=statistics,
                error=(
                    "No notices were "
                    "successfully stored"
                )
            )

        else:

            update_pipeline_run(
                run_id,
                status="COMPLETED",
                stage="FINISHED",
                statistics=statistics
            )

    except Exception as exc:

        update_pipeline_run(
            run_id,
            status="FAILED",
            stage="FAILED",
            statistics=statistics,
            error=str(exc)
        )


# ============================================================
# POST /pipeline/run
# ============================================================

@router.post(
    "/run",
    status_code=202
)
def start_pipeline(
    background_tasks: BackgroundTasks
):

    ensure_tables()

    run_id = generate_run_id()

    create_pipeline_run(
        run_id
    )

    background_tasks.add_task(
        run_pipeline,
        run_id
    )

    return response(
        success=True,
        status=202,
        message=(
            "Pipeline started successfully"
        ),
        data={
            "run_id": run_id,
            "status": "RUNNING"
        }
    )


# ============================================================
# GET /pipeline/run/{run_id}
# ============================================================

@router.get(
    "/run/{run_id}"
)
def get_pipeline_status(
    run_id: str
):

    with engine.begin() as conn:

        result = conn.execute(
            text("""
                SELECT
                    run_id,
                    status,
                    current_stage,
                    statistics,
                    error,
                    started_at,
                    updated_at
                FROM pipeline_runs
                WHERE run_id = :run_id
            """),
            {
                "run_id": run_id
            }
        ).mappings().first()

    if not result:

        raise HTTPException(
            status_code=404,
            detail=response(
                False,
                404,
                "Pipeline run not found",
                error={
                    "code": "RUN_NOT_FOUND",
                    "details": run_id
                }
            )
        )

    return response(
        success=True,
        status=200,
        message=(
            "Pipeline status retrieved"
        ),
        data=dict(result)
    )


# ============================================================
# GET /pipeline/results/{run_id}
# ============================================================

@router.get(
    "/results/{run_id}"
)
def get_pipeline_results(
    run_id: str
):

    with engine.connect() as conn:

        result = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM api_verification
                WHERE run_id = :run_id
            """),
            {
                "run_id": run_id
            }
        ).scalar()

    return {

        "success": True,

        "status": 200,

        "message": (
            "Pipeline results retrieved "
            "successfully"
        ),

        "data": {

            "run_id": run_id,

            "total_records": result
        },

        "error": None
    }