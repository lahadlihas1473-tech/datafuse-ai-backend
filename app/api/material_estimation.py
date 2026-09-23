from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db


router = APIRouter(
    prefix="/material-estimation",
    tags=["Material Estimation"]
)


# ============================================================
# MATERIAL LABELS
# ============================================================

MATERIAL_LABELS = {
    "steel": ("Staal", "Steel"),
    "copper": ("Koper", "Copper"),
    "aluminium": ("Aluminium", "Aluminium"),
    "other_metal": ("Overig metaal", "Other Metal"),
    "wood": ("Hout", "Wood"),
    "concrete": ("Beton", "Concrete"),
    "brick": ("Baksteen", "Brick"),
    "other_construction_minerals": (
        "Overige constructie mineralen",
        "Other Construction Minerals"
    ),
    "glass": ("Glas", "Glass"),
    "ceramics": ("Keramiek", "Ceramics"),
    "plastic": ("Plastic", "Plastic"),
    "insulation": ("Isolatie", "Insulation"),
    "other": ("Overig", "Other"),
    "total": ("Totaal", "Total"),
}


# ============================================================
# HELPER FUNCTION
# ============================================================

def material_values(result, prefix):
    """
    Convert a material's tonnes and CO2 values into
    tonnes and kilograms.

    Example:
        prefix = "koper"

    Reads:
        koper_tonnes
        koper_co2_tonnes

    Returns:
        tonnes
        kg
        co2_tonnes
        co2_kg
    """

    tonnes = result[f"{prefix}_tonnes"]
    co2_tonnes = result[f"{prefix}_co2_tonnes"]

    return {
        "tonnes": tonnes,
        "kg": tonnes * 1000,
        "co2_tonnes": co2_tonnes,
        "co2_kg": co2_tonnes * 1000
    }


# ============================================================
# SEARCH MATERIAL ESTIMATION BY ADDRESS
# ============================================================

