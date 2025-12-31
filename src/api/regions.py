"""
API Routes para gerenciamento de regioes GPU

Fornece endpoints para listar regioes disponiveis, precos e disponibilidade.
Usa o RegionService para operacoes de regiao.
"""
from flask import Blueprint, jsonify, request, g
from src.services.region_service import RegionService

regions_bp = Blueprint('regions', __name__, url_prefix='/api/regions')


def get_region_service() -> RegionService:
    """Factory para criar RegionService com API key do usuario"""
    api_key = getattr(g, 'vast_api_key', '')
    if not api_key:
        return None
    return RegionService(api_key)


@regions_bp.route('/available', methods=['GET'])
def get_available_regions():
    """
    Lista regioes disponiveis com ofertas GPU.

    Query params:
    - gpu_name: Filtrar por GPU (ex: "RTX 4090")
    - max_price: Preco maximo por hora (default: 10.0)
    - min_reliability: Score minimo de confiabilidade (0.0-1.0)
    - eu_only: Se "true", retorna apenas regioes EU/GDPR

    Retorna:
    {
        "regions": [
            {
                "region_id": "eu-de",
                "country_code": "DE",
                "country_name": "Germany",
                "continent_code": "EU",
                "continent_name": "Europe",
                "is_eu": true,
                "compliance_tags": ["GDPR"],
                "offer_count": 15,
                "min_price": 0.35,
                "max_price": 1.20,
                "avg_price": 0.65,
                "gpu_types": ["RTX 4090", "RTX 4080"],
                "fetched_at": "2025-01-01T12:00:00"
            },
            ...
        ],
        "total": 12,
        "filters": {
            "gpu_name": null,
            "max_price": 10.0,
            "eu_only": false
        }
    }
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    # Parse query parameters
    gpu_name = request.args.get('gpu_name')
    max_price = float(request.args.get('max_price', 10.0))
    min_reliability = float(request.args.get('min_reliability', 0.0))
    eu_only = request.args.get('eu_only', 'false').lower() == 'true'

    try:
        regions = region_service.get_available_regions(
            gpu_name=gpu_name,
            max_price=max_price,
            min_reliability=min_reliability,
            eu_only=eu_only,
        )

        return jsonify({
            'regions': regions,
            'total': len(regions),
            'filters': {
                'gpu_name': gpu_name,
                'max_price': max_price,
                'min_reliability': min_reliability,
                'eu_only': eu_only,
            }
        })

    except Exception as e:
        return jsonify({
            'error': 'Erro ao buscar regioes',
            'details': str(e)
        }), 500


@regions_bp.route('/<region_id>/pricing', methods=['GET'])
def get_region_pricing(region_id: str):
    """
    Retorna informacoes de preco para uma regiao especifica.

    Path params:
    - region_id: ID da regiao (ex: "eu-de", "na-us-ca")

    Query params:
    - gpu_name: Filtrar por GPU (opcional)

    Retorna:
    {
        "region_id": "eu-de",
        "available": true,
        "currency": "USD",
        "offer_count": 15,
        "compute_price": {
            "min": 0.35,
            "max": 1.20,
            "avg": 0.65
        },
        "by_gpu": [
            {"gpu_name": "RTX 4090", "min": 0.35, "avg": 0.45, "count": 10},
            {"gpu_name": "RTX 4080", "min": 0.25, "avg": 0.35, "count": 5}
        ],
        "fetched_at": "2025-01-01T12:00:00"
    }
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    gpu_name = request.args.get('gpu_name')

    try:
        pricing = region_service.get_region_pricing(
            region_id=region_id,
            gpu_name=gpu_name,
        )

        return jsonify(pricing)

    except Exception as e:
        return jsonify({
            'error': f'Erro ao buscar pricing para regiao {region_id}',
            'details': str(e)
        }), 500


