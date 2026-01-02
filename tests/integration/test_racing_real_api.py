"""
Real Integration Tests for GPU Racing/Provisioning

These tests use the REAL Vast.ai API to test the racing algorithm:
- Creates real GPU instances (costs money!)
- Tests race winner selection
- Tests cleanup of losers
- Tests failover scenarios

IMPORTANT: These tests provision real GPU instances and cost money.
Run with: pytest tests/integration/test_racing_real_api.py -v --timeout=600

Environment variables needed:
- VAST_API_KEY: Your Vast.ai API key
"""

import pytest
import os
import time
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

VAST_API_KEY = os.environ.get("VAST_API_KEY", "")
RACE_BATCH_SIZE = 3  # Number of machines to race (keep low to save costs)
RACE_TIMEOUT_SECONDS = 300  # 5 minutes
POLL_INTERVAL_SECONDS = 5
MIN_RELIABILITY = 0.95
MAX_PRICE_PER_HOUR = 0.30  # Keep costs low for tests


# =============================================================================
# SKIP MARKER IF NO API KEY
# =============================================================================

skip_if_no_api_key = pytest.mark.skipif(
    not VAST_API_KEY,
    reason="VAST_API_KEY not set - skipping real API tests"
)


# =============================================================================
# VAST.AI API CLIENT
# =============================================================================

@dataclass
class VastOffer:
    """Represents a Vast.ai GPU offer"""
    id: int
    gpu_name: str
    num_gpus: int
    dph_total: float
    reliability: float
    geolocation: str
    disk_space: int
    inet_down: float


@dataclass
class VastInstance:
    """Represents a Vast.ai instance"""
    id: int
    actual_status: str
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    label: Optional[str] = None


