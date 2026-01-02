"""
Unit Tests for Wizard Form Logic

Tests the extracted pure functions from useWizardForm hook.
These functions are easily testable without React or DOM.
"""
import pytest


# =============================================================================
# CONSTANTS (mirroring JavaScript exports)
# =============================================================================

WIZARD_STEPS = [
    {'id': 1, 'name': 'Região', 'description': 'Localização'},
    {'id': 2, 'name': 'Hardware', 'description': 'GPU e performance'},
    {'id': 3, 'name': 'Estratégia', 'description': 'Failover'},
    {'id': 4, 'name': 'Provisionar', 'description': 'Conectando'},
]

FAILOVER_STRATEGIES = {
    'SNAPSHOT_ONLY': 'snapshot_only',
    'VAST_WARMPOOL': 'vast_warmpool',
    'CPU_STANDBY': 'cpu_standby_only',
    'TENSORDOCK': 'tensordock',
    'NO_FAILOVER': 'no_failover',
}

DEFAULT_PORTS = [
    {'port': '22', 'protocol': 'TCP'},
    {'port': '8888', 'protocol': 'TCP'},
    {'port': '6006', 'protocol': 'TCP'},
]

MIN_BALANCE = 0.10


# =============================================================================
# PURE FUNCTIONS (Python equivalents for testing)
# =============================================================================

def format_time(seconds):
    """Format seconds as mm:ss"""
    if not isinstance(seconds, (int, float)) or seconds < 0:
        return '0:00'
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"


def calculate_eta(elapsed_time, max_progress, has_winner):
    """Calculate ETA based on elapsed time and progress"""
    if has_winner:
        return 'Concluído!'
    if max_progress <= 0:
        return 'Sem máquinas ativas'
    if max_progress <= 10 or elapsed_time < 3:
        return 'Estimando...'

    estimated_total = (elapsed_time / max_progress) * 100
    remaining = max(0, int(estimated_total - elapsed_time + 0.5))

    if remaining < 60:
        return f'~{remaining}s restantes'
    return f'~{int(remaining / 60 + 0.5)}min restantes'


def is_step_data_complete(step_id, data):
    """Check if step data is complete"""
    selected_location = data.get('selectedLocation')
    selected_tier = data.get('selectedTier')
    failover_strategy = data.get('failoverStrategy')
    provisioning_winner = data.get('provisioningWinner')

    if step_id == 1:
        return bool(selected_location)
    if step_id == 2:
        return bool(selected_tier)
    if step_id == 3:
        return bool(failover_strategy)
    if step_id == 4:
        return bool(provisioning_winner)
    return False


def can_proceed_to_step(target_step, current_step, step_data):
    """Check if user can proceed to a specific step"""
    if target_step < current_step:
        return True
    if target_step == current_step:
        return True
    if target_step == current_step + 1:
        return is_step_data_complete(current_step, step_data)
    return False


def validate_wizard_data(data, user_balance):
    """Validate wizard data before provisioning"""
    errors = []

    if not data.get('selectedLocation'):
        errors.append('Por favor, selecione uma localização para sua máquina')

    if not data.get('selectedTier'):
        errors.append('Por favor, selecione um tier de performance')

    if user_balance is not None and user_balance < MIN_BALANCE:
        errors.append(
            f'Saldo insuficiente. Você precisa de pelo menos ${MIN_BALANCE:.2f} para criar uma máquina. Saldo atual: ${user_balance:.2f}'
        )

    return errors


def get_estimated_cost(tier, tiers):
    """Get estimated cost based on tier"""
    if not tier or not tiers:
        return {'hourly': '0.00', 'daily': '0.00'}

    tier_data = next((t for t in tiers if t.get('name') == tier), None)
    if not tier_data:
        return {'hourly': '0.00', 'daily': '0.00'}

    price_range = tier_data.get('priceRange', '')
    import re
    match = re.search(r'\$(\d+\.?\d*)', price_range)
    min_price = float(match.group(1)) if match else 0.20

    return {
        'hourly': f'{min_price:.2f}',
        'daily': f'{min_price * 24:.2f}',
    }


