
from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session


from app.database.session import get_db
from app.models.demolition import DemolitionStaging
from app.schemas.demolition import (
    DemolitionCreate,
    DemolitionResponse,
    DemolitionUpdate,
    DemolitionLocationResponse,
    DemolitionBAGResponse,
    DemolitionGeometryResponse,

)


from app.schemas.response import APIResponse


router = APIRouter(
    prefix="/demolition",
    tags=["Demolition"],
)


# ============================================================
# GET COUNT
# ============================================================

@router.get(
    "/count",
    response_model=APIResponse,
)
def demolition_count(
    db: Session = Depends(get_db),
):
    count = (
        db.query(
            func.count(DemolitionStaging.notice_id)
        )
        .scalar()
    )

    return APIResponse(
        success=True,
        status=200,
        message="Demolition record count retrieved successfully",
        data={
            "table": "demolition_staging",
            "records": count,
        },
        error=None,
    )


# ============================================================
# GET ALL
# ============================================================

@router.get(
    "/",
    response_model=APIResponse,
)
def get_demolition_records(
    db: Session = Depends(get_db),
):
    records = (
        db.query(DemolitionStaging)
        .order_by(DemolitionStaging.notice_id)
        .limit(100)
        .all()
    )

    data = [
        DemolitionResponse.model_validate(record)
        for record in records
    ]

    return APIResponse(
        success=True,
        status=200,
        message="Demolition records retrieved successfully",
        data=data,
        error=None,
    )


# ============================================================
# GET SINGLE RECORD
# ============================================================

