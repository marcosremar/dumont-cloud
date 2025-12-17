# Como Pausar e Resumir Instâncias

## Funcionalidades Adicionadas

Foram adicionados métodos para **pausar** e **resumir** instâncias no Vast.ai, permitindo economizar custos sem perder dados.

### VastService (src/services/vast_service.py)

**Novos métodos:**

```python
def pause_instance(self, instance_id: int) -> bool:
    """Pausa uma instância (stop sem destruir)"""
    
def resume_instance(self, instance_id: int) -> bool:
    """Resume uma instância pausada"""
```

### API Endpoints (src/api/instances.py)

**Novos endpoints:**

- `POST /api/instances/<id>/pause` - Pausa uma instância
- `POST /api/instances/<id>/resume` - Resume uma instância pausada

## Exemplo de Uso via Python

```python
import requests

session = requests.Session()

# Login
session.post('http://localhost:8766/api/auth/login', json={
    'username': 'seu_email@gmail.com',
    'password': 'sua_senha'
})

# Pausar instância
instance_id = 28917659
response = session.post(f'http://localhost:8766/api/instances/{instance_id}/pause')
print(response.json())
# Output: {'success': True, 'message': 'Instancia 28917659 pausada'}

# Resumir instância
response = session.post(f'http://localhost:8766/api/instances/{instance_id}/resume')
print(response.json())
# Output: {'success': True, 'message': 'Instancia 28917659 resumida'}
```

## Exemplo de Uso via VastService

```python
from src.services import VastService

vast = VastService(api_key='sua_api_key')

# Pausar
success = vast.pause_instance(28917659)
print(f"Pausada: {success}")

# Resumir
success = vast.resume_instance(28917659)
print(f"Resumida: {success}")
```

## Diferença entre Pausar e Destruir

| Ação | Descrição | Custo | Dados |
|------|-----------|-------|-------|
| **Pause** | Para a instância mas mantém alocada | Continua cobrando (reduzido) | Dados preservados |
| **Destroy** | Remove completamente a instância | Não cobra mais | Dados perdidos (exceto snapshot) |

**Recomendação:** Use `pause` para pausas curtas (horas/dias) e `destroy` + snapshot para pausas longas.
