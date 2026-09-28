"""Shared helpers for the ranked text search used by /notices and /addresses."""

from typing import Optional


def like_pattern(search: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    escaped = (
        search.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


def search_params(search: Optional[str]) -> dict:
    """
    Bind parameters for a ranked search.

    `term` is the exact (case-insensitive) value, `prefix` a starts-with
    pattern and `pattern` a contains pattern. All are None without search.
    """
    term = (search or "").strip()

    if not term:
        return {"term": None, "prefix": None, "pattern": None}

    pattern = like_pattern(term)

    return {
        "term": term,
        "prefix": pattern[1:],   # drop the leading % → starts-with
        "pattern": pattern,
    }


# Parameters are cast to TEXT: with psycopg 3 the server binds them and
# cannot infer a type for a bare ":term IS NULL".
TERM = "CAST(:term AS TEXT)"
PREFIX = "CAST(:prefix AS TEXT)"
PATTERN = "CAST(:pattern AS TEXT)"


def city_rank_sql(city: str, municipality: str) -> str:
    """
    SQL rank for a row: 0 = city is the search term, 1 = city/municipality
    starts with it, 2 = any other match. Lower sorts first.
    """
    return f"""
        CASE
            WHEN {TERM} IS NULL THEN 2
            WHEN LOWER(TRIM({city})) = LOWER({TERM})
              OR LOWER(TRIM({municipality})) = LOWER({TERM}) THEN 0
            WHEN {city} ILIKE {PREFIX} ESCAPE '\\'
              OR {municipality} ILIKE {PREFIX} ESCAPE '\\' THEN 1
            ELSE 2
        END
    """


def contains_any_sql(columns: list[str]) -> str:
    """WHERE clause: no search, or any column contains the term."""
    matches = " OR ".join(
        f"{column} ILIKE {PATTERN} ESCAPE '\\'" for column in columns
    )
    return f"({TERM} IS NULL OR {matches})"
