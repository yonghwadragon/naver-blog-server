# Deploy Trigger

This file is used to force Render deployment.

Build timestamp: 2025-08-14 14:56:00

## Changes
- Added Puppeteer support (pyppeteer==1.0.2)
- Added Playwright as backup (playwright==1.40.0) 
- Chrome user data directory conflict resolution
- Fallback from Puppeteer to Selenium

## Expected Result
Health endpoint should show:
```json
{
  "puppeteer_available": true,
  "automation_engine": "Puppeteer"
}
```

If Puppeteer fails to install, should show:
```json
{
  "puppeteer_available": false, 
  "automation_engine": "Selenium"
}
```