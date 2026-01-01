# Specification: Basic Template Marketplace

## Overview

Build a template marketplace feature that provides one-click deployment of pre-configured ML workloads (JupyterLab, Stable Diffusion WebUI, ComfyUI, vLLM) with all GPU dependencies configured. This eliminates the manual CUDA/driver setup pain on Vast.ai, reducing time-to-first-value from hours to minutes for AI artists and ML developers.

## Workflow Type

**Type**: feature

**Rationale**: This is a new feature addition to the Dumont Cloud platform. We're building net-new functionality (template marketplace UI, template deployment API, template metadata storage) that extends the existing instance provisioning capabilities with pre-configured templates.

## Task Scope

### Services Involved
- **cli** (primary) - Python backend service that will handle template metadata storage, Vast.ai integration for template-based deployments, and REST API endpoints for template CRUD operations
- **web** (primary) - React frontend that will display the template marketplace UI, template detail pages, and one-click deployment interface
- **sdk-client** (integration) - Python SDK may need updates to support programmatic template deployment

### This Task Will:
- [ ] Create template metadata schema and storage (4 templates: JupyterLab, Stable Diffusion, ComfyUI, vLLM)
- [ ] Build REST API endpoints for template listing, details, and deployment
- [ ] Implement template marketplace UI in dashboard with filtering and GPU recommendations
- [ ] Add one-click deployment flow that provisions Vast.ai instances with template configurations
- [ ] Create per-template documentation and getting-started guides
- [ ] Optimize boot time to meet <2 minute performance target

### Out of Scope:
- Custom template creation by users (only official templates in this phase)
- Template versioning and updates (v1 uses fixed versions)
- Template usage analytics/metrics
- Multi-cloud provider support (Vast.ai only)
- Template marketplace search/recommendations (basic filtering only)

## Service Context

### cli (Backend Service)

**Tech Stack:**
- Language: Python
- Framework: FastAPI (inferred from tests/test-server.py)
- Database: PostgreSQL (dumont_cloud database)
- Cache: Redis (localhost:6379)
- Key directories: utils/, tests/

**Entry Point:** `__main__.py`

**How to Run:**
```bash
cd cli
pip install -r requirements.txt
python __main__.py
```

**Port:** 8000 (APP_PORT from environment)

**Integrations:**
- Vast.ai API (VAST_API_KEY required)
- PostgreSQL database (for template metadata persistence)
- Redis (for caching template data)

### web (Frontend Service)

**Tech Stack:**
- Language: JavaScript
- Framework: React 18 with Vite
- State Management: Redux Toolkit
- Styling: Tailwind CSS + Radix UI components
- Key directories: src/

**Entry Point:** `src/App.jsx`

**How to Run:**
```bash
cd web
npm install
npm run dev
```

**Port:** 8000 (default_port)

**Integrations:**
- Consumes CLI REST API endpoints
- Existing dashboard patterns (Radix UI components, Redux state)

### tests (E2E Testing Service)

**Tech Stack:**
- Framework: Playwright
- Language: JavaScript

**Purpose:** E2E validation of template deployment flow

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| `cli/models/template.py` | cli | **Create new file** - Define Template SQLAlchemy model with fields: id, name, slug, description, gpu_requirements, docker_image, ports, volumes, launch_command, documentation_url |
| `cli/routes/templates.py` | cli | **Create new file** - Add REST endpoints: GET /api/templates (list), GET /api/templates/:slug (details), POST /api/templates/:slug/deploy (trigger deployment) |
| `cli/services/template_service.py` | cli | **Create new file** - Business logic for template CRUD, integration with Vast.ai API for deployment |
| `cli/services/vast_service.py` | cli | **Modify if exists, or create** - Add template-aware instance provisioning logic (Docker image selection, volume mounts, GPU filtering) |
| `cli/migrations/` | cli | **Create new migration** - Add templates table schema with GPU metadata fields |
| `web/src/pages/TemplatePage.jsx` | web | **Create new file** - Template marketplace UI with grid/list view, filters, GPU recommendations |
| `web/src/pages/TemplateDetailPage.jsx` | web | **Create new file** - Individual template details with specs, getting-started guide, one-click deploy button |
| `web/src/components/TemplateCard.jsx` | web | **Create new file** - Reusable template card component showing name, icon, GPU requirements, quick stats |
| `web/src/store/slices/templateSlice.js` | web | **Create new file** - Redux slice for template state management (list, selected, deployment status) |
| `web/src/App.jsx` | web | **Modify** - Add routes for /templates and /templates/:slug |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `cli/models/` (existing models) | SQLAlchemy model structure, relationships, timestamps |
| `cli/routes/` (existing routes) | FastAPI route decorators, error handling, request/response schemas |
| `web/src/pages/` (existing pages) | React page component structure, hooks usage, Redux integration |
| `web/src/components/` (existing components) | Radix UI component patterns, Tailwind styling conventions |
| `web/src/store/slices/` (existing slices) | Redux Toolkit slice patterns, async thunks, selectors |

