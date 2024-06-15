# app/models/observation.py

from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.db import Base


class Observation(Base):
    __tablename__ = "observations"

    observation_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    viewerlist_fetch_id = Column(
        CHAR(36), ForeignKey("channel_viewerlist_fetch.fetch_id"), nullable=False
    )
    viewer_name = Column(String(40), nullable=False)

    # Relationships
    channel_viewerlist_fetch = relationship(
        "ChannelViewerListFetch", back_populates="observations"
    )
