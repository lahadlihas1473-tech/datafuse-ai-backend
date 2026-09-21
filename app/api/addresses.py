from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.search_utils import (
    city_rank_sql,
    contains_any_sql,
    search_params,
)
from app.database.session import get_db
from app.schemas.response import APIResponse


router = APIRouter(
    prefix="/addresses",
    tags=["Addresses"]
)


# material_estimation_final is the table with separate address,
# house_number, postal_code and city columns. Several notices can share
# an address, so rows are grouped on a normalised key: case, surrounding
# spaces and spaces inside postal codes are ignored.
UNIQUE_ADDRESSES = f"""
    SELECT
        MIN(TRIM(address)) AS address,
        MIN(TRIM(house_number)) AS house_number,
        MIN(UPPER(REPLACE(TRIM(postal_code), ' ', ''))) AS postal_code,
        MIN(TRIM(city)) AS city,
        MIN({city_rank_sql("city", "municipality")}) AS match_rank
    FROM material_estimation_final
    WHERE {{where}}
    GROUP BY
        LOWER(TRIM(address)),
        LOWER(TRIM(house_number)),
        UPPER(REPLACE(TRIM(postal_code), ' ', '')),
        LOWER(TRIM(city))
"""

SEARCH_COLUMNS = [
    "city",
    "municipality",
    "address",
    "house_number",
    "postal_code",
    "CONCAT(address, ' ', house_number)",
]

ADDRESS_FIELDS = "address, house_number, postal_code, city"


# ============================================================
# GET ALL UNIQUE ADDRESSES (with ranked search)
# ============================================================

@router.get("", response_model=APIResponse)
def get_addresses(
    search: Optional[str] = Query(
        None,
        description="City, address, house number or postal code. "
                    "Addresses in a matching city are listed first.",
    ),
    limit: int = Query(25, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    params = search_params(search)
    unique = UNIQUE_ADDRESSES.format(where=contains_any_sql(SEARCH_COLUMNS))

    summary = db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE match_rank < 2) AS city_matches
            FROM ({unique}) AS unique_addresses
        """),
        params,
    ).mappings().one()

    rows = db.execute(
        text(f"""
            SELECT {ADDRESS_FIELDS}
            FROM ({unique}) AS unique_addresses
            ORDER BY match_rank, city, address, house_number
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    return APIResponse(
        success=True,
        status=200,
        message="Addresses retrieved successfully",
        data={
            "search": params["term"],
            "total": summary["total"],
            # Leading results whose city matches the search
            "city_matches": summary["city_matches"] if params["term"] else 0,
            "limit": limit,
            "offset": offset,
            "items": [dict(row) for row in rows],
        },
        error=None,
    )


# ============================================================
# GET UNIQUE ADDRESSES FOR ONE ADDRESS
# ============================================================

@router.get("/{address:path}", response_model=APIResponse)
def get_address(
    address: str,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Exact, case-insensitive match on the address, or on
    "address house_number" (e.g. "Bosstraat 122"). One street can
    return several unique addresses.
    """
    unique = UNIQUE_ADDRESSES.format(where="""
        LOWER(TRIM(address)) = LOWER(TRIM(:address))
        OR LOWER(CONCAT(TRIM(address), ' ', TRIM(house_number)))
           = LOWER(TRIM(:address))
    """)

    rows = db.execute(
        text(f"""
            SELECT {ADDRESS_FIELDS}
            FROM ({unique}) AS unique_addresses
            ORDER BY city, house_number
        """),
        {"address": address, "term": None, "prefix": None},
    ).mappings().all()

    if not rows:
        response.status_code = 404

        return APIResponse(
            success=False,
            status=404,
            message="Address not found",
            data=None,
            error={
                "code": "ADDRESS_NOT_FOUND",
                "details": f"No address was found matching '{address}'.",
            },
        )

    return APIResponse(
        success=True,
        status=200,
        message="Address retrieved successfully",
        data=[dict(row) for row in rows],
        error=None,
    )
