# app/models/suspect.py
# SQLAlchemy model representing Twitch Accounts that have been flagged by the classfier.
"""We all agree a Twitch account is a bot if:
    - it's in thousands upon thousands of channel viewerlists concurrently
    - it has 200ish followers and follows no one itself
    - it has never streamed before and still has lots of followers
    - it never speaks in any channel
    - it remains resident for days and days, long after the stream it was in has ended

* * * THE INITIAL PLAN IS TO TRACK 'PURPLE' AND HIGHER. * * *

The SuspiciousBots table will track details about Twitch Accounts which have been observed by the
bot (during its scans) to be in large volumes of channels concurrently, well beyond the prescribed
100 concurrent channels that Twitch's TOS allows. It will also track accounts below that level of
concurrency as well, but as they're within TOS, they will bear a low SuspicionLevel.

NOTE This particular model will probably see the most change and extension as we learn more and
discover new questions.

Classes:
    SuspicionReason: Enum for the classifier to provide a very brief reason to explain its decision.
    SuspicionLevel: Enum mapped to various levels of channel concurrency.
    SUSPICION_RANKING_THRESHOLDS: Helper dict mapping tuples of the threshold ranges to their
        respective SuspicionLevel.
    SuspectedBots: SQLAlchemy table for tracking additional metadata and metrics for suspicious
        Twitch accounts.
    SuspectedBotAppData, Create, and Read: Pydantic BaseModels for validation and serializing.
    
"""
from enum import Enum
from typing import TYPE_CHECKING, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import conint, constr
from sqlmodel import Field, Relationship, SQLModel


class SuspicionReason(str, Enum):
    UNSPECIFIED = "unspecified"
    CONCURRENT_CHANNEL_COUNT = "concurrent_channel_count"


class SuspicionLevel(str, Enum):
    RED = "red"  #       100001+ channels (Highest alert)
    ORANGE = "orange"  #  50001 - 100k channels
    YELLOW = "yellow"  #  10001 - 50k channels
    GREEN = "green"  #     1001 - 10k channels
    BLUE = "blue"  #        101 - 1k channels
    PURPLE = "purple"  #     21 - 100 channels, technically within TOS for even unapproved bots.
    GREY = "grey"  #         11 - 20 channels (Lowest alert, Moonu Level)
    NONE = "none"  #         1 - 10 channels
    SAFE = "safe"  # special designation for bots that are known, e.g. SeryBot, Nightbot


SUSPICION_RANKING_THRESHOLDS: dict[Tuple[int, int], SuspicionLevel] = {
    (100001, 9999999): SuspicionLevel.RED,
    (50001, 100000): SuspicionLevel.ORANGE,
    (10001, 50000): SuspicionLevel.YELLOW,
    (1001, 10000): SuspicionLevel.GREEN,
    (101, 1000): SuspicionLevel.BLUE,
    (21, 100): SuspicionLevel.PURPLE,
    (11, 20): SuspicionLevel.GREY,
    (1, 10): SuspicionLevel.NONE,
}


"""Twitch Account IDs suspected of being a bot will be logged here. The definition of
"suspicion" and associated thresholds will no doubt be modulated by data and experiments. This
sister-table to TwitchUserData exists as suspects will have more data tracked about them. What's
stored will be gated by their SuspicionLevel (not everyone account gets on this table, and not
everyone on this table will get every field).

NOTE. Regarding "aliases" or namechanges.

Since the bot will routinely scan the platform and will track users by their account ID, which
does not change with a name change, it's possible to track bots that undergo name changes, if
this indeed a thing that happens. However, this also makes it possible for legitimate and
innocent users to be tracked through their own namechanges, effectively making this the ultimate
stalker tool.

I went back and forth on whether to track aliases (or even just a quantity of noticed name
changes) for perhaps "only SuspicionLevel.RED bots" or something, but:
- the possible risks that come with compromising regular user privacy are flatly unacceptable,
however small;
- I have no reason to believe botters would bother changing the name as it doesn't aid in
channel-level ban evasion, and if Twitch bans them it's at the account ID level anyway;
- why wouldn't they just spin up a new account and fire off the servers again?

So, if you were wondering "what happened to aliases?" now you know.

Args:
    suspected_bot_id (str): UUID generated by this app for this account, distinct from its
        Twitch Account ID.
    twitch_account_id (int): [FK] The unique UID for this account from Twitch.

    follower_count (int): The number of distinct Twitch accounts following this suspected bot,
        as reported by Twitch.
    following_count (int): The number of distinct Twitch accounts this suspected bot is
        following, as reported by Twitch.
    is_banned_or_deleted (bool): If the account is queried for later and comes back as absent,
        that means it was either deleted or has been banned; we can't distinguish between the
        two.

    suspicion_level (SuspicionLevel): The app's classification level for this account.
    suspicion_reason (SuspicionReason): The classifier's provided reason for marking this
        account as suspicious.
    additional_notes (str): A space for an admin of the app to put arbitrary text notes
        concerning this account.
"""


class SuspectedBotBase(SQLModel):
    # app data
    suspected_bot_id: UUID = Field(default_factory=uuid4, primary_key=True)
    has_ever_streamed: Optional[bool] = Field(default=None)
    suspicion_level: SuspicionLevel = Field(default=SuspicionLevel.NONE)
    suspicion_reason: SuspicionReason = Field(default=SuspicionReason.UNSPECIFIED)
    additional_notes: Optional[constr(pattern=r"^[a-zA-Z0-9/\s.,!?':;-]*$")] = None

    # api response data
    follower_count: Optional[conint(ge=0)] = Field(default=None)
    following_count: Optional[conint(ge=0)] = Field(default=None)

    # banned vs deleted is extrapolated
    is_banned_or_deleted: bool = Field(default=False)


# Table Model
class SuspectedBot(SuspectedBotBase, table=True):
    __tablename__: str = "suspected_bots"

    # twitch_account_id: conint(ge=0) = Field(
    #     foreign_key="twitch_user_data.twitch_account_id", nullable=False, unique=True, index=True
    # )

    # if TYPE_CHECKING:
    #     from . import TwitchUserData

    # twitch_user_data: Optional["TwitchUserData"] = Relationship(
    #     back_populates="suspected_bot"
    # )


# Create and Read Models
class SuspectedBotCreate(SuspectedBotBase):
    pass


class SuspectedBotRead(SuspectedBotBase):
    pass
