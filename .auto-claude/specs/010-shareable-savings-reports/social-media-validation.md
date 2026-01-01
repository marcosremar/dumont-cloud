# Social Media Preview Validation Checklist

This document describes the manual verification steps for validating social media previews for shareable savings reports.

## Prerequisites

1. **Publicly accessible URL**: Social media crawlers (Twitter, Facebook, LinkedIn) cannot access `localhost` or internal network URLs. The application must be deployed to a publicly accessible domain.

2. **Generated report with image**: A report must be generated with the image generation service running (Puppeteer) so that `image_url` is populated.

3. **HTTPS**: Most social platforms require HTTPS for og:image URLs.

## Implementation Summary

The following meta tags are rendered by `PageMeta` component for shareable reports:

### Open Graph Tags
- `og:title` - Report title (e.g., "Saving $3.2K/year with Dumont Cloud")
- `og:description` - Description with savings percentage
- `og:image` - Absolute URL to generated report image
- `og:url` - Canonical URL of the shareable report
- `og:type` - "article"

### Twitter Card Tags
- `twitter:card` - "summary_large_image" (displays large preview image)
- `twitter:title` - Same as og:title
- `twitter:description` - Same as og:description
- `twitter:image` - Same as og:image
- `twitter:site` - "@dumontcloud"

## Manual Validation Steps

### Step 1: Generate a Test Report

1. Log in to the application
2. Navigate to the dashboard
3. Click "Share Report" button
4. Select format (Twitter recommended for testing)
5. Configure desired metrics
6. Click "Generate Shareable Link"
7. Copy the generated URL (e.g., `https://dumontcloud.com/reports/abc123xyz`)

### Step 2: Validate with Twitter Card Validator

1. Open [Twitter Card Validator](https://cards-dev.twitter.com/validator)
2. Paste the shareable report URL
3. Click "Preview Card"
4. **Verify the following:**
   - [ ] Card type is "Summary Large Image"
   - [ ] Title displays correctly (e.g., "Saving $3.2K/year with Dumont Cloud")
   - [ ] Description is visible and accurate
   - [ ] Image renders correctly with proper dimensions (1200x675 for Twitter format)
   - [ ] No broken image icon
   - [ ] Site attribution shows "@dumontcloud"

### Step 3: Validate with Facebook Sharing Debugger

1. Open [Facebook Sharing Debugger](https://developers.facebook.com/tools/debug/)
2. Paste the shareable report URL
3. Click "Debug"
4. **Verify the following:**
   - [ ] og:title is correctly extracted
   - [ ] og:description is correctly extracted
   - [ ] og:image is correctly fetched (check image dimensions)
   - [ ] No warnings about missing required properties
   - [ ] Preview shows the expected card layout

### Step 4: Validate with LinkedIn Post Inspector (Optional)

1. Open [LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/)
2. Paste the shareable report URL
3. Click "Inspect"
4. **Verify the following:**
   - [ ] Title and description display correctly
   - [ ] Image preview renders properly
   - [ ] No validation errors

## Troubleshooting

### Image Not Displaying

1. **Check og:image URL is absolute**: Must start with `https://`, not relative path
2. **Verify image exists**: Access the `image_url` directly in browser
3. **Check image dimensions**: Recommended minimum 1200x630 pixels
4. **Check file size**: Should be under 5MB
5. **Verify HTTPS**: Image URL must be served over HTTPS

### Meta Tags Not Found

1. **SSR Required**: Social crawlers don't execute JavaScript. If using client-side rendering only, meta tags won't be visible to crawlers.
2. **Use server-side meta injection** or pre-rendering for production.
3. **Cache issues**: Use "Scrape Again" button in Facebook Debugger to force refresh.

### Card Type Incorrect

1. Verify `twitter:card` is set to `summary_large_image`
2. Ensure image meets minimum size requirements (1200x600 for large image cards)

## Code Changes Made

### Backend (`src/api/v1/schemas/reports.py`)
Added `image_url` field to `ReportDataResponse` schema to expose the generated image URL in the public API.

### Backend (`src/api/v1/endpoints/reports.py`)
Updated `get_report` endpoint to include `image_url` in the response for social media og:image support.

### Frontend (`web/src/components/tailadmin/reports/ShareableReportView.tsx`)
- Added `image_url` to `ReportData` TypeScript interface
- Passed `ogImage={report.image_url}` to PageMeta component

## Expected Behavior

When a shareable report URL is shared on social media:

1. **Twitter**: Displays a large image card with the savings report preview, title showing savings amount, and description with percentage saved.

2. **Facebook**: Displays link preview with the report image, engaging title, and call-to-action description.

3. **LinkedIn**: Professional link preview suitable for B2B sharing with clear value proposition.

## Sign-off Criteria

- [ ] Twitter Card Validator shows correct preview with image
- [ ] Facebook Sharing Debugger shows no errors/warnings
- [ ] All required meta tags are present and correctly formatted
- [ ] Image loads quickly and displays at correct dimensions
- [ ] No sensitive user data exposed in meta tags or preview