@router.get("/search")
def search_material_estimation(
    address: str = Query(
        ...,
        min_length=2,
        description=(
            "Search building material estimation by address. "
            "Example: Jan Provostlaan 16, Bilthoven"
        ),
    ),
    db: Session = Depends(get_db)
):
    search = address.strip()

    query = text("""
        SELECT
            address,
            house_number,
            postal_code,
            city,

            -- Main materials
            staal_tonnes,
            staal_co2_tonnes,

            hout_tonnes,
            hout_co2_tonnes,

            beton_tonnes,
            beton_co2_tonnes,

            baksteen_tonnes,
            baksteen_co2_tonnes,

            glas_tonnes,
            glas_co2_tonnes,

            overig_tonnes,
            overig_co2_tonnes,

            -- Building identifier
            pand_id,

            -- Additional materials
            koper_tonnes,
            koper_co2_tonnes,

            aluminium_tonnes,
            aluminium_co2_tonnes,

            overig_metaal_tonnes,
            overig_metaal_co2_tonnes,

            overige_constructie_mineralen_tonnes,
            overige_constructie_mineralen_co2_tonnes,

            keramiek_tonnes,
            keramiek_co2_tonnes,

            plastic_tonnes,
            plastic_co2_tonnes,

            isolatie_tonnes,
            isolatie_co2_tonnes,

            -- Totals
            total_material_mass_tonnes,
            total_co2_tonnes

        FROM public.material_estimation_final

        WHERE
            LOWER(TRIM(address)) ILIKE LOWER(:search)

            OR LOWER(
                TRIM(
                    CONCAT(
                        address,
                        ', ',
                        city
                    )
                )
            ) ILIKE LOWER(:search)

            OR LOWER(
                TRIM(
                    CONCAT(
                        address,
                        ' ',
                        city
                    )
                )
            ) ILIKE LOWER(:search)

            OR LOWER(
                TRIM(
                    CONCAT(
                        address,
                        ', ',
                        postal_code,
                        ' ',
                        city
                    )
                )
            ) ILIKE LOWER(:search)

        ORDER BY id

        LIMIT 1
    """)

    result = db.execute(
        query,
        {
            "search": f"%{search}%"
        }
    ).mappings().first()

    # ========================================================
    # NOT FOUND
    # ========================================================

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No material estimation found for this address"
        )

    # ========================================================
    # MATERIAL CALCULATIONS
    # ========================================================

    materials = {

        # ----------------------------------------------------
        # Steel
        # ----------------------------------------------------

        "steel": {
            "tonnes": result["staal_tonnes"],
            "kg": result["staal_tonnes"] * 1000,
            "co2_tonnes": result["staal_co2_tonnes"],
            "co2_kg": result["staal_co2_tonnes"] * 1000
        },

        # ----------------------------------------------------
        # Wood
        # ----------------------------------------------------

        "wood": {
            "tonnes": result["hout_tonnes"],
            "kg": result["hout_tonnes"] * 1000,
            "co2_tonnes": result["hout_co2_tonnes"],
            "co2_kg": result["hout_co2_tonnes"] * 1000
        },

        # ----------------------------------------------------
        # Concrete
        # ----------------------------------------------------

        "concrete": {
            "tonnes": result["beton_tonnes"],
            "kg": result["beton_tonnes"] * 1000,
            "co2_tonnes": result["beton_co2_tonnes"],
            "co2_kg": result["beton_co2_tonnes"] * 1000
        },

        # ----------------------------------------------------
        # Brick
        # ----------------------------------------------------

        "brick": {
            "tonnes": result["baksteen_tonnes"],
            "kg": result["baksteen_tonnes"] * 1000,
            "co2_tonnes": result["baksteen_co2_tonnes"],
            "co2_kg": result["baksteen_co2_tonnes"] * 1000
        },

        # ----------------------------------------------------
        # Glass
        # ----------------------------------------------------

        "glass": {
            "tonnes": result["glas_tonnes"],
            "kg": result["glas_tonnes"] * 1000,
            "co2_tonnes": result["glas_co2_tonnes"],
            "co2_kg": result["glas_co2_tonnes"] * 1000
        },

        # ----------------------------------------------------
        # Other
        # ----------------------------------------------------

        "other": {
            "tonnes": result["overig_tonnes"],
            "kg": result["overig_tonnes"] * 1000,
            "co2_tonnes": result["overig_co2_tonnes"],
            "co2_kg": result["overig_co2_tonnes"] * 1000
        },

        # ----------------------------------------------------
        # Additional materials
        # ----------------------------------------------------

        "copper": material_values(
            result,
            "koper"
        ),

        "aluminium": material_values(
            result,
            "aluminium"
        ),

        "other_metal": material_values(
            result,
            "overig_metaal"
        ),

        "other_construction_minerals": material_values(
            result,
            "overige_constructie_mineralen"
        ),

        "ceramics": material_values(
            result,
            "keramiek"
        ),

        "plastic": material_values(
            result,
            "plastic"
        ),

        "insulation": material_values(
            result,
            "isolatie"
        ),

        # ----------------------------------------------------
        # Total
        # ----------------------------------------------------

        "total": {
            "tonnes": result["total_material_mass_tonnes"],
            "kg": result["total_material_mass_tonnes"] * 1000,
            "co2_tonnes": result["total_co2_tonnes"],
            "co2_kg": result["total_co2_tonnes"] * 1000
        }
    }

    # ========================================================
    # ADD LABELS
    # ========================================================

    for key, (name_nl, name_en) in MATERIAL_LABELS.items():

        materials[key].update({
            "label": f"{name_nl} ({name_en})",
            "name_nl": name_nl,
            "name_en": name_en
        })

    # ========================================================
    # FULL ADDRESS
    # ========================================================

    full_address = (
        f"{result['address']}, "
        f"{result['postal_code']} "
        f"{result['city']}"
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "success": True,

        "data": {
            "address": full_address,

            "materials": materials,

            "pand_id": result["pand_id"]
        }
    }