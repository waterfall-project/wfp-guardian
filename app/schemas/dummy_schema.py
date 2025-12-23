# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for data serialization and validation.

This module defines Marshmallow schemas for serializing and validating
the application's data models, providing automatic schema generation
from SQLAlchemy models with custom validation rules.
"""

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.models.constants import DUMMY_DESCRIPTION_MAX_LENGTH, DUMMY_NAME_MAX_LENGTH
from app.models.dummy_model import Dummy
from app.schemas.constants import (
    DUMMY_DESCRIPTION_TOO_LONG,
    DUMMY_NAME_EMPTY,
    DUMMY_NAME_NOT_UNIQUE,
    DUMMY_NAME_TOO_LONG,
)


class DummySchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for serializing and validating Dummy model instances.

    This schema provides automatic serialization/deserialization of Dummy
    entities with custom validation for name uniqueness and description length.
    Uses SQLAlchemyAutoSchema for automatic field generation from the model.

    Attributes:
        id: Unique UUID identifier for the Dummy entity (dump only).
        name: Name of the Dummy entity (max 50 characters, required, unique).
        description: Optional description (max 200 characters).
        extra_metadata: Optional JSON metadata for flexible data storage.
        created_at: Timestamp of creation (dump only).
        updated_at: Timestamp of last update (dump only).
    """

    name = fields.Str(
        required=True,
        validate=validate.Length(max=DUMMY_NAME_MAX_LENGTH, error=DUMMY_NAME_TOO_LONG),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=DUMMY_DESCRIPTION_MAX_LENGTH, error=DUMMY_DESCRIPTION_TOO_LONG
        ),
    )
    extra_metadata = fields.Dict(allow_none=True, dump_default=None)

    class Meta:
        """Marshmallow schema configuration options.

        Defines the SQLAlchemy model binding and serialization behavior
        for the DummySchema.

        Attributes:
            model: The Dummy SQLAlchemy model class.
            load_instance: If True, deserialize to model instances.
            include_fk: If True, include foreign key fields.
            dump_only: Tuple of field names that are read-only (id, timestamps).
            unknown: How to handle unknown fields (EXCLUDE to ignore them).
        """

        model = Dummy
        load_instance = False
        include_fk = True
        dump_only = ("id", "created_at", "updated_at")
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Strip whitespace from string fields before validation.

        Args:
            data: The input data dictionary.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The modified data dictionary with stripped strings.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        return data

    @validates("name")
    def validate_name(self, value, **kwargs):
        """Validate that the name field is not empty and is unique.

        Checks that the name is provided and does not already exist in the
        database to enforce uniqueness constraint.

        Args:
            value: The name value to validate.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The validated name value.

        Raises:
            ValidationError: If the name is empty or already exists.

        Example:
            >>> schema = DummySchema()
            >>> schema.validate_name("unique_name")
            'unique_name'
        """
        session = kwargs.get("session")

        # Check for empty after strip
        if not value:
            raise ValidationError(DUMMY_NAME_EMPTY)

        # Check uniqueness using session if provided, otherwise use model method
        if session:
            existing = session.query(Dummy).filter(Dummy.name == value).first()
            if existing:
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        else:
            dummy = Dummy.get_by_name(value)
            if dummy:
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        return value


class DummyCreateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for creating new Dummy instances.

    This schema is used for POST requests to create new Dummy entities.
    Excludes read-only fields (id, timestamps) that are auto-generated.

    Attributes:
        name: Name of the Dummy entity (max 50 characters, required, unique).
        description: Optional description (max 200 characters).
        extra_metadata: Optional JSON metadata for flexible data storage.
    """

    name = fields.Str(
        required=True,
        validate=validate.Length(max=DUMMY_NAME_MAX_LENGTH, error=DUMMY_NAME_TOO_LONG),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=DUMMY_DESCRIPTION_MAX_LENGTH, error=DUMMY_DESCRIPTION_TOO_LONG
        ),
    )
    extra_metadata = fields.Dict(allow_none=True, dump_default=None)

    class Meta:
        """Marshmallow schema configuration for creation.

        Attributes:
            model: The Dummy SQLAlchemy model class.
            load_instance: If True, deserialize to model instances.
            include_fk: If True, include foreign key fields.
            exclude: Fields excluded from input (auto-generated fields).
            unknown: How to handle unknown fields (EXCLUDE to ignore them).
        """

        model = Dummy
        load_instance = False
        include_fk = True
        exclude = ("id", "created_at", "updated_at")
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Strip whitespace from string fields before validation.

        Args:
            data: The input data dictionary.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The modified data dictionary with stripped strings.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        return data

    @validates("name")
    def validate_name(self, value, **kwargs):
        """Validate that the name field is not empty and is unique.

        Args:
            value: The name value to validate.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The validated name value.

        Raises:
            ValidationError: If the name is empty or already exists.
        """
        session = kwargs.get("session")

        # Check for empty after strip
        if not value:
            raise ValidationError(DUMMY_NAME_EMPTY)

        # Check uniqueness using session if provided
        if session:
            existing = session.query(Dummy).filter(Dummy.name == value).first()
            if existing:
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        else:
            dummy = Dummy.get_by_name(value)
            if dummy:
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        return value


class DummyReplaceSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for full replacement of Dummy instances (PUT).

    This schema is used for PUT requests where all fields must be provided
    for full entity replacement. Excludes read-only fields (id, timestamps).

    Supports context passing to allow validation to check uniqueness while
    excluding the current entity being updated.

    Attributes:
        name: Required name (max 50 characters, must be unique).
        description: Optional description (max 200 characters).
        extra_metadata: Optional JSON metadata.
    """

    def __init__(self, *args, **kwargs):
        """Initialize schema with context support for update operations.

        Args:
            *args: Positional arguments passed to parent class.
            **kwargs: Keyword arguments. 'context' is extracted and stored.
        """
        self.context = kwargs.pop("context", {})
        super().__init__(*args, **kwargs)

    name = fields.Str(
        required=True,
        validate=validate.Length(max=DUMMY_NAME_MAX_LENGTH, error=DUMMY_NAME_TOO_LONG),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=DUMMY_DESCRIPTION_MAX_LENGTH, error=DUMMY_DESCRIPTION_TOO_LONG
        ),
    )
    extra_metadata = fields.Dict(allow_none=True, dump_default=None)

    class Meta:
        """Marshmallow schema configuration for full replacement.

        Attributes:
            model: The Dummy SQLAlchemy model class.
            load_instance: If True, deserialize to model instances.
            include_fk: If True, include foreign key fields.
            exclude: Fields excluded from input (auto-generated/immutable).
            partial: If False, all required fields must be provided.
            unknown: How to handle unknown fields (EXCLUDE to ignore them).
        """

        model = Dummy
        load_instance = False
        include_fk = True
        exclude = ("id", "created_at", "updated_at")
        partial = False
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Strip whitespace from string fields before validation.

        Args:
            data: The input data dictionary.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            Modified data dictionary with strings stripped.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        return data

    @validates("name")
    def validate_name(self, value, **kwargs):
        """Validate that the name is unique, except for the current dummy being replaced.

        Uses context to get the current dummy instance and exclude it from
        uniqueness check, allowing a dummy to keep its own name during replacement.

        Args:
            value: The name value to validate.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The validated name value.

        Raises:
            ValidationError: If the name is empty or already exists for another entity.
        """
        session = kwargs.get("session")

        # Check for empty after strip
        if not value:
            raise ValidationError(DUMMY_NAME_EMPTY)

        # Get current dummy from context to exclude it from uniqueness check
        current_dummy = self.context.get("dummy") if hasattr(self, "context") else None

        # Check uniqueness using session if provided
        if session:
            existing = session.query(Dummy).filter(Dummy.name == value).first()
            # Allow same name if it's the dummy being updated
            if existing and (not current_dummy or existing.id != current_dummy.id):
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        else:
            dummy = Dummy.get_by_name(value)
            # Allow same name if it's the dummy being updated
            if dummy and (not current_dummy or dummy.id != current_dummy.id):
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        return value


class DummyUpdateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for partial updates of Dummy instances (PATCH).

    This schema is used for PATCH requests to partially update Dummy entities.
    All fields are optional (partial updates supported). Excludes read-only
    fields (id, timestamps).

    Supports context passing to allow validation to check uniqueness while
    excluding the current entity being updated.

    Attributes:
        name: Optional new name (max 50 characters, must be unique if provided).
        description: Optional new description (max 200 characters).
        extra_metadata: Optional new JSON metadata.
    """

    def __init__(self, *args, **kwargs):
        """Initialize schema with context support for update operations.

        Args:
            *args: Positional arguments passed to parent class.
            **kwargs: Keyword arguments. 'context' is extracted and stored.
        """
        self.context = kwargs.pop("context", {})
        super().__init__(*args, **kwargs)

    name = fields.Str(
        required=False,
        validate=validate.Length(max=DUMMY_NAME_MAX_LENGTH, error=DUMMY_NAME_TOO_LONG),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=DUMMY_DESCRIPTION_MAX_LENGTH, error=DUMMY_DESCRIPTION_TOO_LONG
        ),
    )
    extra_metadata = fields.Dict(allow_none=True, dump_default=None)

    class Meta:
        """Marshmallow schema configuration for updates.

        Attributes:
            model: The Dummy SQLAlchemy model class.
            load_instance: If True, deserialize to model instances.
            include_fk: If True, include foreign key fields.
            exclude: Fields excluded from input (auto-generated/immutable).
            partial: If True, all fields are optional (for partial updates).
            unknown: How to handle unknown fields (EXCLUDE to ignore them).
        """

        model = Dummy
        load_instance = False
        include_fk = True
        exclude = ("id", "created_at", "updated_at")
        partial = True
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Strip whitespace from string fields before validation.

        Args:
            data: The input data dictionary.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The modified data dictionary with stripped strings.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        return data

    @validates("name")
    def validate_name(self, value, **kwargs):
        """Validate that the name is unique, except for the current dummy being updated.

        Uses context to get the current dummy instance and exclude it from
        uniqueness check, allowing a dummy to keep its own name during update.

        Args:
            value: The name value to validate.
            **kwargs: Additional keyword arguments from Marshmallow.

        Returns:
            The validated name value.

        Raises:
            ValidationError: If the name is empty or already exists for another entity.
        """
        session = kwargs.get("session")

        # Check for empty after strip
        if not value:
            raise ValidationError(DUMMY_NAME_EMPTY)

        # Get current dummy from context to exclude it from uniqueness check
        current_dummy = self.context.get("dummy") if hasattr(self, "context") else None

        # Check uniqueness using session if provided
        if session:
            existing = session.query(Dummy).filter(Dummy.name == value).first()
            # Allow same name if it's the dummy being updated
            if existing and (not current_dummy or existing.id != current_dummy.id):
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        else:
            dummy = Dummy.get_by_name(value)
            # Allow same name if it's the dummy being updated
            if dummy and (not current_dummy or dummy.id != current_dummy.id):
                raise ValidationError(DUMMY_NAME_NOT_UNIQUE)
        return value
