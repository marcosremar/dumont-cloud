"""
API Routes para Template Marketplace (Flask Blueprint)

Expoe o TemplateService como API REST para o frontend.
Permite listar templates, buscar por slug, e fazer deploy.
"""
from flask import Blueprint, jsonify, request, g
from services.template_service import TemplateService

templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')


def get_template_service():
    """Factory para criar TemplateService"""
    return TemplateService()


@templates_bp.route('', methods=['GET'])
def list_templates():
    """
    Lista todos os templates disponiveis.

    Query params:
        min_vram: int - Filtrar templates que requerem <= este VRAM (GB)
        category: str - Filtrar por categoria (notebook, image_generation, llm_inference, training)
        verified_only: bool - Apenas templates verificados

    Returns:
        JSON com lista de templates e contagem
    """
    try:
        service = get_template_service()

        # Obter parametros de filtro
        min_vram = request.args.get('min_vram', type=int)
        category = request.args.get('category')
        verified_only = request.args.get('verified_only', 'false').lower() == 'true'

        # Buscar templates
        if verified_only:
            templates = service.get_verified_templates()
        elif min_vram is not None:
            templates = service.filter_by_vram(min_vram)
        else:
            templates = service.get_all_templates()

        # Aplicar filtro de categoria se especificado
        if category:
            from src.modules.marketplace.models import TemplateCategory
            try:
                category_enum = TemplateCategory(category)
                templates = [t for t in templates if t.category == category_enum]
            except ValueError:
                return jsonify({
                    'error': f"Categoria invalida: {category}. Valores validos: notebook, image_generation, llm_inference, training"
                }), 400

        # Converter para formato de resposta
        template_list = []
        for t in templates:
            template_list.append({
                'id': t.id,
                'name': t.name,
                'slug': t.slug,
                'description': t.description,
                'docker_image': t.docker_image,
                'gpu_min_vram': t.gpu_min_vram,
                'gpu_recommended_vram': t.gpu_recommended_vram,
                'cuda_version': t.cuda_version,
                'ports': t.ports,
                'volumes': t.volumes,
                'launch_command': t.launch_command,
                'env_vars': t.env_vars,
                'category': t.category.value if hasattr(t.category, 'value') else str(t.category),
                'icon_url': t.icon_url,
                'documentation_url': t.documentation_url,
                'is_active': t.is_active,
                'is_verified': t.is_verified,
            })

        return jsonify({
            'templates': template_list,
            'count': len(template_list)
        })

    except Exception as e:
        return jsonify({'error': f'Falha ao listar templates: {str(e)}'}), 500


@templates_bp.route('/<slug>', methods=['GET'])
def get_template(slug: str):
    """
    Busca template por slug.

    Path params:
        slug: str - Slug do template (ex: jupyter-lab, stable-diffusion, comfy-ui, vllm)

    Returns:
        JSON com detalhes do template
    """
    try:
        service = get_template_service()
        template = service.get_template_by_slug(slug)

        if not template:
            return jsonify({'error': f"Template '{slug}' nao encontrado"}), 404

        return jsonify({
            'id': template.id,
            'name': template.name,
            'slug': template.slug,
            'description': template.description,
            'docker_image': template.docker_image,
            'gpu_min_vram': template.gpu_min_vram,
            'gpu_recommended_vram': template.gpu_recommended_vram,
            'cuda_version': template.cuda_version,
            'ports': template.ports,
            'volumes': template.volumes,
            'launch_command': template.launch_command,
            'env_vars': template.env_vars,
            'category': template.category.value if hasattr(template.category, 'value') else str(template.category),
            'icon_url': template.icon_url,
            'documentation_url': template.documentation_url,
            'is_active': template.is_active,
            'is_verified': template.is_verified,
        })

    except Exception as e:
        return jsonify({'error': f'Falha ao buscar template: {str(e)}'}), 500


@templates_bp.route('/<slug>/gpu-requirements', methods=['GET'])
def get_template_gpu_requirements(slug: str):
    """
    Retorna requisitos de GPU para um template.

    Path params:
        slug: str - Slug do template

    Returns:
        JSON com requisitos de GPU (min_vram, recommended_vram, cuda_version)
    """
    try:
        service = get_template_service()
        template = service.get_template_by_slug(slug)

        if not template:
            return jsonify({'error': f"Template '{slug}' nao encontrado"}), 404

        return jsonify({
            'min_vram': template.gpu_min_vram,
            'recommended_vram': template.gpu_recommended_vram,
            'cuda_version': template.cuda_version,
        })

    except Exception as e:
        return jsonify({'error': f'Falha ao buscar requisitos de GPU: {str(e)}'}), 500