## Patterns to Follow

### Backend: FastAPI Route Pattern

From existing CLI service patterns:

```python
# cli/routes/templates.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..services.template_service import TemplateService
from ..schemas.template import TemplateResponse, DeploymentRequest

router = APIRouter(prefix="/api/templates", tags=["templates"])

@router.get("/", response_model=list[TemplateResponse])
async def list_templates(db: Session = Depends(get_db)):
    """List all available templates with GPU recommendations"""
    service = TemplateService(db)
    return service.get_all_templates()

@router.post("/{slug}/deploy", response_model=DeploymentResponse)
async def deploy_template(slug: str, request: DeploymentRequest, db: Session = Depends(get_db)):
    """Deploy a template to Vast.ai with one-click provisioning"""
    service = TemplateService(db)
    return await service.deploy_template(slug, request)
```

**Key Points:**
- Use APIRouter for route grouping
- Dependency injection for database sessions
- Response models for type safety
- Async handlers for I/O operations

### Frontend: React Component Pattern

From existing web service patterns (Radix UI + Tailwind):

```jsx
// web/src/components/TemplateCard.jsx
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export function TemplateCard({ template, onDeploy }) {
  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-lg">{template.name}</h3>
          <p className="text-sm text-gray-600 mt-1">{template.description}</p>
        </div>
        <Badge>{template.gpu_requirements.min_vram}GB VRAM</Badge>
      </div>
      <Button onClick={() => onDeploy(template.slug)} className="mt-4 w-full">
        Deploy Now
      </Button>
    </Card>
  )
}
```

**Key Points:**
- Use existing Radix UI components from `@/components/ui/`
- Follow Tailwind CSS utility classes for styling
- Props-based component design with event handlers
- Consistent spacing and hover states

### Redux State Management Pattern

From existing Redux Toolkit patterns:

```javascript
// web/src/store/slices/templateSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import axios from 'axios'

export const fetchTemplates = createAsyncThunk(
  'templates/fetchAll',
  async () => {
    const response = await axios.get('/api/templates')
    return response.data
  }
)

const templateSlice = createSlice({
  name: 'templates',
  initialState: { items: [], status: 'idle', error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTemplates.pending, (state) => { state.status = 'loading' })
      .addCase(fetchTemplates.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
      })
  }
})

export default templateSlice.reducer
```

**Key Points:**
- Use createAsyncThunk for API calls
- Handle loading/success/error states
- Export thunks and selectors for component usage

## Requirements

### Functional Requirements

#### 1. Template Metadata Storage
**Description:** Store template definitions (4 templates: JupyterLab, Stable Diffusion WebUI, ComfyUI, vLLM) in PostgreSQL with GPU requirements, Docker images, launch commands, and documentation URLs.

**Acceptance:**
- Database migration creates `templates` table with fields: id, name, slug, description, docker_image, gpu_min_vram, gpu_recommended_vram, cuda_version, ports (JSON), volumes (JSON), launch_command, env_vars (JSON), documentation_url, created_at
- Seed data populates 4 official templates with configurations from research (see table below)

**Template Seed Data (from research.json):**

| Template | Slug | Docker Image | Launch Command | Ports | Volumes | Env Vars | Min VRAM | Rec VRAM | CUDA |
|----------|------|--------------|----------------|-------|---------|----------|----------|----------|------|
| JupyterLab | `jupyter-lab` | `jupyter/pytorch-notebook:latest` | `jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root` | `[8888]` | `["/home/jovyan/work"]` | `{"JUPYTER_ENABLE_LAB": "yes"}` | 4GB | 8GB | 11.8 |
| Stable Diffusion WebUI | `stable-diffusion` | `ghcr.io/absolutelyludicrous/automatic1111-webui:latest` (unverified) | `python launch.py --listen --port 7860` | `[7860]` | `["/app/models", "/app/outputs"]` | `{"COMMANDLINE_ARGS": "--medvram"}` | 4GB | 8GB | 11.8 |
| ComfyUI | `comfy-ui` | `yanwk/comfyui-boot:latest` (unverified) | `python main.py --listen 0.0.0.0 --port 8188` | `[8188]` | `["/app/models", "/app/output", "/app/input"]` | `{}` | 4GB | 8GB | 11.8 |
| vLLM | `vllm` | `vllm/vllm-openai:latest` (unverified) | `python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-7b-hf --host 0.0.0.0 --port 8000` | `[8000]` | `["/root/.cache/huggingface"]` | `{"HUGGING_FACE_HUB_TOKEN": ""}` | 16GB | 24GB | 11.8 |

