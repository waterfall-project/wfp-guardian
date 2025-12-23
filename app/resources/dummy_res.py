# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Dummy REST API resources.

This module defines the Flask-RESTful resources for managing Dummy entities.
It provides CRUD operations through REST endpoints with proper validation,
authentication, and error handling.
"""

from flask import current_app, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.db import db
from app.models.dummy_model import Dummy
from app.resources.constants import (
    ERROR_DATABASE,
    ERROR_DATABASE_LOG,
    ERROR_INTEGRITY,
    ERROR_INTEGRITY_LOG,
    ERROR_VALIDATION,
    ERROR_VALIDATION_LOG,
    LOG_CREATING_DUMMY,
    LOG_DELETING_DUMMY,
    LOG_DUMMY_CREATED,
    LOG_DUMMY_DELETED,
    LOG_DUMMY_NOT_FOUND,
    LOG_DUMMY_PARTIAL_UPDATED,
    LOG_DUMMY_UPDATED,
    LOG_PARTIAL_UPDATING_DUMMY,
    LOG_RETRIEVING_ALL_DUMMIES,
    LOG_RETRIEVING_DUMMY,
    LOG_UPDATING_DUMMY,
    MSG_DUMMY_DELETED,
    MSG_DUMMY_NOT_FOUND,
    MSG_NO_INPUT_DATA,
)
from app.schemas.dummy_schema import (
    DummyCreateSchema,
    DummyReplaceSchema,
    DummySchema,
    DummyUpdateSchema,
)
from app.utils.guardian import Operation, access_required
from app.utils.jwt_utils import require_jwt_auth
from app.utils.limiter import limiter
from app.utils.logger import logger


class DummyListResource(Resource):
    """Resource for managing the collection of Dummy entities.

    Provides endpoints for:
    - Listing all Dummy entities (GET)
    - Creating a new Dummy entity (POST)

    All endpoints require JWT authentication and appropriate permissions.
    """

    @require_jwt_auth
    @access_required(Operation.LIST)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """Retrieve Dummy entities with optional pagination.

        Query Parameters:
            limit (int, optional): Maximum number of records to return.
                Default from config (PAGE_LIMIT), Max from config (MAX_PAGE_LIMIT)
            offset (int, optional): Number of records to skip. Default: 0

        Returns:
            tuple: JSON response with list of Dummy entities and HTTP 200.

        Example response:
            [
                {
                    "id": "uuid",
                    "name": "Example",
                    "description": "...",
                    "extra_metadata": {...},
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                }
            ]
        """
        logger.info(LOG_RETRIEVING_ALL_DUMMIES)

        # Parse pagination parameters from query string
        try:
            limit = request.args.get(
                "limit", default=current_app.config["PAGE_LIMIT"], type=int
            )
            offset = request.args.get("offset", default=0, type=int)
        except (TypeError, ValueError) as e:
            logger.error("Invalid pagination parameters: %s", str(e))
            return {"message": "Invalid pagination parameters", "error": str(e)}, 400

        # Validate limit and offset
        if limit < 1:
            return {"message": "Limit must be greater than 0"}, 400
        if limit > current_app.config["MAX_PAGE_LIMIT"]:
            limit = current_app.config["MAX_PAGE_LIMIT"]
        if offset < 0:
            return {"message": "Offset must be greater than or equal to 0"}, 400

        dummies = Dummy.get_all(limit=limit, offset=offset)
        schema = DummySchema(many=True)
        return schema.dump(dummies), 200

    @require_jwt_auth
    @access_required(Operation.CREATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def post(self):
        """Create a new Dummy entity.

        Expected JSON payload:
            {
                "name": "string" (required, max 50 chars),
                "description": "string" (optional, max 200 chars),
                "extra_metadata": {...} (optional)
            }

        Returns:
            tuple: JSON response with created Dummy and HTTP 201 on success.
            tuple: Error response with HTTP 400/500 on failure.

        Note: Avec load_instance=False, schema.load() retourne un dict.
              On doit créer l'instance manuellement avec Dummy(**data).
        """
        logger.info(LOG_CREATING_DUMMY)

        json_data = request.get_json()
        if not json_data:
            return {"message": MSG_NO_INPUT_DATA}, 400

        # Validation: schema.load() retourne un dict car load_instance=False
        schema = DummyCreateSchema()
        try:
            validated_data = schema.load(json_data, session=db.session())
        except ValidationError as err:
            logger.error(ERROR_VALIDATION_LOG, err.messages)
            return {"message": ERROR_VALIDATION, "errors": err.messages}, 422

        # Création manuelle de l'instance à partir du dict validé
        try:
            dummy = Dummy(**validated_data)
            db.session.add(dummy)
            db.session.commit()
            logger.info(LOG_DUMMY_CREATED, dummy.id)
        except IntegrityError as e:
            db.session.rollback()
            logger.error(ERROR_INTEGRITY_LOG, str(e))
            return {"message": ERROR_INTEGRITY, "error": str(e)}, 409
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(ERROR_DATABASE_LOG, str(e))
            return {"message": ERROR_DATABASE, "error": str(e)}, 500

        # Serialization pour la réponse
        response_schema = DummySchema()
        return response_schema.dump(dummy), 201


class DummyResource(Resource):
    """Resource for managing individual Dummy entities by ID.

    Provides endpoints for:
    - Retrieving a single Dummy (GET)
    - Updating a Dummy (PUT - full replacement)
    - Partially updating a Dummy (PATCH)
    - Deleting a Dummy (DELETE)

    All endpoints require JWT authentication and appropriate permissions.
    """

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self, dummy_id):
        """Retrieve a single Dummy entity by ID.

        Args:
            dummy_id: UUID of the Dummy to retrieve.

        Returns:
            tuple: JSON response with Dummy data and HTTP 200 on success.
            tuple: Error response with HTTP 404 if not found.
        """
        logger.info(LOG_RETRIEVING_DUMMY, dummy_id)

        dummy = Dummy.get_by_id(dummy_id)
        if not dummy:
            logger.warning(LOG_DUMMY_NOT_FOUND, dummy_id)
            return {"message": MSG_DUMMY_NOT_FOUND}, 404

        schema = DummySchema()
        return schema.dump(dummy), 200

    @require_jwt_auth
    @access_required(Operation.UPDATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def put(self, dummy_id):
        """Update a Dummy entity (full replacement).

        Args:
            dummy_id: UUID of the Dummy to update.

        Expected JSON payload:
            {
                "name": "string" (required),
                "description": "string" (optional),
                "extra_metadata": {...} (optional)
            }

        Returns:
            tuple: JSON response with updated Dummy and HTTP 200 on success.
            tuple: Error response with HTTP 400/404/500 on failure.
        """
        logger.info(LOG_UPDATING_DUMMY, dummy_id)

        dummy = Dummy.get_by_id(dummy_id)
        if not dummy:
            logger.warning(LOG_DUMMY_NOT_FOUND, dummy_id)
            return {"message": MSG_DUMMY_NOT_FOUND}, 404

        json_data = request.get_json()
        if not json_data:
            return {"message": MSG_NO_INPUT_DATA}, 400

        # Validation avec DummyReplaceSchema (tous les champs requis pour PUT)
        # avec contexte pour vérifier l'unicité tout en permettant de garder le même nom
        schema = DummyReplaceSchema(context={"dummy": dummy})
        try:
            validated_data = schema.load(json_data, session=db.session())
        except ValidationError as err:
            logger.error(ERROR_VALIDATION_LOG, err.messages)
            return {"message": ERROR_VALIDATION, "errors": err.messages}, 422

        # Mise à jour de l'instance existante
        try:
            for key, value in validated_data.items():
                setattr(dummy, key, value)
            db.session.commit()
            logger.info(LOG_DUMMY_UPDATED, dummy_id)
        except IntegrityError as e:
            db.session.rollback()
            logger.error(ERROR_INTEGRITY_LOG, str(e))
            return {"message": ERROR_INTEGRITY, "error": str(e)}, 409
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(ERROR_DATABASE_LOG, str(e))
            return {"message": ERROR_DATABASE, "error": str(e)}, 500

        response_schema = DummySchema()
        return response_schema.dump(dummy), 200

    @require_jwt_auth
    @access_required(Operation.UPDATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def patch(self, dummy_id):
        """Partially update a Dummy entity.

        Args:
            dummy_id: UUID of the Dummy to update.

        Expected JSON payload (all fields optional):
            {
                "name": "string",
                "description": "string",
                "extra_metadata": {...}
            }

        Returns:
            tuple: JSON response with updated Dummy and HTTP 200 on success.
            tuple: Error response with HTTP 400/404/500 on failure.

        Note: Avec DummyUpdateSchema (partial=True), schema.load() accepte
              des données partielles et retourne un dict avec seulement
              les champs fournis.
        """
        logger.info(LOG_PARTIAL_UPDATING_DUMMY, dummy_id)

        dummy = Dummy.get_by_id(dummy_id)
        if not dummy:
            logger.warning(LOG_DUMMY_NOT_FOUND, dummy_id)
            return {"message": MSG_DUMMY_NOT_FOUND}, 404

        json_data = request.get_json()
        if not json_data:
            return {"message": MSG_NO_INPUT_DATA}, 400

        # Validation avec DummyUpdateSchema (partial=True) avec contexte
        schema = DummyUpdateSchema(context={"dummy": dummy})
        try:
            validated_data = schema.load(json_data, session=db.session())
        except ValidationError as err:
            logger.error(ERROR_VALIDATION_LOG, err.messages)
            return {"message": ERROR_VALIDATION, "errors": err.messages}, 422

        # Mise à jour uniquement des champs fournis
        try:
            for key, value in validated_data.items():
                setattr(dummy, key, value)
            db.session.commit()
            logger.info(LOG_DUMMY_PARTIAL_UPDATED, dummy_id)
        except IntegrityError as e:
            db.session.rollback()
            logger.error(ERROR_INTEGRITY_LOG, str(e))
            return {"message": ERROR_INTEGRITY, "error": str(e)}, 409
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(ERROR_DATABASE_LOG, str(e))
            return {"message": ERROR_DATABASE, "error": str(e)}, 500

        response_schema = DummySchema()
        return response_schema.dump(dummy), 200

    @require_jwt_auth
    @access_required(Operation.DELETE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def delete(self, dummy_id):
        """Delete a Dummy entity.

        Args:
            dummy_id: UUID of the Dummy to delete.

        Returns:
            tuple: Success message and HTTP 204 on success.
            tuple: Error response with HTTP 404/500 on failure.
        """
        logger.info(LOG_DELETING_DUMMY, dummy_id)

        dummy = Dummy.get_by_id(dummy_id)
        if not dummy:
            logger.warning(LOG_DUMMY_NOT_FOUND, dummy_id)
            return {"message": MSG_DUMMY_NOT_FOUND}, 404

        try:
            db.session.delete(dummy)
            db.session.commit()
            logger.info(LOG_DUMMY_DELETED, dummy_id)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(ERROR_DATABASE_LOG, str(e))
            return {"message": ERROR_DATABASE, "error": str(e)}, 500

        return {"message": MSG_DUMMY_DELETED}, 204