def filter_gpus(gpus, query):
    """Filter GPUs by search query"""
    if not query or not query.strip():
        return gpus

    lower_query = query.lower()
    return [
        gpu for gpu in gpus
        if lower_query in gpu.get('name', '').lower() or
           lower_query in gpu.get('vram', '').lower()
    ]


def get_active_candidates(candidates):
    """Get active candidates (not failed)"""
    return [c for c in candidates if c.get('status') != 'failed']


def get_max_progress(candidates):
    """Get max progress from candidates"""
    active = get_active_candidates(candidates)
    if not active:
        return 0
    return max(c.get('progress', 0) for c in active)


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestFormatTime:
    """Test time formatting function"""

    def test_format_zero_seconds(self):
        assert format_time(0) == '0:00'

    def test_format_seconds_only(self):
        assert format_time(30) == '0:30'

    def test_format_one_minute(self):
        assert format_time(60) == '1:00'

    def test_format_minutes_and_seconds(self):
        assert format_time(90) == '1:30'

    def test_format_two_minutes_five_seconds(self):
        assert format_time(125) == '2:05'

    def test_format_negative_returns_zero(self):
        assert format_time(-5) == '0:00'

    def test_format_non_number_returns_zero(self):
        assert format_time("invalid") == '0:00'
        assert format_time(None) == '0:00'

    def test_format_large_value(self):
        assert format_time(3600) == '60:00'  # 1 hour


class TestCalculateETA:
    """Test ETA calculation function"""

    def test_eta_with_winner(self):
        assert calculate_eta(30, 50, True) == 'Concluído!'

    def test_eta_no_machines(self):
        assert calculate_eta(30, 0, False) == 'Sem máquinas ativas'

    def test_eta_estimating_low_progress(self):
        assert calculate_eta(30, 5, False) == 'Estimando...'

    def test_eta_estimating_early(self):
        assert calculate_eta(2, 50, False) == 'Estimando...'

    def test_eta_seconds_remaining(self):
        result = calculate_eta(30, 50, False)
        assert 's restantes' in result

    def test_eta_minutes_remaining(self):
        result = calculate_eta(60, 30, False)
        assert 'min restantes' in result


class TestIsStepDataComplete:
    """Test step completion check"""

    def test_step1_complete_with_location(self):
        data = {'selectedLocation': 'US-West'}
        assert is_step_data_complete(1, data) is True

    def test_step1_incomplete_without_location(self):
        data = {}
        assert is_step_data_complete(1, data) is False

    def test_step2_complete_with_tier(self):
        data = {'selectedTier': 'Medio'}
        assert is_step_data_complete(2, data) is True

    def test_step2_incomplete_without_tier(self):
        data = {'selectedLocation': 'US-West'}
        assert is_step_data_complete(2, data) is False

    def test_step3_complete_with_strategy(self):
        data = {'failoverStrategy': 'cpu_standby'}
        assert is_step_data_complete(3, data) is True

    def test_step4_complete_with_winner(self):
        data = {'provisioningWinner': {'id': 'inst-123'}}
        assert is_step_data_complete(4, data) is True

    def test_invalid_step_returns_false(self):
        data = {'selectedLocation': 'US-West'}
        assert is_step_data_complete(99, data) is False


class TestCanProceedToStep:
    """Test step navigation logic"""

    def test_can_go_back(self):
        data = {}
        assert can_proceed_to_step(1, 3, data) is True

    def test_can_stay_current(self):
        data = {}
        assert can_proceed_to_step(2, 2, data) is True

    def test_can_proceed_when_complete(self):
        data = {'selectedLocation': 'US-West'}
        assert can_proceed_to_step(2, 1, data) is True

    def test_cannot_proceed_when_incomplete(self):
        data = {}
        assert can_proceed_to_step(2, 1, data) is False

    def test_cannot_skip_steps(self):
        data = {'selectedLocation': 'US-West'}
        assert can_proceed_to_step(3, 1, data) is False