**IMPORTANT**: Docker images and commands marked "(unverified)" are based on research phase findings but were NOT verified against live documentation. Implementation must validate these work correctly before deployment.

#### 2. Template Listing API
**Description:** REST endpoint that returns all available templates with filtering by GPU capability.

**Acceptance:**
- `GET /api/templates` returns JSON array of templates
- Optional query param `?min_vram=X` filters templates requiring ≤X GB VRAM
- Response includes all metadata fields needed for UI rendering

#### 3. Template Deployment API
**Description:** REST endpoint that provisions Vast.ai instance with template configuration.

**Acceptance:**
- `POST /api/templates/:slug/deploy` accepts GPU selection and deployment options
- Backend calls Vast.ai API with template's docker_image, ports, volumes, and launch_command
- Returns deployment status with instance_id and connection details
- Validates GPU meets template minimum requirements before deployment

**CRITICAL CAVEAT**: Vast.ai integration mechanism is UNVERIFIED per research phase (marked as HIGH RISK). Research identified these unknowns:
- How instances are currently provisioned
- Whether a programmatic deployment API exists
- What image formats are supported
- How templates/images are managed on the platform

**Implementation must first:**
1. Investigate existing Vast.ai integration code (if any)
2. Verify API endpoints and authentication
3. Test deployment flow with a simple container before implementing full template system
4. Document actual Vast.ai API patterns found (may differ from assumptions)

#### 4. Template Marketplace UI
**Description:** Dashboard page displaying template cards with filtering and one-click deployment.

**Acceptance:**
- `/templates` route renders grid of TemplateCard components
- Each card shows: template name, description, GPU requirements badge, "Deploy Now" button
- Filtering by GPU VRAM range (e.g., 4-8GB, 8-16GB, 16GB+)
- Clicking "Deploy Now" navigates to template detail page

#### 5. Template Detail Page
**Description:** Individual template page with full specs, getting-started guide, and deployment form.

**Acceptance:**
- `/templates/:slug` route renders template details
- Displays: full description, GPU recommendations table, ports/volumes info, embedded documentation
- Deployment form with GPU selection dropdown (filtered to compatible GPUs from Vast.ai)
- "Deploy" button triggers API call and shows deployment progress

#### 6. Per-Template Documentation
**Description:** Getting-started guides for each template accessible from detail page.

**Acceptance:**
- JupyterLab: How to access notebook, install packages, mount data volumes
- Stable Diffusion WebUI: How to access UI, download models, generate first image
- ComfyUI: How to load workflows, install custom nodes
- vLLM: How to query API, load models from HuggingFace, configure inference parameters
- Documentation rendered as Markdown or hosted as external links

### Edge Cases

1. **Template Deployment Timeout** - If Vast.ai instance doesn't become available within 5 minutes, mark deployment as failed and return error to user with retry option
2. **Insufficient GPU Availability** - If no GPUs meet template requirements on Vast.ai, show "No compatible GPUs available" message with notification signup option
3. **Template Boot Failure** - If deployed instance doesn't respond to health check within 2 minutes, flag as unhealthy and provide troubleshooting link
4. **Concurrent Deployments** - Handle multiple simultaneous template deployments by same user (queue or limit to N concurrent deployments)
5. **Missing Environment Secrets** - If VAST_API_KEY or HUGGINGFACE_TOKEN not configured, show clear error message to admin
6. **Large Model Downloads** - For Stable Diffusion/vLLM first boot, display warning about extended initial download time (may exceed 2min target on first launch)

## Implementation Notes

