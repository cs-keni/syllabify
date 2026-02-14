# SQLAlchemy base.
# TODO: DeclarativeBase, metadata. Import in models (user, course, assignment,
#       schedule). Used by init_db for create_all.
#
# DISCLAIMER: Project structure may change. This describes the general idea.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