@regions_bp.route('/<region_id>/availability', methods=['GET'])
def check_region_availability(region_id: str):
    """
    Verifica disponibilidade de GPU em uma regiao especifica.

    Path params:
    - region_id: ID da regiao (ex: "eu-de", "na-us-ca")

    Query params:
    - gpu_name: Nome da GPU a verificar (opcional)
    - num_gpus: Numero de GPUs necessarias (default: 1)
    - max_price: Preco maximo por hora (default: 10.0)

    Retorna:
    {
        "region_id": "eu-de",
        "available": true,
        "offer_count": 5,
        "cheapest_price": 0.35,
        "gpu_name": "RTX 4090",
        "checked_at": "2025-01-01T12:00:00"
    }
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    gpu_name = request.args.get('gpu_name')
    num_gpus = int(request.args.get('num_gpus', 1))
    max_price = float(request.args.get('max_price', 10.0))

    try:
        availability = region_service.check_region_availability(
            region_id=region_id,
            gpu_name=gpu_name,
            num_gpus=num_gpus,
            max_price=max_price,
        )

        return jsonify(availability)

    except Exception as e:
        return jsonify({
            'error': f'Erro ao verificar disponibilidade para regiao {region_id}',
            'details': str(e)
        }), 500


@regions_bp.route('/suggest', methods=['GET'])
def suggest_regions():
    """
    Sugere regioes baseado na localizacao do usuario.

    Query params:
    - require_eu: Se "true", sugere apenas regioes EU/GDPR
    - gpu_name: Filtrar por GPU (opcional)
    - max_price: Preco maximo por hora (default: 10.0)

    Retorna:
    {
        "suggested_regions": [
            {
                "region_id": "eu-de",
                "suggested": true,
                "suggestion_rank": 1,
                ...
            },
            ...
        ],
        "user_location": {
            "detected": true,
            "country": "Germany",
            "city": "Berlin"
        }
    }
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    require_eu = request.args.get('require_eu', 'false').lower() == 'true'
    gpu_name = request.args.get('gpu_name')
    max_price = float(request.args.get('max_price', 10.0))

    # Obter IP do usuario
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip and ',' in user_ip:
        user_ip = user_ip.split(',')[0].strip()

    try:
        suggested = region_service.suggest_regions_for_user(
            user_ip=user_ip,
            require_eu=require_eu,
            gpu_name=gpu_name,
            max_price=max_price,
        )

        return jsonify({
            'suggested_regions': suggested,
            'user_location': {
                'detected': user_ip is not None,
                'ip': user_ip,
            }
        })

    except Exception as e:
        return jsonify({
            'error': 'Erro ao sugerir regioes',
            'details': str(e)
        }), 500


@regions_bp.route('/eu', methods=['GET'])
def get_eu_regions():
    """
    Lista regioes EU/GDPR-compliant.

    Convenience endpoint para compliance GDPR.

    Query params:
    - gpu_name: Filtrar por GPU (opcional)
    - max_price: Preco maximo por hora (default: 10.0)

    Retorna:
    {
        "regions": [...],
        "total": 5,
        "gdpr_compliant": true
    }
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    gpu_name = request.args.get('gpu_name')
    max_price = float(request.args.get('max_price', 10.0))

    try:
        regions = region_service.get_eu_regions(
            gpu_name=gpu_name,
            max_price=max_price,
        )

        return jsonify({
            'regions': regions,
            'total': len(regions),
            'gdpr_compliant': True,
        })

    except Exception as e:
        return jsonify({
            'error': 'Erro ao buscar regioes EU',
            'details': str(e)
        }), 500


@regions_bp.route('/<region_id>/compliance', methods=['GET'])
def get_region_compliance(region_id: str):
    """
    Retorna informacoes de compliance para uma regiao.

    Path params:
    - region_id: ID da regiao (ex: "eu-de", "na-us-ca")

    Retorna:
    {
        "region_id": "eu-de",
        "is_eu": true,
        "is_gdpr_compliant": true,
        "compliance_tags": ["GDPR", "EU-DC"],
        "data_residency": "EU"
    }
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    try:
        compliance = region_service.get_compliance_info(region_id)
        return jsonify(compliance)

    except Exception as e:
        return jsonify({
            'error': f'Erro ao buscar compliance para regiao {region_id}',
            'details': str(e)
        }), 500


@regions_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """
    Retorna estatisticas do cache de regioes.

    Util para monitoramento e debugging.
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    try:
        stats = region_service.get_cache_stats()
        return jsonify(stats)

    except Exception as e:
        return jsonify({
            'error': 'Erro ao buscar estatisticas de cache',
            'details': str(e)
        }), 500


@regions_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """
    Limpa o cache de regioes.

    Util para forcar atualizacao dos dados.
    """
    region_service = get_region_service()
    if not region_service:
        return jsonify({'error': 'API key nao configurada'}), 400

    try:
        count = region_service.clear_cache()
        return jsonify({
            'success': True,
            'cleared_entries': count,
        })

    except Exception as e:
        return jsonify({
            'error': 'Erro ao limpar cache',
            'details': str(e)
        }), 500
