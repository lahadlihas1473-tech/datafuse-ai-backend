from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class DemolitionBase(BaseModel):
    title: Optional[str] = None
    publication_date: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    municipality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    location_source: Optional[str] = None

    # BAG
    pand_id: Optional[str] = None
    bouwjaar: Optional[int] = None
    status: Optional[str] = None
    geometry: Optional[Any] = None
    geometry_area_m2: Optional[float] = None
    vbo_id: Optional[str] = None


class DemolitionCreate(DemolitionBase):
    notice_id: str


class DemolitionUpdate(BaseModel):
    title: Optional[str] = None
    publication_date: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    municipality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    location_source: Optional[str] = None

    # BAG
    pand_id: Optional[str] = None
    bouwjaar: Optional[int] = None
    status: Optional[str] = None
    geometry: Optional[Any] = None
    geometry_area_m2: Optional[float] = None
    vbo_id: Optional[str] = None


class DemolitionResponse(DemolitionBase):
    notice_id: str

    model_config = ConfigDict(from_attributes=True)


class DemolitionLocationResponse(BaseModel):
    address: Optional[str] = None
    postal_code: Optional[str] = None
    municipality: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: Optional[str] = None


class DemolitionBAGResponse(BaseModel):
    pand_id: Optional[str] = None
    bouwjaar: Optional[int] = None
    status: Optional[str] = None
    geometry: Optional[Any] = None
    geometry_area_m2: Optional[float] = None
    vbo_id: Optional[str] = None


class DemolitionGeometryResponse(BaseModel):
    geometry: Optional[Any] = None
    pand_id: Optional[str] = None
    geometry_area_m2: Optional[float] = None
    vbo_id: Optional[str] = None