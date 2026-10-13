from collections.abc import Sequence
from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint, Uuid
from sqlalchemy.sql.schema import SchemaItem

from app.database.base import Base


def model(
    name: str,
    table_name: str,
    columns: Sequence[tuple[Any, ...]],
    *constraints: SchemaItem,
    indexes: Sequence[Index] = (),
) -> type:
    """Create a small declarative record mapping from explicit SQL columns."""
    attrs: dict[str, Any] = {"__tablename__": table_name, "__table_args__": (*constraints, *indexes)}
    for definition in columns:
        column_name, type_, *options = definition
        kwargs = dict(options[0]) if options else {}
        target = kwargs.pop("foreign_key", None)
        ondelete = kwargs.pop("ondelete", None)
        attribute_name = "metadata_json" if column_name == "metadata" else column_name
        if target:
            attrs[attribute_name] = Column(column_name, type_, ForeignKey(target, ondelete=ondelete), **kwargs)
        else:
            attrs[attribute_name] = Column(column_name, type_, **kwargs)
    return type(name, (Base,), attrs)


def fk(target: str, *, ondelete: str | None = None) -> ForeignKey:
    return ForeignKey(target, ondelete=ondelete)


def association(name: str, left_fk: str, right_fk: str) -> Table:
    left = left_fk.split(".")[0]
    right = right_fk.split(".")[0]
    return Table(
        name,
        Base.metadata,
        Column("assessment_id", Uuid(as_uuid=True), ForeignKey(left_fk), nullable=False),
        Column(right.removesuffix("s") + "_id", Uuid(as_uuid=True), ForeignKey(right_fk), nullable=False),
        UniqueConstraint("assessment_id", right.removesuffix("s") + "_id"),
    )