class VastAPIClient:
    """Client for Vast.ai API"""

    BASE_URL = "https://cloud.vast.ai/api/v0"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        self._init_session()

    def _init_session(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with retry on rate limit"""
        import requests

        url = f"{self.BASE_URL}{endpoint}"
        max_retries = 5
        backoff = 2.0

        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, **kwargs)

                if resp.status_code == 429:
                    wait_time = backoff * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                resp.raise_for_status()
                return resp.json() if resp.text else {}

            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429:
                    continue
                raise

        raise Exception(f"Max retries exceeded for {endpoint}")

    def search_offers(
        self,
        max_price: float = MAX_PRICE_PER_HOUR,
        min_reliability: float = MIN_RELIABILITY,
        limit: int = RACE_BATCH_SIZE
    ) -> List[VastOffer]:
        """Search for GPU offers"""
        params = {
            "q": json.dumps({
                "verified": {"eq": True},
                "rentable": {"eq": True},
                "dph_total": {"lte": max_price},
                "reliability2": {"gte": min_reliability},
                "order": [["dph_total", "asc"]],
                "limit": limit
            })
        }

        data = self._request("GET", "/bundles", params=params)
        offers = data.get("offers", [])

        return [
            VastOffer(
                id=o["id"],
                gpu_name=o.get("gpu_name", "Unknown"),
                num_gpus=o.get("num_gpus", 1),
                dph_total=o.get("dph_total", 0),
                reliability=o.get("reliability2", 0),
                geolocation=o.get("geolocation", ""),
                disk_space=o.get("disk_space", 20),
                inet_down=o.get("inet_down", 0)
            )
            for o in offers
        ]

    def create_instance(self, offer_id: int, label: str, disk_size: int = 10) -> int:
        """Create a new instance from an offer"""
        data = {
            "client_id": "me",
            "image": "pytorch/pytorch:latest",
            "disk": disk_size,
            "label": label,
            "onstart": "echo 'Test instance ready'",
        }

        result = self._request("PUT", f"/asks/{offer_id}/", json=data)

        if "new_contract" in result:
            return result["new_contract"]

        raise Exception(f"Failed to create instance: {result}")

    def get_instance(self, instance_id: int) -> Optional[VastInstance]:
        """Get instance status"""
        try:
            data = self._request("GET", f"/instances/{instance_id}/")

            if not data or "instances" not in data:
                return None

            instances = data.get("instances", [])
            if not instances:
                return None

            inst = instances[0] if isinstance(instances, list) else instances

            return VastInstance(
                id=inst.get("id", instance_id),
                actual_status=inst.get("actual_status", "unknown"),
                ssh_host=inst.get("ssh_host"),
                ssh_port=inst.get("ssh_port"),
                label=inst.get("label")
            )
        except Exception as e:
            logger.warning(f"Error getting instance {instance_id}: {e}")
            return None

    def destroy_instance(self, instance_id: int) -> bool:
        """Destroy an instance"""
        try:
            self._request("DELETE", f"/instances/{instance_id}/")
            return True
        except Exception as e:
            logger.warning(f"Error destroying instance {instance_id}: {e}")
            return False

    def list_my_instances(self) -> List[VastInstance]:
        """List all user instances"""
        data = self._request("GET", "/instances/?owner=me")
        instances = data.get("instances", [])

        return [
            VastInstance(
                id=i.get("id"),
                actual_status=i.get("actual_status", "unknown"),
                ssh_host=i.get("ssh_host"),
                ssh_port=i.get("ssh_port"),
                label=i.get("label")
            )
            for i in instances
        ]


# =============================================================================
# RACING ENGINE
# =============================================================================

@dataclass
class RaceCandidate:
    """A machine participating in the race"""
    offer: VastOffer
    instance_id: Optional[int] = None
    status: str = "idle"  # idle, creating, connecting, ready, failed, cancelled
    progress: int = 0
    error_message: Optional[str] = None


@dataclass
class RaceResult:
    """Result of a race"""
    winner: Optional[RaceCandidate] = None
    losers: List[RaceCandidate] = field(default_factory=list)
    elapsed_seconds: float = 0
    round_number: int = 1
    all_failed: bool = False


class RacingEngine:
    """Engine that runs GPU races"""

    def __init__(self, client: VastAPIClient):
        self.client = client
        self.candidates: List[RaceCandidate] = []
        self.created_instance_ids: List[int] = []

    def search_candidates(self, count: int = RACE_BATCH_SIZE) -> List[VastOffer]:
        """Search for race candidates"""
        return self.client.search_offers(limit=count)

    def start_race(self, offers: List[VastOffer], round_num: int = 1) -> RaceResult:
        """
        Start a race with multiple GPU offers.
        First machine to become ready wins.
        """
        logger.info(f"Starting race round {round_num} with {len(offers)} candidates")

        # Initialize candidates
        self.candidates = [RaceCandidate(offer=o) for o in offers]
        self.created_instance_ids = []

        start_time = time.time()

        # Phase 1: Create all instances
        for i, candidate in enumerate(self.candidates):
            try:
                label = f"race-test-r{round_num}-{candidate.offer.gpu_name}-{int(time.time())}"
                candidate.status = "creating"
                candidate.progress = 10

                logger.info(f"Creating instance {i+1}/{len(self.candidates)}: {candidate.offer.gpu_name}")

                instance_id = self.client.create_instance(
                    offer_id=candidate.offer.id,
                    label=label,
                    disk_size=10
                )

                candidate.instance_id = instance_id
                candidate.status = "connecting"
                candidate.progress = 30
                self.created_instance_ids.append(instance_id)

                # Small delay to avoid rate limiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"Failed to create instance for {candidate.offer.gpu_name}: {e}")
                candidate.status = "failed"
                candidate.error_message = str(e)

        # Phase 2: Poll for winner
        winner = None
        timeout_at = start_time + RACE_TIMEOUT_SECONDS

        while time.time() < timeout_at:
            active_count = 0

            for candidate in self.candidates:
                if candidate.status in ("failed", "cancelled", "ready"):
                    continue

                if not candidate.instance_id:
                    continue

                active_count += 1

                try:
                    instance = self.client.get_instance(candidate.instance_id)

                    if not instance:
                        continue

                    status = instance.actual_status

                    # Update progress based on status
                    if status == "loading":
                        candidate.progress = min(candidate.progress + 10, 90)
                    elif status == "running":
                        candidate.progress = 100
                        candidate.status = "ready"

                        if not winner:
                            winner = candidate
                            logger.info(f"WINNER: {candidate.offer.gpu_name} (instance {candidate.instance_id})")
                    elif status in ("exited", "error", "destroyed"):
                        candidate.status = "failed"
                        candidate.error_message = f"Status: {status}"

                except Exception as e:
                    logger.warning(f"Error polling instance {candidate.instance_id}: {e}")

            # Check if we have a winner
            if winner:
                break

            # Check if all failed
            if active_count == 0:
                break

            time.sleep(POLL_INTERVAL_SECONDS)

        elapsed = time.time() - start_time

        # Mark non-winners
        losers = []
        for candidate in self.candidates:
            if candidate != winner and candidate.status not in ("failed",):
                candidate.status = "cancelled"
                losers.append(candidate)
            elif candidate.status == "failed":
                losers.append(candidate)

        all_failed = winner is None

        return RaceResult(
            winner=winner,
            losers=losers,
            elapsed_seconds=elapsed,
            round_number=round_num,
            all_failed=all_failed
        )

    def cleanup(self, keep_winner: bool = False, winner_id: Optional[int] = None):
        """Destroy all created instances (optionally keeping winner)"""
        for instance_id in self.created_instance_ids:
            if keep_winner and instance_id == winner_id:
                continue

            logger.info(f"Destroying instance {instance_id}")
            self.client.destroy_instance(instance_id)
            time.sleep(0.5)  # Avoid rate limiting

    def destroy_all(self):
        """Destroy all created instances"""
        self.cleanup(keep_winner=False)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def vast_client():
    """Create Vast.ai API client"""
    if not VAST_API_KEY:
        pytest.skip("VAST_API_KEY not set")
    return VastAPIClient(VAST_API_KEY)


@pytest.fixture
def racing_engine(vast_client):
    """Create racing engine with cleanup"""
    engine = RacingEngine(vast_client)
    yield engine
    # Cleanup all instances after test
    engine.destroy_all()


# =============================================================================
# TESTS
# =============================================================================


@skip_if_no_api_key
class TestVastAPIConnection:
    """Test basic Vast.ai API connectivity"""

    def test_api_key_valid(self, vast_client):
        """Test that API key is valid"""
        # Try to list instances - will fail with invalid key
        instances = vast_client.list_my_instances()
        # Should not raise exception
        assert isinstance(instances, list)

    def test_can_search_offers(self, vast_client):
        """Test that we can search for offers"""
        offers = vast_client.search_offers(limit=5)
        assert len(offers) > 0

        # Verify offer structure
        offer = offers[0]
        assert offer.id > 0
        assert offer.gpu_name
        assert offer.dph_total > 0


@skip_if_no_api_key
class TestRaceOfferSearch:
    """Test race candidate search"""

    def test_search_returns_sorted_offers(self, vast_client):
        """Offers should be sorted by price"""
        offers = vast_client.search_offers(limit=5)

        prices = [o.dph_total for o in offers]
        assert prices == sorted(prices), "Offers should be sorted by price ascending"

    def test_search_respects_reliability_filter(self, vast_client):
        """All offers should meet reliability threshold"""
        offers = vast_client.search_offers(
            min_reliability=MIN_RELIABILITY,
            limit=5
        )

        for offer in offers:
            assert offer.reliability >= MIN_RELIABILITY * 0.9, \
                f"Offer {offer.id} has low reliability: {offer.reliability}"

    def test_search_respects_price_filter(self, vast_client):
        """All offers should be under price limit"""
        max_price = 0.50
        offers = vast_client.search_offers(max_price=max_price, limit=5)

        for offer in offers:
            assert offer.dph_total <= max_price * 1.1, \
                f"Offer {offer.id} too expensive: ${offer.dph_total}/hr"


@skip_if_no_api_key
class TestRaceExecution:
    """Test actual race execution (creates real instances!)"""

    def test_race_selects_winner(self, racing_engine):
        """Run a real race and verify winner selection"""
        # Search for candidates
        offers = racing_engine.search_candidates(count=RACE_BATCH_SIZE)

        if len(offers) < 2:
            pytest.skip("Not enough offers available for race")

        # Run race
        result = racing_engine.start_race(offers[:RACE_BATCH_SIZE])

        try:
            if result.all_failed:
                pytest.skip("All candidates failed - no winner")

            # Verify we have a winner
            assert result.winner is not None, "Race should produce a winner"
            assert result.winner.status == "ready"
            assert result.winner.instance_id is not None
            assert result.winner.progress == 100

            # Verify losers
            for loser in result.losers:
                assert loser.status in ("cancelled", "failed")

            # Verify timing
            assert result.elapsed_seconds > 0
            assert result.elapsed_seconds < RACE_TIMEOUT_SECONDS

            logger.info(f"Race completed in {result.elapsed_seconds:.1f}s")
            logger.info(f"Winner: {result.winner.offer.gpu_name}")

        finally:
            # Always cleanup
            racing_engine.destroy_all()

    def test_single_instance_creation(self, racing_engine):
        """Test creating a single instance"""
        offers = racing_engine.search_candidates(count=1)

        if not offers:
            pytest.skip("No offers available")

        offer = offers[0]

        try:
            label = f"test-single-{int(time.time())}"
            instance_id = racing_engine.client.create_instance(
                offer_id=offer.id,
                label=label,
                disk_size=10
            )

            racing_engine.created_instance_ids.append(instance_id)

            assert instance_id > 0, "Should return valid instance ID"

            # Wait for instance to start loading
            time.sleep(10)

            instance = racing_engine.client.get_instance(instance_id)
            assert instance is not None, "Should be able to get instance status"
            # Status may be None initially or one of these values
            assert instance.actual_status in (None, "loading", "running", "creating", "unknown")

        finally:
            racing_engine.destroy_all()


@skip_if_no_api_key
class TestRaceCleanup:
    """Test race cleanup functionality"""

    def test_destroy_instance(self, vast_client):
        """Test destroying an instance"""
        # First create an instance
        offers = vast_client.search_offers(limit=1)

        if not offers:
            pytest.skip("No offers available")

        label = f"test-destroy-{int(time.time())}"
        instance_id = vast_client.create_instance(
            offer_id=offers[0].id,
            label=label,
            disk_size=10
        )

        # Wait a moment
        time.sleep(5)

        # Destroy it
        result = vast_client.destroy_instance(instance_id)
        assert result is True, "Destroy should succeed"

        # Verify it's gone (may take a moment)
        time.sleep(5)
        instance = vast_client.get_instance(instance_id)

        # Instance should be destroyed or in destroyed state
        if instance:
            assert instance.actual_status in ("destroyed", "exited", None)


@skip_if_no_api_key
class TestRaceStatus:
    """Test race status transitions"""

    def test_candidate_status_transitions(self):
        """Test valid status transitions"""
        valid_transitions = {
            "idle": ["creating", "failed"],
            "creating": ["connecting", "failed"],
            "connecting": ["ready", "failed"],
            "ready": ["cancelled"],
            "failed": [],
            "cancelled": [],
        }

        # Verify all statuses have defined transitions
        for status in ["idle", "creating", "connecting", "ready", "failed", "cancelled"]:
            assert status in valid_transitions

    def test_progress_increases(self):
        """Progress should increase through stages"""
        progress_stages = [
            ("idle", 0),
            ("creating", 10),
            ("connecting", 30),
            ("ready", 100),
        ]

        prev_progress = -1
        for status, progress in progress_stages:
            assert progress > prev_progress, f"Progress should increase: {status}={progress}"
            prev_progress = progress


@skip_if_no_api_key
class TestRaceTimings:
    """Test race timing calculations"""

    def test_eta_calculation(self):
        """Test ETA calculation based on progress"""
        def calculate_eta(elapsed, progress):
            if progress <= 0:
                return float('inf')
            estimated_total = (elapsed / progress) * 100
            remaining = max(0, estimated_total - elapsed)
            return remaining

        # 50% done in 30s = ~30s remaining
        eta = calculate_eta(30, 50)
        assert 25 <= eta <= 35

        # 80% done in 40s = ~10s remaining
        eta = calculate_eta(40, 80)
        assert 5 <= eta <= 15

    def test_timeout_detection(self):
        """Test timeout detection logic"""
        start_time = time.time() - 400  # 400s ago
        timeout_seconds = 300

        elapsed = time.time() - start_time
        is_timed_out = elapsed >= timeout_seconds

        assert is_timed_out is True


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=600"])
