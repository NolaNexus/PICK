from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String

from app.database import Base
from app.models.item import ItemType


class Taxonomy(Base):
    """One item type: where it belongs, what to call it, how it is shown.

    The taxonomy used to live only in ``app/taxonomy.py``. Putting it in the
    database means the list of types, and everything the site needs to know
    about a type, is in one place, and the column that holds a type is
    constrained to the same list.
    """

    __tablename__ = "taxonomy"

    type = Column(ItemType, primary_key=True)
    area = Column(String(50), nullable=False, index=True)
    group_name = Column(String(50))
    label = Column(String(100), nullable=False)
    kind = Column(String(20), nullable=False)
    listed = Column(Boolean, nullable=False, server_default="true")
    is_fragment = Column(Boolean, nullable=False, server_default="false")
    display_order = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        CheckConstraint(
            "kind IN ('item', 'record', 'reference')",
            name="ck_taxonomy_kind",
        ),
        CheckConstraint(
            "listed = (kind = 'item')",
            name="ck_taxonomy_listed",
        ),
    )

    def __repr__(self) -> str:
        return f"<Taxonomy(type={self.type}, area={self.area!r})>"