### DO
- **Reuse existing Vast.ai integration** - Extend existing `vast_service.py` (if present) or create new service that follows existing API client patterns
- **Follow database patterns** - Use SQLAlchemy models with timestamps, migrations via Alembic (if detected), seed data in migrations
- **Use existing UI components** - Leverage Radix UI components (@radix-ui/react-*) already in package.json for buttons, cards, badges, dropdowns
- **Store template configs as JSON** - Use PostgreSQL JSONB columns for ports, volumes, environment variables to allow flexible schema
- **Implement health checks** - Poll deployed instance with exponential backoff until service responds on expected port
- **Cache template list** - Use Redis to cache `GET /api/templates` response (TTL: 1 hour) to reduce database queries
- **Validate GPU requirements** - Query Vast.ai API for available GPUs and filter by template's min_vram before showing deployment options
- **Standardize on CUDA 11.8** - Per research recommendations, use CUDA 11.8 for maximum compatibility across PyTorch 2.0+, TensorFlow, and ML libraries (avoid version conflicts)
- **Verify Docker images during implementation** - All Docker images from research are UNVERIFIED (based on industry knowledge, not tested). Validate images exist, test launch commands, and confirm API patterns work before finalizing seed data

### DON'T
- **Don't create new component libraries** - Use existing Radix UI components and Tailwind utilities; avoid adding new UI dependencies
- **Don't hardcode Docker images** - Store images in database to allow easy updates without code changes
- **Don't skip error handling** - Vast.ai API calls can fail; implement retry logic and user-friendly error messages
- **Don't expose internal errors** - Return sanitized error responses to frontend; log detailed errors server-side
- **Don't ignore boot time optimization** - Pre-build Docker images with dependencies, use volume caching for models, implement image pre-warming if needed
- **Don't bypass GPU validation** - Always verify selected GPU meets template requirements before deployment

## Development Environment

### Start Services

**Backend:**
```bash
cd cli
pip install -r requirements.txt
export DATABASE_URL="postgresql://dumont:dumont123@localhost:5432/dumont_cloud"
export REDIS_URL="redis://localhost:6379/0"
export VAST_API_KEY="your_vast_api_key"
python __main__.py
```

**Frontend:**
```bash
cd web
npm install
npm run dev
```

**Database:**
```bash
docker-compose up -d  # Starts PostgreSQL and Redis services
```

**Run Migrations:**
```bash
cd cli
alembic upgrade head  # Apply database migrations including new templates table
```

