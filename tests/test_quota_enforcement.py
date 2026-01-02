"""
Tests for Quota Enforcement with Load Testing

Tests for verifying quota enforcement including:
- Basic quota limit checking
- Quota exceeded returns HTTP 429
- Concurrent request handling (race condition prevention)
- Quota reservation and release
- SELECT FOR UPDATE prevents overselling

Run with: pytest tests/test_quota_enforcement.py -v
"""

import pytest
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mark all tests in this module as integration tests requiring database
pytestmark = [pytest.mark.integration]


def _check_database_connection():
    """Check if database connection is available"""
    try:
        from sqlalchemy import text
        from src.config.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# Skip all tests if database is not available
if not _check_database_connection():
    pytest.skip("Database connection not available", allow_module_level=True)


from sqlalchemy import text
from fastapi.testclient import TestClient

from src.config.database import engine, SessionLocal, get_db
from src.infrastructure.providers.team_repository import SQLAlchemyTeamRepository
from src.models.rbac import Team, TeamMember, TeamQuota, Role
from src.core.jwt import create_access_token
from src.core.permissions import GPU_PROVISION


# Import the FastAPI app from src.main
from src.main import create_app


@pytest.fixture(scope="module")
def app():
    """Create FastAPI application"""
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    """Create test client"""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="function")
def db_session():
    """Create database session for tests"""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def team_repo(db_session):
    """Create team repository for tests"""
    return SQLAlchemyTeamRepository(db_session)


@pytest.fixture
def unique_id():
    """Generate unique ID for test isolation"""
    return uuid.uuid4().hex[:8]


@pytest.fixture
def admin_role(db_session):
    """Get or create admin role for tests"""
    role = db_session.query(Role).filter(
        Role.name == 'admin',
        Role.is_system == True
    ).first()

    if not role:
        role = Role(
            name='admin',
            display_name='Admin',
            description='Full control',
            is_system=True
        )
        db_session.add(role)
        db_session.flush()

    return role


def create_auth_token(
    email: str,
    team_id: int = None,
    role: str = None,
    permissions: list = None,
) -> str:
    """Create an auth token for testing"""
    return create_access_token(
        email=email,
        team_id=team_id,
        role=role,
        permissions=permissions,
    )


def auth_headers(token: str) -> dict:
    """Create authorization headers"""
    return {"Authorization": f"Bearer {token}"}


