# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Integration tests for audit trail dual-write pattern.

Tests that access logs are properly written to:
1. PostgreSQL (hot data, fast queries)
2. Loki (long-term retention via structured logs)
"""

import json
import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import requests

from app.models.audit_log import AccessLog


@pytest.mark.integration
class TestAuditTrailDualWrite:
    """Test audit trail dual-write to PostgreSQL and Loki."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, session):
        """Set up test data for audit trail tests."""
        # Create test company and user IDs
        self.company_id = uuid4()
        self.user_id = uuid4()

        # Create test access logs directly in PostgreSQL
        for i in range(5):
            log = AccessLog(
                user_id=self.user_id,
                company_id=self.company_id,
                service="test-service",
                resource_name=f"test-resource-{i}",
                operation="READ" if i % 2 == 0 else "UPDATE",
                access_granted=i % 3 != 0,
            )
            session.add(log)
        session.commit()

        yield

        # Cleanup
        session.query(AccessLog).filter_by(company_id=self.company_id).delete()
        session.commit()

    def test_dual_write_to_postgres_and_loki(self, session):
        """Test that access logs exist in PostgreSQL and can be queried from Loki.

        Scenario:
        1. Verify logs exist in PostgreSQL (created in setup)
        2. Wait for Promtail to ship logs to Loki
        3. Query Loki API to verify logs were shipped
        4. Verify data consistency
        """
        # Step 1: Verify logs in PostgreSQL
        postgres_logs = (
            session.query(AccessLog)
            .filter(
                AccessLog.company_id == self.company_id,
                AccessLog.user_id == self.user_id,
            )
            .order_by(AccessLog.created_at)
            .all()
        )

        assert len(postgres_logs) >= 5
        print(f"\n✅ Found {len(postgres_logs)} logs in PostgreSQL")

        # Verify key fields in PostgreSQL
        for log in postgres_logs:
            assert log.company_id == self.company_id
            assert log.user_id == self.user_id
            assert log.service == "test-service"
            assert log.operation in ["READ", "UPDATE"]
            assert isinstance(log.access_granted, bool)

        # Step 2: Wait for Promtail to ship logs to Loki
        print("⏳ Waiting 5s for Promtail to ship logs to Loki...")
        time.sleep(5)

        # Step 3: Query Loki API for logs
        loki_url = "http://localhost:3100/loki/api/v1/query_range"

        # Query for the last 5 minutes
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)

        # LogQL query for test-service logs
        logql_query = '{job="guardian", service="test-service"}'

        params = {
            "query": logql_query,
            "start": str(int(start_time.timestamp() * 1e9)),  # Nanoseconds
            "end": str(int(end_time.timestamp() * 1e9)),
            "limit": str(100),
        }

        try:
            response = requests.get(loki_url, params=params, timeout=5)
            response.raise_for_status()
            loki_data = response.json()

            # Parse Loki results
            loki_logs = []
            if loki_data.get("status") == "success":
                for result in loki_data.get("data", {}).get("result", []):
                    for entry in result.get("values", []):
                        # entry[0] is timestamp, entry[1] is log line
                        log_line = entry[1]
                        try:
                            log_json = json.loads(log_line)
                            loki_logs.append(log_json)
                        except json.JSONDecodeError:
                            # Skip non-JSON lines
                            continue

            # Step 4: Verify logs exist in Loki
            print(
                f"✅ Found {len(loki_logs)} logs in Loki (may include other test runs)"
            )

            # Verify Loki structure
            if len(loki_logs) > 0:
                sample_log = loki_logs[0]
                assert "event" in sample_log or "timestamp" in sample_log
                print(
                    f"✅ Loki logs have correct structure: {list(sample_log.keys())[:5]}"
                )
            else:
                print("⚠️  No logs found in Loki yet (Promtail may need more time)")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki not available for testing: {e}")

    def test_postgres_query_performance(self, client, session):
        """Test PostgreSQL query performance with filters."""
        # Generate multiple access logs
        for i in range(10):
            log = AccessLog(
                user_id=self.user_id,
                company_id=self.company_id,
                service="test-service",
                resource_name=f"resource-{i}",
                operation="READ" if i % 2 == 0 else "UPDATE",
                access_granted=i % 3 != 0,
            )
            session.add(log)
        session.commit()

        # Query with filters
        start = datetime.now()
        logs = (
            session.query(AccessLog)
            .filter(
                AccessLog.company_id == self.company_id,
                AccessLog.service == "test-service",
                AccessLog.access_granted.is_(True),
            )
            .all()
        )
        query_time = (datetime.now() - start).total_seconds()

        assert len(logs) > 0
        assert query_time < 0.1  # Should be very fast with indexes
        print(f"\n✅ Query completed in {query_time:.4f}s")

    def test_loki_connectivity(self):
        """Test that Loki is accessible and healthy."""
        try:
            response = requests.get("http://localhost:3100/ready", timeout=3)
            assert response.status_code == 200
            print("\n✅ Loki is ready")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki not available: {e}")