class TestValidateWizardData:
    """Test wizard data validation"""

    def test_valid_data_no_errors(self):
        data = {
            'selectedLocation': 'US-West',
            'selectedTier': 'Medio',
        }
        errors = validate_wizard_data(data, 1.00)
        assert len(errors) == 0

    def test_missing_location_error(self):
        data = {'selectedTier': 'Medio'}
        errors = validate_wizard_data(data, 1.00)
        assert any('localização' in e for e in errors)

    def test_missing_tier_error(self):
        data = {'selectedLocation': 'US-West'}
        errors = validate_wizard_data(data, 1.00)
        assert any('tier' in e for e in errors)

    def test_insufficient_balance_error(self):
        data = {
            'selectedLocation': 'US-West',
            'selectedTier': 'Medio',
        }
        errors = validate_wizard_data(data, 0.05)
        assert any('Saldo insuficiente' in e for e in errors)

    def test_null_balance_no_balance_error(self):
        data = {
            'selectedLocation': 'US-West',
            'selectedTier': 'Medio',
        }
        errors = validate_wizard_data(data, None)
        assert len(errors) == 0

    def test_multiple_errors(self):
        data = {}
        errors = validate_wizard_data(data, 0.01)
        assert len(errors) == 3  # location, tier, balance


class TestGetEstimatedCost:
    """Test cost estimation"""

    def test_no_tier_returns_zero(self):
        result = get_estimated_cost(None, [])
        assert result == {'hourly': '0.00', 'daily': '0.00'}

    def test_tier_not_found_returns_zero(self):
        tiers = [{'name': 'Rapido', 'priceRange': '$0.50/h'}]
        result = get_estimated_cost('Lento', tiers)
        assert result == {'hourly': '0.00', 'daily': '0.00'}

    def test_valid_tier_returns_cost(self):
        tiers = [{'name': 'Medio', 'priceRange': '$0.35/h'}]
        result = get_estimated_cost('Medio', tiers)
        assert result['hourly'] == '0.35'
        assert result['daily'] == '8.40'

    def test_tier_without_price_range(self):
        tiers = [{'name': 'Medio'}]
        result = get_estimated_cost('Medio', tiers)
        assert result['hourly'] == '0.20'  # Default


class TestFilterGPUs:
    """Test GPU filtering"""

    def test_empty_query_returns_all(self):
        gpus = [
            {'name': 'RTX 4090', 'vram': '24GB'},
            {'name': 'RTX 3080', 'vram': '10GB'},
        ]
        result = filter_gpus(gpus, '')
        assert len(result) == 2

    def test_filter_by_name(self):
        gpus = [
            {'name': 'RTX 4090', 'vram': '24GB'},
            {'name': 'RTX 3080', 'vram': '10GB'},
            {'name': 'A100', 'vram': '80GB'},
        ]
        result = filter_gpus(gpus, '4090')
        assert len(result) == 1
        assert result[0]['name'] == 'RTX 4090'

    def test_filter_by_vram(self):
        gpus = [
            {'name': 'RTX 4090', 'vram': '24GB'},
            {'name': 'A100', 'vram': '80GB'},
        ]
        result = filter_gpus(gpus, '80GB')
        assert len(result) == 1
        assert result[0]['name'] == 'A100'

    def test_filter_case_insensitive(self):
        gpus = [{'name': 'RTX 4090', 'vram': '24GB'}]
        result = filter_gpus(gpus, 'rtx')
        assert len(result) == 1

    def test_filter_no_matches(self):
        gpus = [{'name': 'RTX 4090', 'vram': '24GB'}]
        result = filter_gpus(gpus, 'H100')
        assert len(result) == 0


