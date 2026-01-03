# Fireworks.ai UI Analysis & Documentation
Generated: 2026-01-03

## Homepage Analysis (https://fireworks.ai)

### Layout Structure

**Header**
- Logo: Fireworks AI (with flame icon)
- Simple, clean header with minimal navigation
- Light background

**Hero Section**
- Large heading: "Build. Tune. Scale" (left-aligned, bold, large typography)
- Subheading: "Open-source AI models at blazing speed, optimized for your use case, scaled globally with the Fireworks Inference Cloud"
- Clean, modern typography with good spacing

**Key Features List** (Left side)
- Bullet point list with arrow icons:
  - "Own Your AI: Control your models, data, and costs →"
  - "Customize Your AI: Tune model quality, speed, and cost to your use case →"
  - "Scale effortlessly: Run production workloads globally with 99.9% SLA →"
  - "Access 1000s of models: Day-0 support for models like DeepSeek, Kimi, gpt-oss, Gwen, etc. →"

**Social Proof Section**
- "What our customers are saying:"
- Testimonial card with:
  - Quote in italics
  - 5-star rating (purple stars)
  - Name and title: "Sualeh Asif, CPO"
  - Company logo: CURSOR
  - Navigation arrows (< >) for carousel

**Background Design**
- Purple gradient pattern (light to dark purple)
- Geometric/pixel-like visual elements
- Gradient flows from top-right corner

**Footer**
- Black background
- Multiple columns with links
- Standard footer layout

### Login Panel (Right Side)

**Panel Structure**
- White card/panel
- Heading: "Log In" (bold, centered/left-aligned)
- Vertical stack of login buttons

**Login Options** (in order):
1. "Continue with Google" - White button with Google logo
2. "Continue with GitHub" - White button with GitHub logo
3. "Continue with LinkedIn" - White button with LinkedIn logo
4. "Email Login" - White button
5. "Custom SSO Login" - White button

**Sign Up Link**
- "Don't have an account? Sign Up" (Sign Up is a purple link)

### Color Scheme
- Primary: Purple/violet (#6366f1 or similar)
- Background: White/light gray
- Text: Black/dark gray
- Accent: Purple for links and highlights
- Footer: Black

### Typography
- Sans-serif font (likely Inter, Helvetica, or similar)
- Large, bold headings
- Clean, readable body text
- Good hierarchy and spacing

---

## Login Page Analysis (https://app.fireworks.ai/login)

### Redirect Behavior
- Attempting to navigate to fireworks.ai redirects to app.fireworks.ai/login
- Then redirects to Google OAuth flow if clicking "Continue with Google"

### Authentication Flow
- Supports multiple OAuth providers:
  - Google (primary)
  - GitHub
  - LinkedIn
- Also supports:
  - Email/password login
  - Custom SSO

### URL Structure
- Main site: https://fireworks.ai
- App login: https://app.fireworks.ai/login
- OAuth redirect: Uses AWS Cognito (fireworks.auth.us-west-2.amazoncognito.com)

---

## UI Components Observed

### Buttons
**Style Characteristics:**
- Rounded corners (moderate radius, ~8px)
- Clean, flat design
- White background with subtle border
- Hover states (likely)
- Icon + text layout for OAuth buttons
- Good padding and spacing

**Button Types:**
1. Primary action buttons (likely purple background)
2. OAuth buttons (white with provider logos)
3. Navigation buttons (carousel arrows - circular outline)

### Cards
- White background
- Subtle shadow/border
- Rounded corners
- Good padding
- Clean separation from background

### Layout
- Two-column layout on homepage (60/40 split approx)
- Responsive design (likely)
- Generous whitespace
- Center-aligned content in containers

### Icons
- Clean, minimal line icons
- Provider logos for OAuth
- Arrow icons for links
- Star icons for ratings

---

## Inferred Fine-Tuning Interface (Not Yet Visible)

Based on the homepage messaging and typical AI platform patterns, the fine-tuning interface likely includes:

1. **Model Selection**
   - Dropdown or card-based model picker
   - Filters for model type/size
   - Model information cards

2. **Dataset Configuration**
   - File upload component
   - Dataset format selector (JSONL, CSV, etc.)
   - Data preview/validation

3. **Training Parameters**
   - Epochs slider/input
   - Learning rate input
   - Batch size selector
   - LoRA settings (rank, alpha, dropout)

4. **Job Configuration**
   - Job name input
   - Description textarea
   - Resource allocation (GPU selection)

5. **Cost Estimation**
   - Real-time cost calculator
   - Estimated training time

6. **Action Buttons**
   - "Create Fine-Tuning Job" (primary)
   - "Save as Draft"
   - "Cancel"

---

## Next Steps for Full Exploration

To fully document the fine-tuning interface, we need to:

1. Authenticate with valid credentials
2. Navigate to the fine-tuning section (likely at /models, /fine-tune, or /jobs)
3. Capture the full form interface
4. Document all input fields, dropdowns, and options
5. Capture the job creation flow
6. Document the job monitoring/results interface

**Note:** Without authentication, we cannot access the internal application interface where fine-tuning jobs are created and managed.
