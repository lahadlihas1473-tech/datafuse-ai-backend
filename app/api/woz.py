"""Method 1 Estimated WOZ Value per building, with the calculation behind it.

The values are calculated by dataset/estimate_woz_method1.py and stored in
the est_woz_* columns of material_estimation_final. They are looked up on
pand_id. Only the columns that exist are read, so an endpoint keeps working
on a database that has fewer (or none) of them.
"""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


TABLE = "material_estimation_final"

LABEL = "Estimated WOZ Value"

FORMULA = "GO m2 x base EUR/m2 x type factor x age factor"

DISCLAIMER = (
    "Model estimate, not an official WOZ value. Official WOZ values are set "
    "by municipalities; this estimate is not issued by or taken from a "
    "municipality, Kadaster or the Waarderingskamer."
)

# (column, key in the API response, type)
FIELDS = [
    ("est_woz_value_eur", "value_eur", int),
    ("est_woz_reference_year", "reference_year", int),
    ("est_woz_gemeentecode", "gemeentecode", str),
    ("est_woz_gemeentenaam", "gemeente", str),
    ("est_woz_location_source", "location_source", str),
    ("est_woz_cbs_avg_woz_eur", "cbs_avg_woz_eur", int),
    ("est_woz_cbs_avg_floor_area_m2", "cbs_avg_floor_area_m2", float),
    ("est_woz_base_eur_per_m2", "base_eur_per_m2", float),
    ("est_woz_type_factor", "type_factor", float),
    ("est_woz_type_basis", "type_basis", str),
    ("est_woz_age_factor", "age_factor", float),
    ("est_woz_age_band", "age_band", str),
    ("est_woz_eur_per_m2", "eur_per_m2", float),
    ("est_woz_go_m2", "go_m2", float),
    ("est_woz_imputed", "imputed", str),
]

# Inputs from BAG, read alongside so the breakdown can show them
INPUTS = ["bouwjaar", "pand_gebruiksdoel", "go_m2"]

_columns: set[str] = set()


def _available_columns(db: Session) -> set[str]:
    """The est_woz_* columns in the database (re-checked until found)."""
    global _columns

    if not _columns:
        _columns = set(db.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table
              AND column_name LIKE 'est\\_woz\\_%'
        """), {"table": TABLE}).scalars())

    return _columns


def _convert(value, kind):
    if value is None:
        return None
    if kind is int:
        return int(round(float(value)))
    if kind is float:
        return float(value)
    return value


def woz_by_pand_id(db: Session, pand_ids: list[str]) -> dict[str, dict]:
    """pand_id -> estimated_woz object, for the pand_ids that have a value."""
    available = _available_columns(db)
    ids = [pand_id for pand_id in pand_ids if pand_id]

    if "est_woz_value_eur" not in available or not ids:
        return {}

    columns = [column for column, _, _ in FIELDS if column in available]
    rows = db.execute(
        text(f"""
            SELECT pand_id, {", ".join(INPUTS + columns)}
            FROM {TABLE}
            WHERE pand_id = ANY(:ids)
              AND est_woz_value_eur IS NOT NULL
        """),
        {"ids": ids},
    ).mappings().all()

    return {row["pand_id"]: estimated_woz(row) for row in rows}


def estimated_woz(row) -> Optional[dict]:
    """The estimated_woz object of one row (None without a value)."""
    if row.get("est_woz_value_eur") is None:
        return None

    woz = {"label": LABEL}
    woz.update({
        key: _convert(row.get(column), kind) for column, key, kind in FIELDS
    })
    woz["inputs"] = {
        "bouwjaar": row.get("bouwjaar"),
        "gebruiksdoel": row.get("pand_gebruiksdoel"),
        "go_m2": _convert(row.get("go_m2"), float),
    }
    woz["formula"] = FORMULA
    woz["disclaimer"] = DISCLAIMER

    return woz
