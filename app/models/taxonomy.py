from typing import Literal

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.item import ItemType

#: What a type is.
#:
#: "item" is browsable on its own, "reference" is attached to something else.
#: "record" is still part of the vocabulary the client understands, but no type
#: uses it now: the types that were records were fragments.
Kind = Literal["item", "record", "reference"]


class Taxonomy(Base):
    """One item type: where it belongs, what to call it, how it is shown.

    The taxonomy used to live only in ``app/taxonomy.py``. Putting it in the
    database means the list of types, and everything the site needs to know
    about a type, is in one place, and the column that holds a type is
    constrained to the same list.
    """

    __tablename__ = "taxonomy"

    type: Mapped[str] = mapped_column(ItemType, primary_key=True)
    area: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    group_name: Mapped[str | None] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[Kind] = mapped_column(String(20), nullable=False)
    listed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_fragment: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

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
