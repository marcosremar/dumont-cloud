"""
API Routes para gerenciamento de regioes GPU

Fornece endpoints para listar regioes disponiveis, precos e disponibilidade.
Usa o RegionService para operacoes de regiao.

Inclui tambem endpoints para preferencias de regiao do usuario em /api/users/.
"""
from flask import Blueprint, jsonify, request, g, session
from src.services.region_service import RegionService
from src.models.user_region_preference import UserRegionPreference
from src.config.database import get_db_session

regions_bp = Blueprint('regions', __name__, url_prefix='/api/regions')

# Blueprint separado para preferencias de usuario (diferente prefixo de URL)
users_regions_bp = Blueprint('users_regions', __name__, url_prefix='/api/users')


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


# ========================================
# USER REGION PREFERENCES ENDPOINTS
# ========================================

def get_current_user_id():
    """Obtem o ID do usuario logado a partir da sessao."""
    return session.get('user')


@users_regions_bp.route('/region-preferences', methods=['GET'])
def get_user_region_preferences():
    """
    Retorna as preferencias de regiao do usuario logado.

    Retorna:
    {
        "user_id": "user@example.com",
        "preferred_region": "eu-de",
        "fallback_regions": ["eu-nl", "na-us-ca"],
        "data_residency_requirement": "EU_GDPR",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }

    Se o usuario nao tiver preferencias salvas, retorna defaults baseados
    na localizacao detectada.
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Nao autenticado'}), 401

    try:
        db = get_db_session()
        preference = db.query(UserRegionPreference).filter_by(user_id=user_id).first()

        if preference:
            return jsonify(preference.to_dict())

        # Usuario nao tem preferencias salvas - retornar defaults
        # Tentar sugerir regiao baseada na localizacao
        region_service = get_region_service()
        suggested_region = None
        suggested_fallbacks = []

        if region_service:
            try:
                # Obter IP do usuario para sugestao
                user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if user_ip and ',' in user_ip:
                    user_ip = user_ip.split(',')[0].strip()

                suggested = region_service.suggest_regions_for_user(
                    user_ip=user_ip,
                    require_eu=False,
                    max_price=10.0,
                )

                if suggested and len(suggested) > 0:
                    suggested_region = suggested[0].get('region_id')
                    if len(suggested) > 1:
                        suggested_fallbacks = [r.get('region_id') for r in suggested[1:4]]
            except Exception:
                pass  # Ignorar erros de sugestao

        return jsonify({
            'user_id': user_id,
            'preferred_region': suggested_region,
            'fallback_regions': suggested_fallbacks,
            'data_residency_requirement': None,
            'created_at': None,
            'updated_at': None,
            'is_default': True,  # Indica que sao valores sugeridos, nao salvos
        })

    except Exception as e:
        return jsonify({
            'error': 'Erro ao buscar preferencias',
            'details': str(e)
        }), 500


@users_regions_bp.route('/region-preferences', methods=['PUT'])
def update_user_region_preferences():
    """
    Atualiza as preferencias de regiao do usuario logado.

    Request Body:
    {
        "preferred_region": "eu-west",
        "fallback_regions": ["eu-central", "us-east"],  // opcional
        "data_residency_requirement": "EU_GDPR"  // opcional
    }

    Retorna:
    {
        "user_id": "user@example.com",
        "preferred_region": "eu-west",
        "fallback_regions": ["eu-central", "us-east"],
        "data_residency_requirement": "EU_GDPR",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Nao autenticado'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body obrigatorio'}), 400

    # Validar campo obrigatorio
    preferred_region = data.get('preferred_region')
    if not preferred_region:
        return jsonify({'error': 'Campo preferred_region e obrigatorio'}), 400

    # Validar preferred_region e uma string valida
    if not isinstance(preferred_region, str) or len(preferred_region) > 100:
        return jsonify({'error': 'Campo preferred_region deve ser uma string de ate 100 caracteres'}), 400

    # Campos opcionais
    fallback_regions = data.get('fallback_regions')
    data_residency_requirement = data.get('data_residency_requirement')

    # Validar fallback_regions se fornecido
    if fallback_regions is not None:
        if not isinstance(fallback_regions, list):
            return jsonify({'error': 'Campo fallback_regions deve ser uma lista'}), 400
        if not all(isinstance(r, str) for r in fallback_regions):
            return jsonify({'error': 'Todos os itens de fallback_regions devem ser strings'}), 400
        # Limitar a 5 regioes de fallback
        if len(fallback_regions) > 5:
            return jsonify({'error': 'Maximo de 5 regioes de fallback permitidas'}), 400

    # Validar data_residency_requirement se fornecido
    valid_residency_requirements = ['EU_GDPR', 'US_ONLY', 'APAC_ONLY', None]
    if data_residency_requirement is not None:
        if data_residency_requirement not in valid_residency_requirements:
            return jsonify({
                'error': f'Campo data_residency_requirement invalido. Valores permitidos: {valid_residency_requirements}'
            }), 400

    try:
        db = get_db_session()

        # Buscar preferencia existente ou criar nova
        preference = db.query(UserRegionPreference).filter_by(user_id=user_id).first()

        if preference:
            # Atualizar preferencia existente
            preference.preferred_region = preferred_region
            preference.fallback_regions = fallback_regions
            preference.data_residency_requirement = data_residency_requirement
        else:
            # Criar nova preferencia
            preference = UserRegionPreference(
                user_id=user_id,
                preferred_region=preferred_region,
                fallback_regions=fallback_regions,
                data_residency_requirement=data_residency_requirement,
            )
            db.add(preference)

        db.commit()
        db.refresh(preference)

        return jsonify(preference.to_dict())

    except Exception as e:
        db.rollback()
        return jsonify({
            'error': 'Erro ao atualizar preferencias',
            'details': str(e)
        }), 500
