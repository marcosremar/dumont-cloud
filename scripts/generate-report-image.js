/**
 * Generate Report Image Script
 *
 * Puppeteer-based screenshot generator for shareable savings reports.
 * Takes a URL and generates a PNG screenshot with specified dimensions.
 *
 * Usage:
 *   node scripts/generate-report-image.js --url=<url> --format=<format> --output=<path>
 *
 * Options:
 *   --url     Target URL to capture (optional for testing)
 *   --format  Image format: twitter (1200x675), linkedin (1200x627), generic (1200x630)
 *   --width   Custom viewport width (overrides format)
 *   --height  Custom viewport height (overrides format)
 *   --output  Output file path (required)
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

// Format dimensions mapping
const FORMAT_DIMENSIONS = {
  twitter: { width: 1200, height: 675 },
  linkedin: { width: 1200, height: 627 },
  generic: { width: 1200, height: 630 },
};

// Chrome args for Docker/headless compatibility
// Following pattern from capture-interfaces.js
const CHROME_ARGS = [
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-dev-shm-usage',
];

/**
 * Parse command line arguments
 * @returns {Object} Parsed arguments
 */
function parseArgs() {
  const args = {};
  process.argv.slice(2).forEach((arg) => {
    if (arg.startsWith('--')) {
      const [key, value] = arg.slice(2).split('=');
      args[key] = value || true;
    }
  });
  return args;
}

/**
 * Get dimensions based on format or custom values
 * @param {Object} args - Parsed arguments
 * @returns {Object} Width and height
 */
function getDimensions(args) {
  // Custom dimensions take priority
  if (args.width && args.height) {
    return {
      width: parseInt(args.width, 10),
      height: parseInt(args.height, 10),
    };
  }

  // Use format dimensions
  const format = args.format || 'generic';
  const dimensions = FORMAT_DIMENSIONS[format.toLowerCase()];

  if (!dimensions) {
    throw new Error(
      `Invalid format: ${format}. Valid formats: ${Object.keys(FORMAT_DIMENSIONS).join(', ')}`
    );
  }

  return dimensions;
}

/**
 * Ensure output directory exists
 * @param {string} outputPath - Output file path
 */
function ensureOutputDirectory(outputPath) {
  const dir = path.dirname(outputPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

/**
 * Generate a test HTML page for validation without a URL
 * @param {Object} dimensions - Width and height
 * @param {string} format - Format name
 * @returns {string} HTML content
 */
function getTestPageContent(dimensions, format) {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        body {
          width: ${dimensions.width}px;
          height: ${dimensions.height}px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }
        .container {
          text-align: center;
          padding: 40px;
        }
        h1 {
          font-size: 48px;
          font-weight: 700;
          margin-bottom: 20px;
          text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .savings {
          font-size: 72px;
          font-weight: 800;
          margin: 30px 0;
          color: #4ade80;
          text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
          font-size: 24px;
          opacity: 0.9;
          margin-bottom: 30px;
        }
        .format-badge {
          display: inline-block;
          background: rgba(255,255,255,0.2);
          padding: 10px 20px;
          border-radius: 20px;
          font-size: 14px;
          text-transform: uppercase;
          letter-spacing: 2px;
        }
        .dimensions {
          margin-top: 20px;
          font-size: 12px;
          opacity: 0.7;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Dumont Cloud Savings</h1>
        <div class="savings">$3,247/year</div>
        <p class="subtitle">Compared to AWS, GCP, and Azure</p>
        <span class="format-badge">${format} format</span>
        <p class="dimensions">${dimensions.width}x${dimensions.height}px</p>
      </div>
    </body>
    </html>
  `;
}

/**
 * Main function to generate report image
 */
async function generateReportImage() {
  const args = parseArgs();

  // Validate required arguments
  if (!args.output) {
    process.stderr.write('Error: --output is required\n');
    process.exit(1);
  }

  const dimensions = getDimensions(args);
  const format = args.format || 'generic';
  const outputPath = args.output;

  // Ensure output directory exists
  ensureOutputDirectory(outputPath);

  let browser;

  try {
    // Launch Puppeteer with Chrome args for compatibility
    browser = await puppeteer.launch({
      headless: true,
      args: CHROME_ARGS,
    });

    const page = await browser.newPage();

    // Set viewport to exact dimensions
    await page.setViewport({
      width: dimensions.width,
      height: dimensions.height,
      deviceScaleFactor: 1,
    });

    if (args.url) {
      // Navigate to provided URL
      await page.goto(args.url, {
        waitUntil: 'networkidle2',
        timeout: 30000,
      });

      // Additional wait for any dynamic content
      await new Promise((resolve) => setTimeout(resolve, 1000));
    } else {
      // Generate test page for validation
      const testHtml = getTestPageContent(dimensions, format);
      await page.setContent(testHtml, {
        waitUntil: 'networkidle0',
      });
    }

    // Capture screenshot
    await page.screenshot({
      path: outputPath,
      type: 'png',
      clip: {
        x: 0,
        y: 0,
        width: dimensions.width,
        height: dimensions.height,
      },
    });

    // Output success info to stdout for calling process
    process.stdout.write(
      JSON.stringify({
        success: true,
        output: outputPath,
        format: format,
        dimensions: dimensions,
      }) + '\n'
    );

    process.exit(0);
  } catch (error) {
    process.stderr.write(`Error: ${error.message}\n`);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

// Run if called directly
if (require.main === module) {
  generateReportImage().catch((error) => {
    process.stderr.write(`Fatal error: ${error.message}\n`);
    process.exit(1);
  });
}

module.exports = {
  generateReportImage,
  parseArgs,
  getDimensions,
  FORMAT_DIMENSIONS,
};
