# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Audit service for access log management.

This service handles creating, querying, and managing access logs for
compliance and security auditing. Implements dual-write pattern:
1. PostgreSQL for hot data (7 days, fast queries)
2. Structured logs for Loki/ELK (long-term retention)
"""

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from flask import g, request
from sqlalchemy import and_, func
from sqlalchemy.sql import cast
from sqlalchemy.types import Integer

from app.models.audit_log import AccessLog
from app.models.db import db
from app.utils.logger import logger

# Structured logger for shipping to Loki
audit_logger = structlog.get_logger("audit")


class AuditService:
    """Service for managing access logs and audit trail."""

    def log_access(
        self,
        user_id: UUID,
        company_id: UUID,
        service: str,
        resource_name: str,
        operation: str,
        access_granted: bool,
        project_id: UUID | None = None,
        resource_id: str | None = None,
        reason: str | None = None,
        context: dict | None = None,
    ) -> AccessLog:
        """Create an access log entry with dual-write pattern.

        Writes to:
        1. PostgreSQL (for 7-day hot queries)
        2. Structured logs (for Loki/ELK long-term)

        Args:
            user_id: User who made the request
            company_id: User's company
            service: Requesting service
            resource_name: Resource type
            operation: Requested operation
            access_granted: Whether access was granted
            project_id: Project context (optional)
            resource_id: Specific resource ID (optional)
            reason: Access decision reason (optional)
            context: Additional metadata (optional)

        Returns:
            Created AccessLog instance
        """
        # Extract request context
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get("User-Agent") if request else None
        request_id = g.get("request_id") if hasattr(g, "request_id") else None

        # Prepare log data
        log_data = {
            "user_id": user_id,
            "company_id": company_id,
            "service": service,
            "resource_name": resource_name,
            "operation": operation,
            "access_granted": access_granted,
            "project_id": project_id,
            "resource_id": resource_id,
            "reason": reason,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "context": context or {},
        }

        # 1. Write to PostgreSQL (hot data, 7 days)
        access_log = AccessLog(**log_data)
        try:
            db.session.add(access_log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to write access log to database: {e}")
            raise  # Re-raise exception - DB write is critical

        # 2. Write to structured logs (Loki/ELK)
        try:
            audit_logger.info(
                "access_log",
                log_id=str(access_log.id),
                timestamp=datetime.utcnow().isoformat(),
                user_id=str(user_id),
                company_id=str(company_id),
                service=service,
                resource_name=resource_name,
                operation=operation,
                access_granted=access_granted,
                project_id=str(project_id) if project_id else None,
                resource_id=resource_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                context=context or {},
            )
        except Exception as e:
            logger.warning(f"Failed to write structured audit log: {e}")

        return access_log

    def get_logs(
        self,
        user_id: UUID | None = None,
        company_id: UUID | None = None,
        project_id: UUID | None = None,
        service: str | None = None,
        resource_name: str | None = None,
        operation: str | None = None,
        is_granted: bool | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AccessLog], int]:
        """Query access logs with filters and pagination.

        Args:
            user_id: Filter by user
            company_id: Filter by company
            project_id: Filter by project
            service: Filter by service
            resource_name: Filter by resource type
            operation: Filter by operation
            is_granted: Filter by result (True=granted, False=denied, None=all)
            from_date: Start date
            to_date: End date
            page: Page number (1-indexed)
            page_size: Items per page (max 100)

        Returns:
            Tuple of (logs, total_count)
        """
        # Build query with filters
        query = AccessLog.query

        if user_id:
            query = query.filter(AccessLog.user_id == user_id)
        if company_id:
            query = query.filter(AccessLog.company_id == company_id)
        if project_id:
            query = query.filter(AccessLog.project_id == project_id)
        if service:
            query = query.filter(AccessLog.service == service)
        if resource_name:
            query = query.filter(AccessLog.resource_name == resource_name)
        if operation:
            query = query.filter(AccessLog.operation == operation)
        if is_granted is not None:
            query = query.filter(AccessLog.access_granted == is_granted)
        if from_date:
            query = query.filter(AccessLog.created_at >= from_date)
        if to_date:
            query = query.filter(AccessLog.created_at <= to_date)

        # Get total count
        total_count = query.count()

        # Apply pagination
        page_size = min(page_size, 100)  # Max 100 per page
        offset = (page - 1) * page_size
        logs = (
            query.order_by(AccessLog.created_at.desc())
            .limit(page_size)
            .offset(offset)
            .all()
        )

        return logs, total_count

    def get_log_by_id(self, log_id: UUID) -> AccessLog | None:
        """Get a specific access log by ID.

        Args:
            log_id: Log UUID

        Returns:
            AccessLog instance or None if not found
        """
        result: AccessLog | None = AccessLog.query.filter_by(id=log_id).first()
        return result

    def get_statistics(
        self,
        company_id: UUID | None = None,
        project_id: UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> dict:
        """Get aggregated audit statistics.

        Args:
            company_id: Filter by company
            project_id: Filter by project
            from_date: Start date
            to_date: End date

        Returns:
            Dictionary with aggregated statistics
        """
        # Build base query
        query = AccessLog.query

        if company_id:
            query = query.filter(AccessLog.company_id == company_id)
        if project_id:
            query = query.filter(AccessLog.project_id == project_id)
        if from_date:
            query = query.filter(AccessLog.created_at >= from_date)
        if to_date:
            query = query.filter(AccessLog.created_at <= to_date)

        # Total requests
        total_requests = query.count()
        granted_requests = query.filter(AccessLog.access_granted.is_(True)).count()
        denied_requests = total_requests - granted_requests
        success_rate = (
            (granted_requests / total_requests * 100) if total_requests > 0 else 0
        )

        # By service
        # Build filters for aggregations
        filters = []
        if company_id:
            filters.append(AccessLog.company_id == company_id)
        if from_date:
            filters.append(AccessLog.created_at >= from_date)
        if to_date:
            filters.append(AccessLog.created_at <= to_date)

        query_service = db.session.query(
            AccessLog.service,
            func.count(AccessLog.id).label("count"),
            func.sum(cast(AccessLog.access_granted, Integer)).label("granted"),
        )
        if filters:
            query_service = query_service.filter(and_(*filters))
        by_service = query_service.group_by(AccessLog.service).all()

        by_service_list = [
            {
                "service": service,
                "count": count,
                "granted": granted or 0,
                "denied": count - (granted or 0),
            }
            for service, count, granted in by_service
        ]

        # By operation
        query_operation = db.session.query(
            AccessLog.operation,
            func.count(AccessLog.id).label("count"),
            func.sum(cast(AccessLog.access_granted, Integer)).label("granted"),
        )
        if filters:
            query_operation = query_operation.filter(and_(*filters))
        by_operation = query_operation.group_by(AccessLog.operation).all()

        by_operation_list = [
            {
                "operation": operation,
                "count": count,
                "granted": granted or 0,
                "denied": count - (granted or 0),
            }
            for operation, count, granted in by_operation
        ]

        # Top 10 users
        query_top_users = db.session.query(
            AccessLog.user_id,
            func.count(AccessLog.id).label("count"),
        )
        if filters:
            query_top_users = query_top_users.filter(and_(*filters))
        top_users = (
            query_top_users.group_by(AccessLog.user_id)
            .order_by(func.count(AccessLog.id).desc())
            .limit(10)
            .all()
        )

        top_users_list = [
            {"user_id": str(user_id), "count": count} for user_id, count in top_users
        ]

        return {
            "total_requests": total_requests,
            "granted_requests": granted_requests,
            "denied_requests": denied_requests,
            "success_rate": round(success_rate, 2),
            "by_service": by_service_list,
            "by_operation": by_operation_list,
            "top_users": top_users_list,
        }

    def purge_old_logs(
        self, before_date: datetime, company_id: UUID | None = None
    ) -> int:
        """Purge access logs older than specified date (GDPR compliance).

        Args:
            before_date: Delete logs older than this date
            company_id: Limit purge to specific company (optional)

        Returns:
            Number of deleted logs

        Raises:
            ValueError: If before_date is less than 30 days ago
        """
        # Enforce minimum retention of 30 days
        min_date = datetime.utcnow() - timedelta(days=30)
        if before_date > min_date:
            raise ValueError("Cannot delete logs less than 30 days old")

        # Build delete query
        query = AccessLog.query.filter(AccessLog.created_at < before_date)

        if company_id:
            query = query.filter(AccessLog.company_id == company_id)

        # Count before deletion
        count: int = query.count()

        # Delete
        query.delete(synchronize_session=False)
        db.session.commit()

        logger.info(
            f"Purged {count} access logs before {before_date.isoformat()}",
            company_id=str(company_id) if company_id else "all",
        )

        return count
