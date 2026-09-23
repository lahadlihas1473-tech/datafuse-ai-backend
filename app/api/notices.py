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
    prefix="/notices",
    tags=["Notices"]
)


# One row per estimated building in material_estimation_final: the 1081
# demolition notices plus Jan Provostlaan 16, which has a pand_id but no
# notice. Only these fields are exposed.
NOTICE_COLUMNS = """
    notice_id,
    pand_id,
    title,
    publication_date
"""

TABLE = "material_estimation_final"

# Searchable, even though only the columns above are returned
SEARCH_COLUMNS = [
    "city",
    "municipality",
    "title",
    "address",
    "postal_code",
    "notice_id",
    "pand_id",
]

RANK = city_rank_sql("city", "municipality")
MATCHES = contains_any_sql(SEARCH_COLUMNS)


# ============================================================
# GET ALL (with ranked search)
# ============================================================

@router.get("", response_model=APIResponse)
def get_notices(
    search: Optional[str] = Query(
        None,
        description="City, title, address, postal code or notice ID. "
                    "Notices in a matching city are listed first.",
    ),
    limit: int = Query(25, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    params = search_params(search)

    summary = db.execute(
        text(f"""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE {RANK} < 2) AS city_matches
            FROM {TABLE}
            WHERE {MATCHES}
        """),
        params,
    ).mappings().one()

    rows = db.execute(
        text(f"""
            SELECT {NOTICE_COLUMNS}
            FROM {TABLE}
            WHERE {MATCHES}
            ORDER BY
                {RANK},
                publication_date DESC NULLS LAST,
                notice_id
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    return APIResponse(
        success=True,
        status=200,
        message="Notices retrieved successfully",
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
# GET SINGLE NOTICE
# ============================================================

@router.get("/{notice_id}", response_model=APIResponse)
def get_notice(
    notice_id: str,
    response: Response,
    db: Session = Depends(get_db),
):
    row = db.execute(
        text(f"""
            SELECT {NOTICE_COLUMNS}
            FROM {TABLE}
            WHERE notice_id = :notice_id
        """),
        {"notice_id": notice_id},
    ).mappings().first()

    if row is None:
        response.status_code = 404

        return APIResponse(
            success=False,
            status=404,
            message="Notice not found",
            data=None,
            error={
                "code": "NOTICE_NOT_FOUND",
                "details": f"No notice was found for notice_id '{notice_id}'.",
            },
        )

    return APIResponse(
        success=True,
        status=200,
        message="Notice retrieved successfully",
        data=dict(row),
        error=None,
    )
