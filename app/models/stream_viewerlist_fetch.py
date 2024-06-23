# app/models/stream_viewerlist_fetch.py
# SQLAlchemy model representing a single viewerlist fetch event of a target stream.

"""StreamViewerListFetch model and validators.

    Each row represents a single viewer-list fetch event of a target stream: the reception of the
    viewer list and associated metadata. (For our purposes, it is a set of ViewerSightings in a
    given channel during a scan.)

    The Pydantic BaseModels are split into two representing the relevant Twitch API Response data
    and the in-app metadata, and they're brought together by the
    merge_stream_viewerlist_fetch_data() function.

SQLAlchemy Model:
    StreamViewerListFetch: The SQLAlchemy model

Pydantic Models:
    StreamViewerListFetchTwitchAPIResponse: Pydantic model to validate Twitch API response data.
    StreamViewerListFetchAppData: Pydantic model to validate app-generated data.
    StreamViewerListFetchCreate: For making a new DB row.
    StreamViewerListFetchRead For retrieving and working with an existing DB row.

Merging Function:
    merge_stream_viewerlist_fetch_data
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import UUID4, BaseModel, Field, confloat, conint, constr, validator
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.db import Base


class StreamViewerListFetch(Base):
    """SQLAlchemy model representing a Stream Viewlist Fetch event from the Viewer List Fetcher.
    The Viewer List Fetcher will negotiate and handle the reception and parsing of the viewer list
    and will create rows in the ViewerSightings table for each name. This table tracks data of
    interest for the streams/channel(s) in question.

    ID Attributes:
        fetch_id (str): PK. UUID of this channel's Viewerlist Fetch Action.
        scanning_session_id (str): [FK] UUID of the parent Scanning Session.

    Attributes from our data collection:
        time_of_fetch (DateTime): Timestamp of when this fetch action took place.
        time_in_channel (float): Time elapsed by the Viewer List Fetcher worker in this stream's
            chat, clocked with time.perf_counter().

    Attributes from 'Get Streams' Twitch backend API endpoint:
        channel_owner_id (int): [FK] Twitch UUID of the channel this Viewerlist Fetch Action took
            place in; the broadcaster's account id.
        viewer_count (int): The reported viewer count for the stream at the time of the fetch.
        stream_id (int): Twitch UUID of the given stream/broadcast. Useful for tracking different
            streams for the same channel.
        stream_started_at (DateTime): The go-live timestamp of this live stream.
        category_id (int): Twitch UUID for the category.
        language (str): ISO 639-1 lanuage code of the stream.
        is_mature (bool): Whether the given channel is flagged as "For mature audiences."
        was_live (bool): Whether the channel was (still) live when the viewerlist fetch took place.

    Relationships:
        scanning_session (): many stream_viewerlist_fetches to one scanning_session
        twitch_user_data (): # one-to-one (this relationship mapping is for the user of THIS STREAM)
        viewer_sightings (): many viewer_sightings to one stream_viewerlist_fetch
    """

    __tablename__ = "stream_viewerlist_fetch"

    fetch_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    fetch_action_at = Column(DateTime, nullable=False)
    duration_of_fetch_action = Column(
        Float, nullable=False
    )  # use time.perf_counter() to measure, returns fractional seconds

    # foreign keys
    scanning_session_id = Column(
        CHAR(36), ForeignKey("scanning_sessions.scanning_session_id"), nullable=False
    )
    channel_owner_id = Column(
        BigInteger, ForeignKey("twitch_user_data.twitch_account_id"), nullable=False
    )  # 'user_id'
    category_id = Column(
        BigInteger, ForeignKey("stream_categories.category_id"), nullable=False
    )  # 'game_id'
    # category_name should be stored in the StreamCategories table if it's new to us.

    # 'Get Stream' response data
    viewer_count = Column(Integer, nullable=False)  # 'viewer_count' for this broadcast
    stream_id = Column(
        BigInteger, unique=True, nullable=False
    )  # 'id' UUID of this specific live-stream
    stream_started_at = Column(DateTime, nullable=False)  # 'started_at'
    language: Column(
        CHAR(2), nullable=False
    )  # 'language', ISO 639-1, always two char long.
    is_mature: Column(Boolean, nullable=False)  # 'is_mature'
    was_live: Column(
        Boolean, nullable=False
    )  # the 'type' field is either "live" or "" for down.

    # not tracked: thumbnail_url, title,

    # relationships
    scanning_session = relationship(
        "ScanningSession", back_populates="stream_viewerlist_fetches"
    )  # many stream_viewerlist_fetches to one scanning_session
    twitch_user_data = relationship(
        "TwitchUserData", back_populates="stream_viewerlist_fetch"
    )  # one-to-one (this relationship mapping is for the user of THIS STREAM)
    viewer_sightings = relationship(
        "ViewerSighting", back_populates="stream_viewerlist_fetch"
    )  # many viewer_sightings to one stream_viewerlist_fetch
    stream_category = relationship(
        "StreamCategory", back_populates="stream_viewerlist_fetch"
    )

    # indexes
    __table_args__ = (
        Index("ix_scanning_session_id", "scanning_session_id"),
        Index("ix_channel_owner_id", "channel_owner_id"),
        Index("ix_category_id", "category_id"),
    )


class StreamViewerListFetchTwitchAPIResponse(BaseModel):
    viewer_count: conint(ge=0) = Field(..., alias="viewer_count")
    stream_id: conint(gt=0) = Field(..., alias="id")
    stream_started_at: datetime = Field(..., alias="started_at")
    language: constr(regex=r"^[a-z]{2}$") = Field(..., alias="language")
    is_mature: bool = Field(..., alias="is_mature")
    was_live: bool = Field(..., alias="type")

    @validator("was_live", pre=True)
    def convert_type_to_was_live(cls, v: Optional[str]) -> bool:
        if v is None:
            raise ValueError("'type' field in Twitch response cannot be None.")
        if isinstance(v, str):
            if v == "live":
                return True
            elif v == "":
                return False
        raise ValueError(
            "Could not convert 'type' in Twitch response.",
        )

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class StreamViewerListFetchAppData(BaseModel):
    fetch_action_at: datetime = Field(..., alias="fetch_action_at")
    duration_of_fetch_action: confloat(ge=0.0) = Field(
        ..., alias="duration_of_fetch_action"
    )
    scanning_session_id: UUID4
    channel_owner_id: int
    category_id: int

    class Config:
        orm_mode = True


class StreamViewerListFetchCreate(BaseModel):
    # Combine the TwitchAPI response with the AppData using the merge function in this file.
    scanning_session_id: UUID
    channel_owner_id: int
    category_id: int
    fetch_action_at: datetime
    duration_of_fetch_action: confloat(ge=0.0)
    viewer_count: conint(ge=0)
    stream_id: conint(gt=0)
    stream_started_at: datetime
    language: constr(regex=r"^[a-z]{2}$")
    is_mature: bool
    was_live: bool

    class Config:
        orm_mode = True


class StreamViewerListFetchRead(StreamViewerListFetchCreate):
    fetch_id: UUID4

    class Config:
        orm_mode = True


def merge_stream_viewerlist_fetch_data(
    api_data: StreamViewerListFetchTwitchAPIResponse,
    app_data: StreamViewerListFetchAppData,
) -> StreamViewerListFetchCreate:
    combined_data = {
        **api_data.dict(),
        **app_data.dict(),
    }
    return StreamViewerListFetchCreate(**combined_data)