class TestQuotaRepository:
    """Tests for TeamRepository quota methods"""

    def test_get_quota_returns_none_when_not_set(self, team_repo, admin_role, unique_id, db_session):
        """get_quota should return None when team has no quota"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team without quota
        team = team_repo.create_team(
            name=f"No Quota Team {unique_id}",
            slug=f"no-quota-team-{unique_id}",
            owner_user_id=owner_email,
        )
        db_session.flush()

        quota = team_repo.get_quota(team.id)
        assert quota is None

    def test_create_quota(self, team_repo, admin_role, unique_id, db_session):
        """create_or_update_quota should create quota when not exists"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Quota Team {unique_id}",
            slug=f"quota-team-{unique_id}",
            owner_user_id=owner_email,
        )
        db_session.flush()

        quota = team_repo.create_or_update_quota(
            team_id=team.id,
            max_gpu_hours_per_month=100.0,
            max_concurrent_instances=5,
            max_monthly_budget_usd=500.0,
        )
        db_session.flush()

        assert quota is not None
        assert quota.team_id == team.id
        assert quota.max_concurrent_instances == 5
        assert quota.current_concurrent_instances == 0

    def test_update_quota(self, team_repo, admin_role, unique_id, db_session):
        """create_or_update_quota should update existing quota"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Update Quota Team {unique_id}",
            slug=f"update-quota-team-{unique_id}",
            owner_user_id=owner_email,
        )

        # Create initial quota
        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5,
        )
        db_session.flush()

        # Update quota
        updated_quota = team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=10,
        )
        db_session.flush()

        assert updated_quota.max_concurrent_instances == 10

    def test_check_quota_available_under_limit(self, team_repo, unique_id, db_session):
        """check_quota_available should return available=True when under limit"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Under Limit Team {unique_id}",
            slug=f"under-limit-team-{unique_id}",
            owner_user_id=owner_email,
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5,
        )
        db_session.flush()

        result = team_repo.check_quota_available(
            team_id=team.id,
            instances_needed=1
        )

        assert result['available'] == True
        assert result['quota_exists'] == True
        assert len(result['violations']) == 0

    def test_check_quota_available_at_limit(self, team_repo, unique_id, db_session):
        """check_quota_available should return available=False when at limit"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"At Limit Team {unique_id}",
            slug=f"at-limit-team-{unique_id}",
            owner_user_id=owner_email,
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=2,
        )
        db_session.flush()

        # Simulate 2 instances already running
        quota = team_repo.get_quota(team.id)
        quota.current_concurrent_instances = 2
        db_session.flush()

        result = team_repo.check_quota_available(
            team_id=team.id,
            instances_needed=1
        )

        assert result['available'] == False
        assert len(result['violations']) > 0
        assert result['violations'][0]['type'] == 'concurrent_instances'

    def test_check_quota_available_no_quota_unlimited(self, team_repo, unique_id, db_session):
        """check_quota_available should allow unlimited when no quota set"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Unlimited Team {unique_id}",
            slug=f"unlimited-team-{unique_id}",
            owner_user_id=owner_email,
        )
        db_session.flush()

        result = team_repo.check_quota_available(
            team_id=team.id,
            instances_needed=100  # Large number should be allowed
        )

        assert result['available'] == True
        assert result['quota_exists'] == False

    def test_check_and_reserve_instance_quota_success(self, team_repo, unique_id, db_session):
        """check_and_reserve_instance_quota should reserve quota when available"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Reserve Team {unique_id}",
            slug=f"reserve-team-{unique_id}",
            owner_user_id=owner_email,
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5,
        )
        db_session.flush()

        result = team_repo.check_and_reserve_instance_quota(
            team_id=team.id,
            instances_needed=1
        )

        assert result['available'] == True
        assert result['quota'].current_concurrent_instances == 1

    def test_check_and_reserve_instance_quota_exceeds_limit(self, team_repo, unique_id, db_session):
        """check_and_reserve_instance_quota should fail when exceeding limit"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Exceed Team {unique_id}",
            slug=f"exceed-team-{unique_id}",
            owner_user_id=owner_email,
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=1,
        )
        db_session.flush()

        # First reservation should succeed
        result1 = team_repo.check_and_reserve_instance_quota(team.id, 1)
        assert result1['available'] == True
        db_session.flush()

        # Second reservation should fail
        result2 = team_repo.check_and_reserve_instance_quota(team.id, 1)
        assert result2['available'] == False
        assert len(result2['violations']) > 0
        assert 'max_concurrent_instances' in result2['violations'][0]['type']

    def test_release_instance_quota(self, team_repo, unique_id, db_session):
        """release_instance_quota should decrement counter"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Release Team {unique_id}",
            slug=f"release-team-{unique_id}",
            owner_user_id=owner_email,
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5,
        )
        db_session.flush()

        # Reserve an instance
        team_repo.check_and_reserve_instance_quota(team.id, 1)
        db_session.flush()

        quota = team_repo.get_quota(team.id)
        assert quota.current_concurrent_instances == 1

        # Release the instance
        team_repo.release_instance_quota(team.id, 1)
        db_session.flush()

        quota = team_repo.get_quota(team.id)
        assert quota.current_concurrent_instances == 0

    def test_release_instance_quota_not_negative(self, team_repo, unique_id, db_session):
        """release_instance_quota should not go below zero"""
        owner_email = f"owner_{unique_id}@test.com"

        team = team_repo.create_team(
            name=f"Not Negative Team {unique_id}",
            slug=f"not-negative-team-{unique_id}",
            owner_user_id=owner_email,
        )

        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5,
        )
        db_session.flush()

        # Release without reserving first
        team_repo.release_instance_quota(team.id, 5)
        db_session.flush()

        quota = team_repo.get_quota(team.id)
        assert quota.current_concurrent_instances == 0  # Should not be negative


class TestQuotaEnforcementConcurrency:
    """Tests for concurrent quota enforcement (race condition prevention)"""

    def test_concurrent_reservations_with_row_locking(self, unique_id, db_session):
        """
        Test that SELECT FOR UPDATE prevents race conditions.
        Multiple concurrent requests should not exceed the quota limit.
        """
        owner_email = f"owner_{unique_id}@test.com"

        # Create team with quota of 3 instances
        repo = SQLAlchemyTeamRepository(db_session)
        team = repo.create_team(
            name=f"Concurrent Team {unique_id}",
            slug=f"concurrent-team-{unique_id}",
            owner_user_id=owner_email,
        )

        repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=3,
        )
        db_session.commit()

        team_id = team.id
        success_count = 0
        failure_count = 0
        lock = threading.Lock()

        def try_reserve():
            """Attempt to reserve an instance in a separate session"""
            nonlocal success_count, failure_count
            session = SessionLocal()
            try:
                r = SQLAlchemyTeamRepository(session)
                result = r.check_and_reserve_instance_quota(team_id, 1)
                session.commit()

                with lock:
                    if result['available']:
                        success_count += 1
                    else:
                        failure_count += 1
            except Exception as e:
                with lock:
                    failure_count += 1
            finally:
                session.close()

        # Try to reserve 10 instances concurrently (only 3 should succeed)
        num_threads = 10
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_reserve) for _ in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        # Exactly 3 should succeed, 7 should fail
        assert success_count == 3, f"Expected 3 successes, got {success_count}"
        assert failure_count == 7, f"Expected 7 failures, got {failure_count}"

        # Verify final quota count
        final_session = SessionLocal()
        try:
            final_repo = SQLAlchemyTeamRepository(final_session)
            final_quota = final_repo.get_quota(team_id)
            assert final_quota.current_concurrent_instances == 3
        finally:
            final_session.close()

    def test_rapid_reserve_release_cycles(self, unique_id, db_session):
        """
        Test rapid reserve/release cycles don't corrupt quota counter.
        Each thread reserves and releases, final count should be 0.
        """
        owner_email = f"owner_{unique_id}@test.com"

        repo = SQLAlchemyTeamRepository(db_session)
        team = repo.create_team(
            name=f"Rapid Team {unique_id}",
            slug=f"rapid-team-{unique_id}",
            owner_user_id=owner_email,
        )

        repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=100,  # High limit for this test
        )
        db_session.commit()

        team_id = team.id
        errors = []

        def reserve_and_release():
            """Reserve then release an instance"""
            session = SessionLocal()
            try:
                r = SQLAlchemyTeamRepository(session)
                result = r.check_and_reserve_instance_quota(team_id, 1)
                session.commit()

                if result['available']:
                    # Simulate some work
                    time.sleep(0.01)

                    # Release
                    r.release_instance_quota(team_id, 1)
                    session.commit()
            except Exception as e:
                errors.append(str(e))
            finally:
                session.close()

        # Run 20 concurrent reserve/release cycles
        num_threads = 20
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(reserve_and_release) for _ in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        # Final count should be 0 (all reserved/released)
        final_session = SessionLocal()
        try:
            final_repo = SQLAlchemyTeamRepository(final_session)
            final_quota = final_repo.get_quota(team_id)
            assert final_quota.current_concurrent_instances == 0, \
                f"Expected 0 after all releases, got {final_quota.current_concurrent_instances}"
        finally:
            final_session.close()

        assert len(errors) == 0, f"Errors during test: {errors}"


class TestQuotaAPI:
    """Tests for quota enforcement via API endpoints"""

    def test_create_instance_returns_429_when_quota_exceeded(
        self, client, team_repo, admin_role, unique_id, db_session
    ):
        """POST /api/v1/instances should return 429 when quota exceeded"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team with quota of 0 instances (will always exceed)
        team = team_repo.create_team(
            name=f"Zero Quota Team {unique_id}",
            slug=f"zero-quota-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=0,  # Zero instances allowed
        )
        db_session.commit()

        # Create token with team context
        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[GPU_PROVISION],
        )

        # Try to create instance (should be rejected)
        response = client.post(
            "/api/v1/instances",
            json={
                "offer_id": 12345,
                "image": "pytorch/pytorch:latest",
                "disk_size": 50,
            },
            headers=auth_headers(token),
        )

        assert response.status_code == 429
        assert "quota exceeded" in response.json()["detail"].lower()

    def test_create_instance_succeeds_under_quota(
        self, client, team_repo, admin_role, unique_id, db_session
    ):
        """POST /api/v1/instances should succeed when under quota (demo mode)"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create team with quota allowing instances
        team = team_repo.create_team(
            name=f"Has Quota Team {unique_id}",
            slug=f"has-quota-team-{unique_id}",
            owner_user_id=owner_email,
        )
        team_repo.add_member(team.id, owner_email, admin_role.id)
        team_repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=5,
        )
        db_session.commit()

        # Create token with team context
        token = create_auth_token(
            owner_email,
            team_id=team.id,
            role="admin",
            permissions=[GPU_PROVISION],
        )

        # In demo mode, this should succeed
        response = client.post(
            "/api/v1/instances?demo=true",
            json={
                "offer_id": 12345,
                "image": "pytorch/pytorch:latest",
                "disk_size": 50,
            },
            headers=auth_headers(token),
        )

        # Demo mode returns 201, not quota restricted
        assert response.status_code == 201

    def test_create_instance_no_team_context_bypasses_quota(
        self, client, unique_id
    ):
        """POST /api/v1/instances without team context should not check quota"""
        owner_email = f"owner_{unique_id}@test.com"

        # Create token without team context
        token = create_auth_token(
            owner_email,
            permissions=[GPU_PROVISION],
        )

        # In demo mode without team, should succeed (no quota check)
        response = client.post(
            "/api/v1/instances?demo=true",
            json={
                "offer_id": 12345,
                "image": "pytorch/pytorch:latest",
                "disk_size": 50,
            },
            headers=auth_headers(token),
        )

        # Demo mode should return success
        assert response.status_code == 201


class TestQuotaModel:
    """Tests for TeamQuota model methods"""

    def test_is_concurrent_instances_exceeded_true(self, db_session):
        """is_concurrent_instances_exceeded returns True when at limit"""
        quota = TeamQuota(
            team_id=1,
            max_concurrent_instances=5,
            current_concurrent_instances=5,
        )

        assert quota.is_concurrent_instances_exceeded() == True

    def test_is_concurrent_instances_exceeded_false(self, db_session):
        """is_concurrent_instances_exceeded returns False when under limit"""
        quota = TeamQuota(
            team_id=1,
            max_concurrent_instances=5,
            current_concurrent_instances=3,
        )

        assert quota.is_concurrent_instances_exceeded() == False

    def test_is_concurrent_instances_exceeded_unlimited(self, db_session):
        """is_concurrent_instances_exceeded returns False when unlimited"""
        quota = TeamQuota(
            team_id=1,
            max_concurrent_instances=None,  # Unlimited
            current_concurrent_instances=100,
        )

        assert quota.is_concurrent_instances_exceeded() == False

    def test_quota_warning_threshold(self, db_session):
        """should_warn_* methods check against thresholds"""
        quota = TeamQuota(
            team_id=1,
            max_gpu_hours_per_month=100.0,
            current_gpu_hours_used=85.0,
            warn_at_gpu_hours_percent=80.0,
            max_monthly_budget_usd=1000.0,
            current_monthly_spend_usd=850.0,
            warn_at_budget_percent=80.0,
        )

        assert quota.should_warn_gpu_hours() == True
        assert quota.should_warn_budget() == True

    def test_quota_to_dict_structure(self, db_session):
        """to_dict returns correct structure"""
        now = datetime.utcnow()
        quota = TeamQuota(
            id=1,
            team_id=1,
            max_gpu_hours_per_month=100.0,
            max_concurrent_instances=5,
            max_monthly_budget_usd=500.0,
            current_gpu_hours_used=25.0,
            current_concurrent_instances=2,
            current_monthly_spend_usd=100.0,
            created_at=now,
            updated_at=now,
        )

        result = quota.to_dict()

        assert 'limits' in result
        assert 'usage' in result
        assert result['limits']['max_concurrent_instances'] == 5
        assert result['usage']['concurrent_instances'] == 2


class TestQuotaLoadSimulation:
    """
    Load testing simulations for quota enforcement.
    These tests verify the system can handle high concurrent load.
    """

    def test_high_concurrency_stress_test(self, unique_id, db_session):
        """
        Stress test with high concurrency to verify no race conditions.
        """
        owner_email = f"stress_{unique_id}@test.com"

        repo = SQLAlchemyTeamRepository(db_session)
        team = repo.create_team(
            name=f"Stress Team {unique_id}",
            slug=f"stress-team-{unique_id}",
            owner_user_id=owner_email,
        )

        # Allow 10 instances
        repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=10,
        )
        db_session.commit()

        team_id = team.id
        results = {'success': 0, 'failure': 0}
        lock = threading.Lock()

        def attempt_reservation():
            session = SessionLocal()
            try:
                r = SQLAlchemyTeamRepository(session)
                result = r.check_and_reserve_instance_quota(team_id, 1)
                session.commit()

                with lock:
                    if result['available']:
                        results['success'] += 1
                    else:
                        results['failure'] += 1
            except Exception:
                with lock:
                    results['failure'] += 1
            finally:
                session.close()

        # 50 concurrent attempts for 10 slots
        num_threads = 50
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(attempt_reservation) for _ in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

        # Exactly 10 should succeed
        assert results['success'] == 10, \
            f"Expected 10 successes, got {results['success']}"
        assert results['failure'] == 40, \
            f"Expected 40 failures, got {results['failure']}"

        # Verify quota is exactly at limit
        final_session = SessionLocal()
        try:
            final_repo = SQLAlchemyTeamRepository(final_session)
            final_quota = final_repo.get_quota(team_id)
            assert final_quota.current_concurrent_instances == 10, \
                f"Expected quota at 10, got {final_quota.current_concurrent_instances}"
        finally:
            final_session.close()

    def test_mixed_operations_concurrent(self, unique_id, db_session):
        """
        Test mixed reserve/release operations concurrently.
        """
        owner_email = f"mixed_{unique_id}@test.com"

        repo = SQLAlchemyTeamRepository(db_session)
        team = repo.create_team(
            name=f"Mixed Team {unique_id}",
            slug=f"mixed-team-{unique_id}",
            owner_user_id=owner_email,
        )

        repo.create_or_update_quota(
            team_id=team.id,
            max_concurrent_instances=20,
        )
        db_session.commit()

        team_id = team.id

        # Track operations
        operations = {'reserves': 0, 'releases': 0}
        lock = threading.Lock()

        def reserve():
            session = SessionLocal()
            try:
                r = SQLAlchemyTeamRepository(session)
                result = r.check_and_reserve_instance_quota(team_id, 1)
                session.commit()

                with lock:
                    if result['available']:
                        operations['reserves'] += 1
            finally:
                session.close()

        def release():
            session = SessionLocal()
            try:
                r = SQLAlchemyTeamRepository(session)
                r.release_instance_quota(team_id, 1)
                session.commit()

                with lock:
                    operations['releases'] += 1
            finally:
                session.close()

        # Mix of reserves and releases
        with ThreadPoolExecutor(max_workers=30) as executor:
            # 15 reserves, 10 releases
            reserve_futures = [executor.submit(reserve) for _ in range(15)]
            release_futures = [executor.submit(release) for _ in range(10)]

            for future in as_completed(reserve_futures + release_futures):
                try:
                    future.result()
                except Exception:
                    pass

        # Final quota should reflect net operations
        final_session = SessionLocal()
        try:
            final_repo = SQLAlchemyTeamRepository(final_session)
            final_quota = final_repo.get_quota(team_id)

            # At most 15 reserves, 10 releases = net 5 max (but some reserves may fail)
            # And releases won't go below 0
            assert final_quota.current_concurrent_instances >= 0, \
                f"Quota should not be negative: {final_quota.current_concurrent_instances}"
            assert final_quota.current_concurrent_instances <= 15, \
                f"Quota should not exceed 15: {final_quota.current_concurrent_instances}"
        finally:
            final_session.close()
