
from fastapi import APIRouter
import psycopg2
from psycopg2.extras import RealDictCursor


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/materials",
    tags=["Materials"]
)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "datafuse",
    "user": "postgres",
    "password": "hazard7"
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================
# GENERIC MATERIAL FUNCTION
# ============================================================

def get_material(
    pand_id: str,
    column: str,
    material_nl: str,
    material_en: str
):

    conn = get_connection()

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:

            # Column names come only from the fixed endpoint
            # definitions below, not from user input.
            query = f"""
                SELECT
                    pand_id,
                    typegebouw,
                    cohort,
                    material_profile_id,
                    go_m2,
                    go_source,

                    {column}_tonnes,
                    {column}_co2_factor,
                    {column}_co2_tonnes

                FROM material_estimation_final

                WHERE pand_id = %s

                LIMIT 1
            """

            cursor.execute(query, (pand_id,))

            row = cursor.fetchone()

            # ------------------------------------------------
            # BUILDING NOT FOUND
            # ------------------------------------------------

            if not row:

                return {
                    "success": False,
                    "status": 404,
                    "message": "Building not found",
                    "data": None,
                    "error": {
                        "code": "PAND_NOT_FOUND",
                        "pand_id": pand_id
                    }
                }

            # ------------------------------------------------
            # MATERIAL VALUES
            # ------------------------------------------------

            tonnes = row[f"{column}_tonnes"]

            co2_factor = row[f"{column}_co2_factor"]

            co2_tonnes = row[f"{column}_co2_tonnes"]

            # Convert tonnes CO2 → kg CO2
            co2_kg = None

            if co2_tonnes is not None:
                co2_kg = co2_tonnes * 1000

            # ------------------------------------------------
            # RESPONSE DATA
            # ------------------------------------------------

            data = {
                "pand_id": row["pand_id"],

                "material": material_nl,
                "material_name_en": material_en,
                "material_label": f"{material_nl} ({material_en})",

                "typegebouw": row["typegebouw"],
                "cohort": row["cohort"],
                "material_profile_id": row["material_profile_id"],

                "go_m2": row["go_m2"],
                "go_source": row["go_source"],

                "estimated_quantity_tonnes": tonnes,

                "co2_factor_tco2e_per_tonne": co2_factor,

                "estimated_co2_tonnes": co2_tonnes,
                "estimated_co2_kg": co2_kg
            }

            # ------------------------------------------------
            # SUCCESS RESPONSE
            # ------------------------------------------------

            return {
                "success": True,
                "status": 200,
                "message": (
                    f"{material_nl} ({material_en}) "
                    "material estimation completed successfully"
                ),
                "data": data,
                "error": None
            }

    finally:

        conn.close()


# ============================================================
# 1. STAAL / STEEL
# ============================================================

@router.get("/staal(steel)/{pand_id}")
def get_staal(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="staal",
        material_nl="Staal",
        material_en="Steel"
    )


# ============================================================
# 2. KOPER / COPPER
# ============================================================

@router.get("/koper(copper)/{pand_id}")
def get_koper(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="koper",
        material_nl="Koper",
        material_en="Copper"
    )


# ============================================================
# 3. ALUMINIUM / ALUMINIUM
# ============================================================

@router.get("/aluminium(aluminium)/{pand_id}")
def get_aluminium(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="aluminium",
        material_nl="Aluminium",
        material_en="Aluminium"
    )


# ============================================================
# 4. OVERIG METAAL / OTHER METAL
# ============================================================

@router.get("/overig_metaal(other-metal)/{pand_id}")
def get_overig_metaal(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="overig_metaal",
        material_nl="Overig metaal",
        material_en="Other Metal"
    )


# ============================================================
# 5. HOUT / WOOD
# ============================================================

@router.get("/hout(wood)/{pand_id}")
def get_hout(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="hout",
        material_nl="Hout",
        material_en="Wood"
    )


# ============================================================
# 6. BETON / CONCRETE
# ============================================================

@router.get("/beton(concrete)/{pand_id}")
def get_beton(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="beton",
        material_nl="Beton",
        material_en="Concrete"
    )


# ============================================================
# 7. BAKSTEEN / BRICK
# ============================================================

@router.get("/baksteen(brick)/{pand_id}")
def get_baksteen(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="baksteen",
        material_nl="Baksteen",
        material_en="Brick"
    )


# ============================================================
# 8. OVERIGE CONSTRUCTIE MINERALEN
# ============================================================

@router.get(
    "/overige_constructiemineralen(other-construction-minerals)/{pand_id}"
)
def get_overige_constructie_mineralen(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="overige_constructie_mineralen",
        material_nl="Overige constructie mineralen",
        material_en="Other Construction Minerals"
    )


# ============================================================
# 9. GLAS / GLASS
# ============================================================

@router.get("/glas(glass)/{pand_id}")
def get_glas(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="glas",
        material_nl="Glas",
        material_en="Glass"
    )


# ============================================================
# 10. KERAMIEK / CERAMICS
# ============================================================

@router.get("/keramiek(ceramics)/{pand_id}")
def get_keramiek(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="keramiek",
        material_nl="Keramiek",
        material_en="Ceramics"
    )


# ============================================================
# 11. PLASTIC / PLASTIC
# ============================================================

@router.get("/plastic(plastic)/{pand_id}")
def get_plastic(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="plastic",
        material_nl="Plastic",
        material_en="Plastic"
    )


# ============================================================
# 12. ISOLATIE / INSULATION
# ============================================================

@router.get("/isolatie(insulation)/{pand_id}")
def get_isolatie(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="isolatie",
        material_nl="Isolatie",
        material_en="Insulation"
    )


# ============================================================
# 13. OVERIG / OTHER
# ============================================================

@router.get("/overig(other)/{pand_id}")
def get_overig(pand_id: str):

    return get_material(
        pand_id=pand_id,
        column="overig",
        material_nl="Overig",
        material_en="Other"
    )
