# Course ORM model.
# TODO: SQLAlchemy model (3NF). id, user_id, name, term, etc. Relationships
#       to user, assignment, schedule.
#
# DISCLAIMER: Project structure may change. Fields/relationships may be added or
# modified. This describes the general idea.

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base