# Social Media Preview

This directory contains the social media preview card for WATI Conductor.

## Files

- `preview.html` - Interactive HTML preview card (1200x630px)

## Usage

### View in Browser

```bash
# Open directly
open assets/social-preview/preview.html

# Or serve with Python
cd assets/social-preview
python3 -m http.server 8000
# Visit: http://localhost:8000/preview.html
```

### Generate Screenshot

**Option 1: Browser Screenshot**
1. Open `preview.html` in Chrome/Firefox
2. Set browser window to exactly 1280x640px (or use responsive mode)
3. Take screenshot (Cmd+Shift+4 on Mac, Win+Shift+S on Windows)
4. Save as `preview.png`

**Option 2: Automated (Playwright/Puppeteer)**

```bash
# Install playwright
npm install -g playwright
npx playwright install chromium

# Generate screenshot
npx playwright screenshot \
  --viewport-size=1280,640 \
  --full-page \
  file://$(pwd)/preview.html \
  preview.png
```

**Option 3: Using Docker + Puppeteer**

```bash
docker run --rm -v $(pwd):/workspace \
  ghcr.io/puppeteer/puppeteer:latest \
  node -e "
    const puppeteer = require('puppeteer');
    (async () => {
      const browser = await puppeteer.launch();
      const page = await browser.newPage();
      await page.setViewport({ width: 1280, height: 640 });
      await page.goto('file:///workspace/preview.html');
      await page.screenshot({ path: '/workspace/preview.png' });
      await browser.close();
    })();
  "
```

## Design Specs

- **Dimensions**: 1280x640px (GitHub's recommended size for best display)
- **Safe Zone**: 40pt border around all important content (prevents cropping)
- **Format**: HTML/CSS (screenshot to PNG for final use)
- **Fonts**: Inter (UI), JetBrains Mono (code)
- **Colors**:
  - WhatsApp Green: #25D366
  - Cyan Accent: #06B6D4
  - Dark Background: #0f172a → #1e1b4b gradient

### GitHub Social Preview Guidelines

✓ Image size: 1280×640px  
✓ Safe zone: 40pt border (important content stays within this margin)  
✓ File format: PNG  
✓ Max file size: 1MB

## GitHub Social Preview Setup

1. Generate `preview.png` from `preview.html`
2. Go to GitHub repo → Settings → General → Social preview
3. Upload `preview.png`
4. Preview will appear when sharing the repo link

## Customization

Edit `preview.html` to modify:
- Title/subtitle text
- Chat conversation example
- Color scheme (CSS variables in `<style>` section)
- Badges and tech stack