@router.get(
    "/{notice_id}",
    response_model=APIResponse,
)
def get_demolition_record(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    data = DemolitionResponse.model_validate(record)

    return APIResponse(
        success=True,
        status=200,
        message="Demolition record retrieved successfully",
        data=data,
        error=None,
    )





# ============================================================
# POSTGIS VALIDATION
# ============================================================

@router.get(
    "/{notice_id}/validate",
    response_model=APIResponse,
)
def validate_demolition_geometry(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    if record.latitude is None or record.longitude is None:
        return APIResponse(
            success=False,
            status=400,
            message="Latitude or longitude is missing",
            data=None,
            error={
                "code": "COORDINATES_MISSING",
                "details": (
                    "Latitude and longitude are required "
                    "for geometry validation."
                ),
            },
        )

    if record.geometry is None:
        return APIResponse(
            success=False,
            status=400,
            message="BAG geometry is missing",
            data=None,
            error={
                "code": "BAG_GEOMETRY_MISSING",
                "details": (
                    "BAG geometry is required "
                    "for PostGIS validation."
                ),
            },
        )

    sql = text(
        """
        WITH bag_polygon AS (
            SELECT
                ST_Transform(
                    ST_SetSRID(
                        ST_GeomFromGeoJSON(
                            CAST(:geometry AS text)
                        ),
                        4326
                    ),
                    28992
                ) AS geom
        ),

        demolition_point AS (
            SELECT
                ST_Transform(
                    ST_SetSRID(
                        ST_Point(
                            :longitude,
                            :latitude
                        ),
                        4326
                    ),
                    28992
                ) AS geom
        )

        SELECT
            ST_Contains(
                bag_polygon.geom,
                demolition_point.geom
            ) AS inside_bag_geometry,

            ST_Intersects(
                bag_polygon.geom,
                demolition_point.geom
            ) AS intersects_bag_geometry,

            ST_Distance(
                bag_polygon.geom,
                demolition_point.geom
            ) AS distance_meters,

            ST_GeometryType(
                bag_polygon.geom
            ) AS geometry_type

        FROM bag_polygon, demolition_point
        """
    )

    try:
        result = db.execute(
            sql,
            {
                "geometry": str(
                    record.geometry
                ).replace("'", '"'),
                "longitude": record.longitude,
                "latitude": record.latitude,
            },
        ).fetchone()

    except Exception as exc:
        return APIResponse(
            success=False,
            status=500,
            message="PostGIS validation error",
            data=None,
            error={
                "code": "POSTGIS_VALIDATION_ERROR",
                "details": str(exc),
            },
        )

    if result is None:
        return APIResponse(
            success=False,
            status=500,
            message="PostGIS returned no validation result",
            data=None,
            error={
                "code": "POSTGIS_NO_RESULT",
                "details": (
                    "PostGIS did not return a validation result "
                    "for the provided geometry and coordinates."
                ),
            },
        )

    inside = bool(result[0])
    intersects = bool(result[1])
    distance = float(result[2])
    geometry_type = result[3]

    if inside and intersects:
        validation = "STRONG_MATCH"
    elif intersects:
        validation = "INTERSECTING"
    elif distance <= 5:
        validation = "NEAR_MATCH"
    else:
        validation = "OUTSIDE_GEOMETRY"

    return APIResponse(
        success=True,
        status=200,
        message="Demolition geometry validated successfully",
        data={
            "notice_id": record.notice_id,
            "pand_id": record.pand_id,
            "coordinate": {
                "latitude": record.latitude,
                "longitude": record.longitude,
            },
            "inside_bag_geometry": inside,
            "intersects_bag_geometry": intersects,
            "distance_meters": distance,
            "geometry_type": geometry_type,
            "validation": validation,
        },
        error=None,
    )


# ============================================================
# GET LOCATION
# ============================================================

@router.get(
    "/{notice_id}/location",
    response_model=APIResponse,
)
def get_demolition_location(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    data = DemolitionLocationResponse(
        address=record.address,
        postal_code=record.postal_code,
        municipality=record.municipality,
        city=record.city,
        latitude=record.latitude,
        longitude=record.longitude,
        location_source=record.location_source,
    )

    return APIResponse(
        success=True,
        status=200,
        message="Demolition location retrieved successfully",
        data=data,
        error=None,
    )

# ============================================================
# GET BAG DATA
# ============================================================

@router.get(
    "/{notice_id}/bag",
    response_model=APIResponse,
)
def get_demolition_bag(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    data = DemolitionBAGResponse(
        pand_id=record.pand_id,
        bouwjaar=record.bouwjaar,
        status=record.status,
        geometry=record.geometry,
    )

    return APIResponse(
        success=True,
        status=200,
        message="BAG data retrieved successfully",
        data=data,
        error=None,
    )

# ============================================================
# GET GEOMETRY
# ============================================================

@router.get(
    "/{notice_id}/geometry",
    response_model=APIResponse,
)
def get_demolition_geometry(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    data = DemolitionGeometryResponse(
        geometry=record.geometry,
        pand_id=record.pand_id,
    )

    return APIResponse(
        success=True,
        status=200,
        message="Demolition geometry retrieved successfully",
        data=data,
        error=None,
    )
# ============================================================
# GET GEOMETRY AREA
# ============================================================

@router.get(
    "/{notice_id}/area",
    response_model=APIResponse,
)
def get_demolition_geometry_area(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    return APIResponse(
        success=True,
        status=200,
        message="Building geometry area retrieved successfully",
        data={
            "notice_id": record.notice_id,
            "geometry_area_m2": record.geometry_area_m2,
        },
        error=None,
    )


# ============================================================
# GET VBO ID
# ============================================================

@router.get(
    "/{notice_id}/vbo",
    response_model=APIResponse,
)
def get_demolition_vbo(
    notice_id: str,
    db: Session = Depends(get_db),
):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    return APIResponse(
        success=True,
        status=200,
        message="VBO ID retrieved successfully",
        data={
            "notice_id": record.notice_id,
            "vbo_id": record.vbo_id,
        },
        error=None,
    )

# ============================================================
# POST - CREATE
# ============================================================

@router.post(
    "/",
    response_model=APIResponse,
    status_code=201,
)
def create_demolition_record(
    data: DemolitionCreate,
    db: Session = Depends(get_db),
    

):
    existing = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == data.notice_id
        )
        .first()
    )

    if existing is not None:
        return APIResponse(
            success=False,
            status=409,
            message="Demolition record already exists",
            data=None,
            error={
                "code": "NOTICE_ID_EXISTS",
                "details": (
                    f"A demolition record with notice_id "
                    f"'{data.notice_id}' already exists."
                ),
            },
        )

    record = DemolitionStaging(
        notice_id=data.notice_id,
        title=data.title,
        publication_date=data.publication_date,
        address=data.address,
        postal_code=data.postal_code,
        municipality=data.municipality,
        latitude=data.latitude,
        longitude=data.longitude,
        city=data.city,
        location_source=data.location_source,
        pand_id=data.pand_id,
        bouwjaar=data.bouwjaar,
        status=data.status,
        geometry=data.geometry,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    data_response = DemolitionResponse.model_validate(record)

    return APIResponse(
        success=True,
        status=201,
        message="Demolition record created successfully",
        data=data_response,
        error=None,
    )   
# ============================================================
# PUT - UPDATE
# ============================================================

@router.put(
    "/{notice_id}",
    response_model=APIResponse,
)
def update_demolition_record(
    notice_id: str,
    data: DemolitionUpdate,
    db: Session = Depends(get_db),
   

):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)

    data_response = DemolitionResponse.model_validate(record)

    return APIResponse(
        success=True,
        status=200,
        message="Demolition record updated successfully",
        data=data_response,
        error=None,
    )


# ============================================================
# DELETE
# ============================================================

@router.delete(
    "/{notice_id}",
    response_model=APIResponse,
)
def delete_demolition_record(
    notice_id: str,
    db: Session = Depends(get_db),
    

):
    record = (
        db.query(DemolitionStaging)
        .filter(
            DemolitionStaging.notice_id == notice_id
        )
        .first()
    )

    if record is None:
        return APIResponse(
            success=False,
            status=404,
            message="Demolition record not found",
            data=None,
            error={
                "code": "DEMOLITION_NOT_FOUND",
                "details": (
                    f"No demolition record was found "
                    f"for notice_id '{notice_id}'."
                ),
            },
        )

    db.delete(record)
    db.commit()

    return APIResponse(
        success=True,
        status=200,
        message="Demolition record deleted successfully",
        data={
            "notice_id": notice_id,
        },
        error=None,
    )
