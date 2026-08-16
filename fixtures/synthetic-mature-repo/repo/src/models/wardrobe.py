from sqlalchemy import Column, Integer, String

from src.db import Base


class Wardrobe(Base):
    __tablename__ = "wardrobes"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, nullable=False)
    name = Column(String(120), nullable=False)


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True)
    wardrobe_id = Column(Integer, nullable=False)
    label = Column(String(120), nullable=False)