### Service URLs
- Backend API: http://localhost:8000
- Frontend Dashboard: http://localhost:8000 (Vite dev server)
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Required Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (postgresql://dumont:dumont123@localhost:5432/dumont_cloud)
- `REDIS_URL`: Redis connection string (redis://localhost:6379/0)
- `VAST_API_KEY`: API key for Vast.ai integration (required for deployment)
- `HUGGINGFACE_TOKEN`: HuggingFace token for private model access (optional, needed for vLLM gated models)
- `APP_PORT`: Application port (default: 8000)
- `DEBUG`: Enable debug mode (default: true for development)

## Success Criteria

The task is complete when:

1. [ ] All 4 templates (JupyterLab, Stable Diffusion WebUI, ComfyUI, vLLM) are stored in database with accurate GPU requirements
2. [ ] Template marketplace UI accessible at `/templates` route with functional filtering and template cards
3. [ ] One-click deployment flow completes successfully: user clicks "Deploy Now" → selects GPU → instance provisions on Vast.ai → receives connection details
4. [ ] Each template detail page displays getting-started documentation and GPU recommendations
5. [ ] Boot time meets <2 minute target for JupyterLab and ComfyUI (with pre-built images). **Note**: First-boot downloads for Stable Diffusion (4GB models) and vLLM (14-130GB models) will exceed this target; implement model pre-loading or display clear warnings to users.
6. [ ] No console errors in browser or backend logs during deployment flow
7. [ ] Existing tests still pass (unit tests in cli/tests/, E2E tests in tests/)
8. [ ] Template deployment verified via browser: successfully deployed JupyterLab instance accessible via returned URL

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| `test_template_model` | `cli/tests/test_models.py` | Template model creation, validation, required fields |
| `test_list_templates` | `cli/tests/test_routes_templates.py` | GET /api/templates returns 4 templates, filtering by min_vram works |
| `test_deploy_template` | `cli/tests/test_routes_templates.py` | POST /api/templates/:slug/deploy validates GPU requirements, calls Vast.ai service |
| `test_template_service` | `cli/tests/test_services.py` | TemplateService CRUD operations, deployment logic, error handling |
| `test_vast_integration` | `cli/tests/test_vast_service.py` | Vast.ai API calls use template config (docker_image, ports, volumes) |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| `test_template_api_integration` | cli ↔ PostgreSQL | Templates persist correctly, migrations applied, seed data loaded |
| `test_frontend_api_integration` | web ↔ cli | Frontend fetches templates from API, displays data correctly, deploys template |
| `test_vast_deployment_integration` | cli ↔ Vast.ai API | End-to-end deployment creates instance, returns connection details |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Browse Templates | 1. Navigate to /templates 2. Verify 4 templates displayed 3. Apply GPU filter | Template cards render, filtering updates visible templates |
| View Template Details | 1. Click template card 2. Navigate to /templates/:slug 3. Verify details page | Full specs, documentation, deployment form visible |
| Deploy Template | 1. Select JupyterLab template 2. Choose compatible GPU 3. Click "Deploy" 4. Wait for provisioning | Deployment succeeds, instance ID returned, connection URL accessible |
| Verify Deployment | 1. Open returned instance URL 2. Verify JupyterLab loads 3. Check CUDA availability | JupyterLab UI loads, CUDA drivers configured, GPU accessible |

### Browser Verification (Frontend)
| Page/Component | URL | Checks |
|----------------|-----|--------|
| Template Marketplace | `http://localhost:8000/templates` | ✓ 4 template cards visible ✓ GPU filters functional ✓ No console errors ✓ Responsive layout |
| Template Detail | `http://localhost:8000/templates/jupyter-lab` | ✓ Full template specs ✓ Documentation rendered ✓ Deployment form functional |
| Deployment Flow | `/templates/:slug → Deploy` | ✓ GPU dropdown populated ✓ Form validation works ✓ Loading states shown ✓ Success message displays connection URL |

### Database Verification
| Check | Query/Command | Expected |
|-------|---------------|----------|
| Templates Table Exists | `\dt templates` (psql) | Table exists with correct schema |
| 4 Templates Seeded | `SELECT COUNT(*) FROM templates;` | Returns 4 |
| GPU Metadata Present | `SELECT slug, gpu_min_vram FROM templates;` | All templates have non-null gpu_min_vram values |
| Migration Applied | `SELECT version_num FROM alembic_version;` | Latest migration version matches code |

### API Verification
| Endpoint | Request | Expected Response |
|----------|---------|-------------------|
| List Templates | `GET /api/templates` | Status 200, JSON array with 4 items |
| Filter Templates | `GET /api/templates?min_vram=8` | Returns only templates requiring ≤8GB VRAM |
| Get Template Details | `GET /api/templates/stable-diffusion` | Status 200, full template object with GPU specs |
| Deploy Template | `POST /api/templates/jupyter-lab/deploy` with GPU ID | Status 201, deployment object with instance_id |
| Invalid Template | `GET /api/templates/nonexistent` | Status 404, error message |

### Performance Verification
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Template List Load | <500ms | Browser DevTools Network tab |
| Deployment API Response | <3s | Time from POST to response |
| JupyterLab Boot Time | <2 min | Time from deploy to first successful health check |
| ComfyUI Boot Time | <2 min | Time from deploy to UI accessible |

**IMPORTANT BOOT TIME CAVEAT**: The <2 minute boot time target applies ONLY when models are pre-downloaded or images are pre-built with dependencies. First-time deployments may significantly exceed this target:
- Stable Diffusion WebUI: **5+ minutes** on first boot (4GB model downloads)
- vLLM: **2-5 minutes** depending on model size (7B models ~14GB, 70B models ~130GB)
- Research recommendation: Pre-build Docker images with embedded models to meet boot time SLA

### QA Sign-off Requirements
- [ ] All unit tests pass (cli/tests/)
- [ ] All integration tests pass (template API ↔ database, frontend ↔ backend)
- [ ] All E2E tests pass (full deployment flow via Playwright)
- [ ] Browser verification complete: all pages render without errors, deployment flow works
- [ ] Database verification complete: migrations applied, 4 templates seeded, schema correct
- [ ] API verification complete: all endpoints return expected responses
- [ ] Performance verification complete: boot times <2min for Jupyter/ComfyUI (excluding initial downloads)
- [ ] No regressions in existing functionality (existing routes, dashboard pages still work)
- [ ] Code follows established patterns (FastAPI routes, SQLAlchemy models, React components, Redux slices)
- [ ] No security vulnerabilities introduced (secrets not exposed in logs/responses, input validation on API)
- [ ] Documentation complete: getting-started guides written for all 4 templates