class TestGetActiveCandidates:
    """Test active candidate filtering"""

    def test_all_active(self):
        candidates = [
            {'id': '1', 'status': 'connecting'},
            {'id': '2', 'status': 'running'},
        ]
        result = get_active_candidates(candidates)
        assert len(result) == 2

    def test_filter_failed(self):
        candidates = [
            {'id': '1', 'status': 'connecting'},
            {'id': '2', 'status': 'failed'},
            {'id': '3', 'status': 'running'},
        ]
        result = get_active_candidates(candidates)
        assert len(result) == 2
        assert all(c['status'] != 'failed' for c in result)

    def test_all_failed(self):
        candidates = [
            {'id': '1', 'status': 'failed'},
            {'id': '2', 'status': 'failed'},
        ]
        result = get_active_candidates(candidates)
        assert len(result) == 0


class TestGetMaxProgress:
    """Test max progress calculation"""

    def test_max_progress_single(self):
        candidates = [{'status': 'running', 'progress': 50}]
        assert get_max_progress(candidates) == 50

    def test_max_progress_multiple(self):
        candidates = [
            {'status': 'connecting', 'progress': 30},
            {'status': 'running', 'progress': 80},
            {'status': 'connecting', 'progress': 45},
        ]
        assert get_max_progress(candidates) == 80

    def test_max_progress_ignores_failed(self):
        candidates = [
            {'status': 'failed', 'progress': 90},
            {'status': 'running', 'progress': 50},
        ]
        assert get_max_progress(candidates) == 50

    def test_max_progress_empty(self):
        assert get_max_progress([]) == 0

    def test_max_progress_all_failed(self):
        candidates = [
            {'status': 'failed', 'progress': 90},
            {'status': 'failed', 'progress': 80},
        ]
        assert get_max_progress(candidates) == 0


class TestWizardSteps:
    """Test wizard step configuration"""

    def test_has_four_steps(self):
        assert len(WIZARD_STEPS) == 4

    def test_steps_have_required_fields(self):
        for step in WIZARD_STEPS:
            assert 'id' in step
            assert 'name' in step
            assert 'description' in step

    def test_step_ids_sequential(self):
        ids = [s['id'] for s in WIZARD_STEPS]
        assert ids == [1, 2, 3, 4]


class TestFailoverStrategies:
    """Test failover strategy configuration"""

    def test_has_five_strategies(self):
        assert len(FAILOVER_STRATEGIES) == 5

    def test_strategy_values_unique(self):
        values = list(FAILOVER_STRATEGIES.values())
        assert len(values) == len(set(values))

    def test_expected_strategies_exist(self):
        assert 'SNAPSHOT_ONLY' in FAILOVER_STRATEGIES
        assert 'CPU_STANDBY' in FAILOVER_STRATEGIES
        assert 'NO_FAILOVER' in FAILOVER_STRATEGIES


class TestDefaultPorts:
    """Test default port configuration"""

    def test_has_default_ports(self):
        assert len(DEFAULT_PORTS) == 3

    def test_ssh_port_included(self):
        ports = [p['port'] for p in DEFAULT_PORTS]
        assert '22' in ports

    def test_jupyter_port_included(self):
        ports = [p['port'] for p in DEFAULT_PORTS]
        assert '8888' in ports

    def test_tensorboard_port_included(self):
        ports = [p['port'] for p in DEFAULT_PORTS]
        assert '6006' in ports

    def test_all_ports_tcp(self):
        assert all(p['protocol'] == 'TCP' for p in DEFAULT_PORTS)


class TestMinBalance:
    """Test minimum balance constant"""

    def test_min_balance_value(self):
        assert MIN_BALANCE == 0.10

    def test_min_balance_is_float(self):
        assert isinstance(MIN_BALANCE, float)


# =============================================================================
# RUN ALL TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
