from sqlalchemy import Column, Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database.database import Base


class DemolitionStaging(Base):
    __tablename__ = "demolition_staging"
    __table_args__ = {"schema": "public"}

    notice_id = Column(Text, primary_key=True)

    title = Column(Text)
    publication_date = Column(Text)
    address = Column(Text)
    postal_code = Column(Text)
    municipality = Column(Text)

    latitude = Column(Float)
    longitude = Column(Float)

    city = Column(Text)
    location_source = Column(Text)

    pand_id = Column(Text)
    bouwjaar = Column(Integer)
    status = Column(Text)

    geometry = Column(JSONB)
    geometry_area_m2 = Column(Float)
    vbo_id = Column(Text)