from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.response import APIResponse


router = APIRouter(
    prefix="/method-2",
    tags=["Method 2"]
)


# One row per building in public.method_2: the geometry-based estimate
# (3DBAG measurements x construction build-up per building type and age).
# Every column is returned, so the frontend has the full Method 2 record:
# building information, geometry, 3DBAG attributes, facade, roof, height,
# area, materials and CO2.
TABLE = "public.method_2"

# An address is searched the way people write it: street alone, with a
# house number, and with postal code and / or city behind it.
ADDRESS_MATCH = """
    LOWER(TRIM(address)) ILIKE LOWER(:search)

    OR LOWER(TRIM(CONCAT(address, ' ', house_number)))
        ILIKE LOWER(:search)

    OR LOWER(TRIM(CONCAT(address, ' ', house_number, ', ', city)))
        ILIKE LOWER(:search)

    OR LOWER(TRIM(CONCAT(address, ', ', city))) ILIKE LOWER(:search)

    OR LOWER(TRIM(CONCAT(address, ' ', city))) ILIKE LOWER(:search)

    OR LOWER(TRIM(CONCAT(address, ' ', house_number, ', ',
                         postal_code, ' ', city))) ILIKE LOWER(:search)

    OR LOWER(TRIM(CONCAT(address, ', ', postal_code, ' ', city)))
        ILIKE LOWER(:search)

    OR LOWER(TRIM(name)) ILIKE LOWER(:search)
"""


# ============================================================
# SEARCH BY ADDRESS
# ============================================================

@router.get("/search", response_model=APIResponse)
def search_method_2(
    response: Response,
    address: str = Query(
        ...,
        min_length=2,
        description="Street, optionally with house number, postal code "
                    "or city, e.g. 'Jan Provostlaan 16' or "
                    "'Jan Provostlaan 16, 3723RD Bilthoven'",
    ),
    limit: int = Query(25, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    search = address.strip()
    params = {"search": f"%{search}%"}

    try:
        rows = db.execute(
            text(f"""
                SELECT *
                FROM {TABLE}
                WHERE {ADDRESS_MATCH}
                ORDER BY city, address, house_number, pand_id
                LIMIT :limit OFFSET :offset
            """),
            {**params, "limit": limit, "offset": offset},
        ).mappings().all()

        total = db.execute(
            text(f"""
                SELECT COUNT(*) AS total
                FROM {TABLE}
                WHERE {ADDRESS_MATCH}
            """),
            params,
        ).mappings().one()["total"]

    except SQLAlchemyError as error:
        response.status_code = 500

        return APIResponse(
            success=False,
            status=500,
            message="Database error",
            data=None,
            error={
                "code": "DATABASE_ERROR",
                "details": str(getattr(error, "orig", error)),
            },
        )

    if not rows:
        response.status_code = 404

        return APIResponse(
            success=False,
            status=404,
            message="Method 2 record not found",
            data=None,
            error={
                "code": "METHOD_2_NOT_FOUND",
                "details": f"No Method 2 record was found for address '{search}'.",
            },
        )

    return APIResponse(
        success=True,
        status=200,
        message="Method 2 record retrieved successfully",
        data={
            "address": search,
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
            "items": [dict(row) for row in rows],
        },
        error=None,
    )
