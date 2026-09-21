from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db


router = APIRouter(
    prefix="/material-estimation",
    tags=["Material Estimation"]
)


# Response key -> (Dutch name, English name), in display order
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


@router.get("/search")
def search_material_estimation(
    address: str = Query(..., min_length=2),
    db: Session = Depends(get_db)
):
    search = address.strip()

    query = text("""
        SELECT
            address,
            house_number,
            postal_code,
            city,

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

            pand_id,

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

            total_material_mass_tonnes,
            total_co2_tonnes

        FROM material_estimation_final

        WHERE
            address ILIKE :search
            OR CONCAT(address, ' ', house_number) ILIKE :search
            OR CONCAT(address, ' ', house_number, ', ', city) ILIKE :search

        ORDER BY id
        LIMIT 1
    """)

    result = db.execute(
        query,
        {"search": f"%{search}%"}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No material estimation found for this address"
        )

    materials = {
        "steel": {
            "tonnes": result["staal_tonnes"],
            "kg": result["staal_tonnes"] * 1000,
            "co2_tonnes": result["staal_co2_tonnes"],
            "co2_kg": result["staal_co2_tonnes"] * 1000
        },

        "wood": {
            "tonnes": result["hout_tonnes"],
            "kg": result["hout_tonnes"] * 1000,
            "co2_tonnes": result["hout_co2_tonnes"],
            "co2_kg": result["hout_co2_tonnes"] * 1000
        },

        "concrete": {
            "tonnes": result["beton_tonnes"],
            "kg": result["beton_tonnes"] * 1000,
            "co2_tonnes": result["beton_co2_tonnes"],
            "co2_kg": result["beton_co2_tonnes"] * 1000
        },

        "brick": {
            "tonnes": result["baksteen_tonnes"],
            "kg": result["baksteen_tonnes"] * 1000,
            "co2_tonnes": result["baksteen_co2_tonnes"],
            "co2_kg": result["baksteen_co2_tonnes"] * 1000
        },

        "glass": {
            "tonnes": result["glas_tonnes"],
            "kg": result["glas_tonnes"] * 1000,
            "co2_tonnes": result["glas_co2_tonnes"],
            "co2_kg": result["glas_co2_tonnes"] * 1000
        },

        "other": {
            "tonnes": result["overig_tonnes"],
            "kg": result["overig_tonnes"] * 1000,
            "co2_tonnes": result["overig_co2_tonnes"],
            "co2_kg": result["overig_co2_tonnes"] * 1000
        },

        "copper": material_values(result, "koper"),
        "aluminium": material_values(result, "aluminium"),
        "other_metal": material_values(result, "overig_metaal"),
        "other_construction_minerals": material_values(
            result, "overige_constructie_mineralen"
        ),
        "ceramics": material_values(result, "keramiek"),
        "plastic": material_values(result, "plastic"),
        "insulation": material_values(result, "isolatie"),

        "total": {
            "tonnes": result["total_material_mass_tonnes"],
            "kg": result["total_material_mass_tonnes"] * 1000,
            "co2_tonnes": result["total_co2_tonnes"],
            "co2_kg": result["total_co2_tonnes"] * 1000
        }
    }

    # Display labels only; keys and values stay unchanged
    for key, (name_nl, name_en) in MATERIAL_LABELS.items():
        materials[key].update({
            "label": f"{name_nl} ({name_en})",
            "name_nl": name_nl,
            "name_en": name_en
        })

    return {
        "success": True,
        "data": {
            "address": (
                f"{result['address']} "
                f"{result['house_number']}, "
                f"{result['postal_code']} "
                f"{result['city']}"
            ).strip(),

            "materials": materials,

            "pand_id": result["pand_id"]
        }
    }


def material_values(result, column: str):
    # Missing values stay None instead of failing the multiplication
    tonnes = result[f"{column}_tonnes"]
    co2_tonnes = result[f"{column}_co2_tonnes"]

    return {
        "tonnes": tonnes,
        "kg": tonnes * 1000 if tonnes is not None else None,
        "co2_tonnes": co2_tonnes,
        "co2_kg": co2_tonnes * 1000 if co2_tonnes is not None else None
    }