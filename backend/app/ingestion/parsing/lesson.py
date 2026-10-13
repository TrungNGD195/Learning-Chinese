import json
from uuid import UUID

from app.ingestion.parsing.base import ParsedUnit, ParsingFailure


_FIELDS = {
    "LESSON": ("title", "description"),
    "VOCABULARY": ("hanzi", "pinyin", "vietnamese_meaning", "part_of_speech", "note", "example"),
    "GRAMMAR": ("name", "structure", "explanation", "usage", "note", "example"),
}


def _uuid(value: object) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


class LessonSnapshotParser:
    name = "raw_lesson_snapshot"
    version = "v1"

    def parse(self, raw: bytes) -> list[ParsedUnit]:
        try:
            data = json.loads(raw.decode("utf-8"))
            lesson = data["lesson"]
            if (data.get("schema_version") != "raw_lesson_snapshot/v1" or not isinstance(lesson, dict)
                    or not _uuid(lesson.get("id")) or lesson.get("status") != "PUBLISHED"
                    or not isinstance(lesson.get("hsk"), dict) or not _uuid(lesson["hsk"].get("id"))
                    or not isinstance(lesson.get("lesson_number"), int)
                    or not isinstance(lesson.get("title"), str)
                    or not isinstance(data.get("vocabulary"), list) or not isinstance(data.get("grammar"), list)):
                raise ValueError
            units: list[ParsedUnit] = []
            for section, entity, entity_id_field, fields in (
                ("LESSON", lesson, "id", _FIELDS["LESSON"]),
            ):
                self._append_fields(units, section, entity, entity_id_field, fields)
            for section, key, id_field, order_required, fields in (
                ("VOCABULARY", "vocabulary", "vocabulary_id", True, _FIELDS["VOCABULARY"]),
                ("GRAMMAR", "grammar", "grammar_id", True, _FIELDS["GRAMMAR"]),
            ):
                last_order = -1
                for entity in data[key]:
                    link_id = "lesson_vocabulary_id" if section == "VOCABULARY" else "lesson_grammar_id"
                    if (not isinstance(entity, dict) or not _uuid(entity.get(id_field)) or not _uuid(entity.get(link_id))
                            or not isinstance(entity.get("order_index"), int)
                            or entity["order_index"] < 0 or entity["order_index"] <= last_order):
                        raise ValueError
                    last_order = entity["order_index"]
                    self._append_fields(units, section, entity, id_field, fields)
            return [ParsedUnit(i, unit.text, unit.source_locator) for i, unit in enumerate(units)]
        except ParsingFailure:
            raise
        except Exception as exc:
            raise ParsingFailure("INVALID_LESSON_SNAPSHOT", "Stored lesson snapshot is invalid or unsupported.") from exc

    @staticmethod
    def _append_fields(units: list[ParsedUnit], section: str, entity: dict, id_field: str, fields: tuple[str, ...]) -> None:
        entity_id = str(entity[id_field])
        for field in fields:
            value = entity.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                raise ValueError
            from app.ingestion.cleaning import clean_text
            cleaned = clean_text(value)
            if cleaned:
                locator = {"kind": "LESSON_FIELD", "section": section, "entity_id": entity_id, "field": field}
                if section != "LESSON":
                    locator["order_index"] = entity["order_index"]
                units.append(ParsedUnit(len(units), cleaned, locator))
