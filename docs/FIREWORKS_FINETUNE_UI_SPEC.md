# Fireworks.ai Fine-Tuning UI Specification

Captured from https://app.fireworks.ai on 2026-01-03

## Screenshots Location
All screenshots saved to: `.playwright-mcp/screenshots/`

## 1. Fine-Tuning Jobs List Page
**URL:** `/dashboard/fine-tuning?type=supervised`

### Layout
- Header: "Fine-Tuning Jobs"
- Subtitle: "View your past fine-tuning jobs and create new ones."
- Primary Button: "Fine-tune a Model" (purple, top-right)

### Search & Filters
- Search input with placeholder: "Search by id, name, dataset, or created by"
- Tabs: **Supervised** | Reinforcement | Preference
- Status dropdown filter: All / Running / Completed / Failed

### Jobs Table Columns
| Column | Description |
|--------|-------------|
| Fine-tuning jobs | Name + ID with copy button |
| Base model | Model name + ID with copy button |
| Dataset | Dataset name + ID with copy button |
| Created by | Email |
| Create time | Date + Time |
| Status | Badge (Completed/Running/Failed) + menu |

## 2. Method Selection Modal
**Trigger:** Click "Fine-tune a Model"

### Options
1. **Supervised (SFT)** - Selected by default
   - Description: "Train models on examples of correct inputs and outputs to teach specific patterns and formats."
   - Use cases:
     - Classification tasks (sentiment, categorization, routing)
     - Content extraction and entity recognition
     - Style transfer and format standardization

2. **Reinforced (RFT)**
   - Description: "A way to help AI models reason better using feedback scores instead of tons of labeled examples."

3. **Direct Preference (DPO)**
   - Description: "Uses pairs of preferred vs. rejected answers to directly teach the model what people like."

### Buttons
- Cancel (secondary)
- Continue (primary, purple)

## 3. Create Fine-Tuning Job Wizard

### Step 1: Model
- Title: "Model"
- Description: "Choose a base model or a LoRA adapter to start fine-tuning."
- Model dropdown with:
  - Search input
  - Tabs: Model Library | Custom Models
  - Options show: Logo + Model name + Provider + Model ID
- Next button

### Step 2: Dataset
- Title: "Dataset"
- Select dataset dropdown (existing datasets)
- OR Upload / Drag & Drop area
- Evaluation option dropdown:
  - "Do not use a validation dataset"
  - Select existing dataset
- Back / Next buttons

### Step 3: Optional Settings
| Field | Type | Default |
|-------|------|---------|
| Model Output Name | Text | ft-<timestamp>-<random-string> |
| Job ID | Text | auto-generated |
| Display Name | Text | (optional) |
| Epochs | Number | 1 |
| Batch Size | Number | 65536 |
| LoRA Rank | Number | 8 |
| Learning Rate | Number | 0.0001 |
| Max Context Length | Number | 65536 |
| Gradient Accumulation Steps | Number | 1 |
| Learning Rate Warmup Steps | Number | 0 |
| Turbo Mode | Checkbox | Off |
| Enable Weights & Biases | Checkbox | Off |

- Back button
- Create button (primary, purple)

## 4. Job Details Page
**URL:** `/dashboard/fine-tuning/supervised/{job_id}`

### Header
- Job output name (e.g., "ft-4hn5ujxxl3oym")
- Job resource ID with copy button
- Progress bar with: percentage • Epoch X/Y
- Actions button (dropdown)
- Deploy button

### Main Content
- Left: Training metrics chart (shows "No data" initially)
- Right: Job details

### Job Details Section
| Field | Value |
|-------|-------|
| Output Model | Link to model with copy |
| Base Model | Link to base model with copy |
| Type | Conversation |
| State | Running (with spinner icon) |
| Created On | Full date |

### Configuration Section
| Field | Value |
|-------|-------|
| Dataset | Link with copy |
| Evaluation Dataset | N/A or link |
| Epochs | Number |
| LoRA Rank | Number |
| Learning Rate | Number |
| Max Context Length | Number |
| Chunk Size | Not set or Number |
| Turbo Mode | On/Off |

### Deployments Section
- Title: "Deployments"
- Shows "No current deployments." when empty
- Or list of deployments

## 5. Design System

### Colors
- Primary: Purple (#7C3AED or similar)
- Success: Green (#22C55E)
- Background: White/Light gray
- Text: Dark gray/Black
- Borders: Light gray

### Components
- Cards with subtle shadow
- Rounded corners (8px)
- Clear visual hierarchy
- Collapsible accordion sections with step indicators
- Progress indicators (numbered circles)
- Status badges (colored pills)
- Copy to clipboard buttons
- Breadcrumb navigation

### Typography
- Sans-serif font (Inter or similar)
- Clear heading hierarchy
- Subtle secondary text (gray)

## 6. Implementation Priority for Dumont Cloud

### Phase 1: Core UI
1. Recreate the 3-step wizard structure
2. Model selection with search
3. Dataset selection with upload option
4. Configuration form

### Phase 2: Job Management
1. Jobs list with filtering
2. Job details page
3. Progress monitoring
4. Status badges

### Phase 3: Advanced Features
1. Reinforcement fine-tuning
2. Direct Preference Optimization
3. Weights & Biases integration
4. Model deployment from fine-tune
