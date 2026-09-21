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


def city_rank_sql(city: str, municipality: str) -> str:
    """
    SQL rank for a row: 0 = city is the search term, 1 = city/municipality
    starts with it, 2 = any other match. Lower sorts first.
    """
    return f"""
        CASE
            WHEN :term IS NULL THEN 2
            WHEN LOWER(TRIM({city})) = LOWER(:term)
              OR LOWER(TRIM({municipality})) = LOWER(:term) THEN 0
            WHEN {city} ILIKE :prefix ESCAPE '\\'
              OR {municipality} ILIKE :prefix ESCAPE '\\' THEN 1
            ELSE 2
        END
    """


def contains_any_sql(columns: list[str]) -> str:
    """WHERE clause: no search, or any column contains the term."""
    matches = " OR ".join(
        f"{column} ILIKE :pattern ESCAPE '\\'" for column in columns
    )
    return f"(:term IS NULL OR {matches})"