@templates_bp.route('/<slug>/deploy', methods=['POST'])
def deploy_template(slug: str):
    """
    Faz deploy de um template em uma instancia GPU.

    Path params:
        slug: str - Slug do template

    Body (JSON):
        offer_id: int - ID da oferta GPU do vast.ai (obrigatorio)
        disk_size: int - Tamanho do disco em GB (default: 50)
        label: str - Label opcional para a instancia
        env_overrides: dict - Variaveis de ambiente para sobrescrever
        skip_validation: bool - Pular validacao de GPU (nao recomendado)

    Returns:
        JSON com status do deploy e detalhes da instancia
    """
    import random
    import os
    from services.vast_service import VastService

    try:
        service = get_template_service()
        template = service.get_template_by_slug(slug)

        if not template:
            return jsonify({'error': f"Template '{slug}' nao encontrado"}), 404

        data = request.get_json() or {}
        offer_id = data.get('offer_id')
        disk_size = data.get('disk_size', 50)
        label = data.get('label')
        env_overrides = data.get('env_overrides')
        skip_validation = data.get('skip_validation', False)

        # Verificar modo demo
        is_demo = os.getenv('DEMO_MODE', 'false').lower() == 'true' or request.args.get('demo') == 'true'

        if is_demo:
            # Modo demo: retornar deploy simulado
            demo_instance_id = random.randint(10000000, 99999999)
            return jsonify({
                'success': True,
                'instance_id': demo_instance_id,
                'template_slug': slug,
                'template_name': template.name,
                'gpu_validation': {
                    'is_compatible': True,
                    'is_recommended': True,
                    'gpu_vram': 24,
                    'required_vram': template.gpu_min_vram,
                    'recommended_vram': template.gpu_recommended_vram,
                    'messages': ['Demo mode: GPU validation simulada']
                },
                'message': f"Demo: Template '{template.name}' deployed com sucesso",
                'connection_info': {
                    'ssh_host': 'demo.dumontcloud.com',
                    'ssh_port': 22,
                    'public_ip': 'demo.dumontcloud.com',
                    'ports': {str(p): p for p in template.ports},
                }
            }), 201

        # Validar offer_id
        if not offer_id:
            return jsonify({'error': 'offer_id e obrigatorio'}), 400

        # Obter API key do usuario
        api_key = getattr(g, 'vast_api_key', '')
        if not api_key:
            return jsonify({'error': 'API key nao configurada. Atualize as configuracoes.'}), 400

        vast_service = VastService(api_key)

        # Buscar oferta selecionada
        offers = vast_service.search_offers(max_price=10.0, limit=200)
        selected_offer = None
        for offer in offers:
            if offer.get('id') == offer_id:
                selected_offer = offer
                break

        if not selected_offer:
            return jsonify({'error': f'Oferta GPU {offer_id} nao encontrada ou nao disponivel'}), 400

        # Validar GPU para o template
        gpu_validation = vast_service.validate_gpu_for_template(selected_offer, template)

        if not gpu_validation['is_compatible'] and not skip_validation:
            return jsonify({
                'error': f"GPU nao atende requisitos do template: {'; '.join(gpu_validation['messages'])}"
            }), 400

        # Criar instancia a partir do template
        instance_id = vast_service.create_instance_from_template(
            offer_id=offer_id,
            template=template,
            disk=disk_size,
            env_overrides=env_overrides,
        )

        if not instance_id:
            return jsonify({'error': 'Falha ao criar instancia. Tente novamente.'}), 500

        return jsonify({
            'success': True,
            'instance_id': instance_id,
            'template_slug': slug,
            'template_name': template.name,
            'gpu_validation': gpu_validation,
            'message': f"Template '{template.name}' deploy iniciado. Instancia {instance_id} sendo provisionada.",
            'connection_info': {
                'status': 'provisioning',
                'expected_ports': template.ports,
                'note': 'Detalhes de conexao disponiveis quando a instancia estiver rodando. Consulte GET /api/instances/{instance_id} para status.'
            }
        }), 201

    except Exception as e:
        return jsonify({'error': f'Falha ao fazer deploy do template: {str(e)}'}), 500


@templates_bp.route('/<slug>/offers', methods=['GET'])
def get_compatible_offers(slug: str):
    """
    Lista ofertas GPU compativeis com um template.

    Path params:
        slug: str - Slug do template

    Query params:
        max_price: float - Preco maximo por hora em USD (default: 2.0)
        region: str - Filtro de regiao (US, EU, ASIA)
        num_gpus: int - Numero de GPUs (default: 1)
        verified_only: bool - Apenas hosts verificados
        limit: int - Maximo de resultados (default: 20)

    Returns:
        JSON com lista de ofertas compativeis
    """
    import os
    from services.vast_service import VastService

    try:
        service = get_template_service()
        template = service.get_template_by_slug(slug)

        if not template:
            return jsonify({'error': f"Template '{slug}' nao encontrado"}), 404

        # Verificar modo demo
        is_demo = os.getenv('DEMO_MODE', 'false').lower() == 'true' or request.args.get('demo') == 'true'

        if is_demo:
            # Modo demo: retornar ofertas simuladas
            return jsonify({
                'template_slug': template.slug,
                'template_name': template.name,
                'min_vram': template.gpu_min_vram,
                'offers': [
                    {
                        'id': 12345,
                        'gpu_name': 'RTX 4090',
                        'gpu_ram': 24,
                        'num_gpus': 1,
                        'dph_total': 0.50,
                        'verified': True,
                        'geolocation': 'US',
                    },
                    {
                        'id': 12346,
                        'gpu_name': 'RTX 3090',
                        'gpu_ram': 24,
                        'num_gpus': 1,
                        'dph_total': 0.35,
                        'verified': True,
                        'geolocation': 'EU',
                    },
                ],
                'count': 2
            })

        # Obter API key do usuario
        api_key = getattr(g, 'vast_api_key', '')
        if not api_key:
            return jsonify({'error': 'API key nao configurada. Atualize as configuracoes.'}), 400

        # Obter parametros
        max_price = request.args.get('max_price', 2.0, type=float)
        region = request.args.get('region')
        num_gpus = request.args.get('num_gpus', 1, type=int)
        verified_only = request.args.get('verified_only', 'false').lower() == 'true'
        limit = request.args.get('limit', 20, type=int)

        vast_service = VastService(api_key)

        offers = vast_service.search_offers_for_template(
            template=template,
            num_gpus=num_gpus,
            max_price=max_price,
            region=region,
            verified_only=verified_only,
            limit=limit,
        )

        return jsonify({
            'template_slug': template.slug,
            'template_name': template.name,
            'min_vram': template.gpu_min_vram,
            'offers': offers,
            'count': len(offers),
        })

    except Exception as e:
        return jsonify({'error': f'Falha ao buscar ofertas compativeis: {str(e)}'}), 500
