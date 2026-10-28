"""The snapshot has a contract, and the contract is checked.

The published site reads one file, ``frontend/public/snapshot.json``, and
nothing else. Its shape used to be described by hand-written TypeScript
interfaces that nothing validated, so a field the exporter stopped writing, or
a type the client did not expect, was found by a user rather than by CI.

Now the shape is written down in ``snapshot.schema.json``. The exporter writes
the file, the client reads it, and this test checks that the file matches the
contract, and that the contract is the one both sides agree on.
"""

import json
import re
from pathlib import Path

from jsonschema import Draft7Validator

from app.models.item import ITEM_TYPE_VALUES
from app.services.snapshot import SNAPSHOT_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SNAPSHOT = REPO_ROOT / "frontend" / "src" / "lib" / "snapshot.ts"
GENERATED_TYPES = REPO_ROOT / "frontend" / "src" / "lib" / "snapshot.types.ts"
SCHEMA_PATH = REPO_ROOT / "snapshot.schema.json"
SNAPSHOT_PATH = REPO_ROOT / "frontend" / "public" / "snapshot.json"

_CONSTANT = re.compile(r"export const SNAPSHOT_SCHEMA_VERSION\s*=\s*(\d+)")


def _frontend_schema_version() -> int:
    """Read the schema version the frontend expects."""
    source = FRONTEND_SNAPSHOT.read_text(encoding="utf-8")
    match = _CONSTANT.search(source)
    assert match is not None, f"no SNAPSHOT_SCHEMA_VERSION in {FRONTEND_SNAPSHOT}"
    return int(match.group(1))


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _validator() -> Draft7Validator:
    return Draft7Validator(_schema())


class TestTheContract:
    def test_the_schema_is_itself_valid(self):
        """A schema that does not validate proves nothing."""
        Draft7Validator.check_schema(_schema())

    def test_the_frontend_and_the_backend_agree_on_the_snapshot_shape(self):
        """Both sides must declare the same snapshot version."""
        assert _frontend_schema_version() == SNAPSHOT_SCHEMA_VERSION

    def test_the_frontend_file_is_where_the_test_looks(self):
        """Guard against the test silently reading a file that moved.

        A rename would leave the test reading nothing and comparing a constant
        against itself, so the file has to be there.
        """
        assert FRONTEND_SNAPSHOT.is_file()
        assert "SNAPSHOT_SCHEMA_VERSION" in FRONTEND_SNAPSHOT.read_text(encoding="utf-8")

    def test_the_schema_and_the_database_agree_on_the_types(self):
        """The file and the database must accept the same types.

        The schema is the file's contract and the enum is the database's. If
        they drift, the exporter can write a type the client refuses, or the
        database can hold a type the schema does not describe.
        """
        schema_types = _schema()["definitions"]["itemType"]["enum"]
        assert list(schema_types) == list(ITEM_TYPE_VALUES)


class TestThePublishedFile:
    def test_the_published_snapshot_matches_the_contract(self):
        """The file the site reads must match the contract."""
        validator = _validator()
        errors = sorted(validator.iter_errors(_snapshot()), key=lambda e: list(e.path))
        assert not errors, "\n".join(
            f"{'.'.join(str(part) for part in error.path)}: {error.message}"
            for error in errors[:10]
        )

    def test_the_schema_version_matches_the_file(self):
        assert _snapshot()["schema_version"] == SNAPSHOT_SCHEMA_VERSION

    def test_the_counts_agree_with_the_rows(self):
        """The published count has to match what was published."""
        snapshot = _snapshot()
        assert snapshot["counts"]["items"] == len(snapshot["items"])
        assert snapshot["counts"]["formulas"] == len(snapshot["formulas"])
        assert snapshot["counts"]["wiki_pages"] == len(snapshot["wiki_pages"])


class TestTheContractCatchesThings:
    """The checks have to reject something, or they are decoration."""

    def test_an_unknown_item_type_is_rejected(self):
        snapshot = _snapshot()
        snapshot["items"][0]["type"] = "not_a_real_type"
        assert list(_validator().iter_errors(snapshot))

    def test_a_missing_field_is_rejected(self):
        snapshot = _snapshot()
        del snapshot["items"][0]["slug"]
        assert list(_validator().iter_errors(snapshot))

    def test_an_unexpected_field_is_rejected(self):
        """A field nobody declared is a change nobody agreed to."""
        snapshot = _snapshot()
        snapshot["items"][0]["surprise"] = 1
        assert list(_validator().iter_errors(snapshot))

    def test_a_bad_confidence_is_rejected(self):
        snapshot = _snapshot()
        snapshot["formulas"][0]["confidence"] = "pretty sure"
        assert list(_validator().iter_errors(snapshot))

    def test_data_that_is_not_an_object_is_rejected(self):
        snapshot = _snapshot()
        snapshot["items"][0]["data"] = [1, 2, 3]
        assert list(_validator().iter_errors(snapshot))

    def test_an_empty_name_is_rejected(self):
        snapshot = _snapshot()
        snapshot["items"][0]["name"] = ""
        assert list(_validator().iter_errors(snapshot))

    def test_a_missing_top_level_key_is_rejected(self):
        snapshot = _snapshot()
        del snapshot["counts"]
        assert list(_validator().iter_errors(snapshot))

    def test_an_item_with_an_unknown_type_in_the_taxonomy_is_rejected(self):
        snapshot = _snapshot()
        snapshot["taxonomy"][0]["type"] = "not_a_real_type"
        assert list(_validator().iter_errors(snapshot))


class TestTheGeneratedTypes:
    """The client's types come from the contract, so they cannot drift."""

    def test_the_generated_types_are_committed(self):
        assert GENERATED_TYPES.is_file(), (
            f"{GENERATED_TYPES} is missing. Run `npm run generate:snapshot-types`."
        )

    def test_the_generated_types_describe_every_type(self):
        """The type list in the generated file has to match the schema."""
        source = GENERATED_TYPES.read_text(encoding="utf-8")
        for item_type in ITEM_TYPE_VALUES:
            assert f'"{item_type}"' in source, f"{item_type} is missing from the types"

    def test_the_generated_types_name_the_contract(self):
        """The file says where it came from, so nobody edits it by hand."""
        source = GENERATED_TYPES.read_text(encoding="utf-8")
        assert "json-schema-to-typescript" in source
        assert "DO NOT MODIFY IT BY HAND" in source
