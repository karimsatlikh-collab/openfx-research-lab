# Owner next steps: Claude and Gemini

This checklist is for the project owner using an Android phone. It does not grant either service access to ChatGPT, the VPS, or the repository automatically.

## A. Claude mobile — install only, then wait for the project connector
1. Open Google Play Store on the phone.
2. Search for the official **Claude by Anthropic** app; verify the publisher is Anthropic before installing.
3. Open it and sign in or create an account, subject to the service's regional availability and terms.
4. Do not upload credentials, broker details, API keys, or private project secrets.
5. For now, use Claude only as an independent reviewer by pasting non-secret excerpts or asking it to critique a design. Do not connect it to the VPS.
6. A future custom MCP connector needs a real HTTPS MCP server URL and an authentication design. The OpenFX connector does not exist yet. Do not enter a placeholder URL or create a connector before the project owner has a verified endpoint.
7. When the connector is implemented, start with read-only access to approved OpenFX docs/reports. Review the requested permissions before authorizing.

Official information: https://claude.com/download and https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp

## B. Google AI Studio / Gemini API — create a key only when needed
Google AI Studio is a browser-based developer console; it is not necessary to install another phone app for the initial setup.

1. Open https://aistudio.google.com/ in a browser and sign in with a Google account.
2. Check that AI Studio is available for your actual region/account and that the terms permit your intended use.
3. Open the API keys section and create a Gemini API key only if the service is accessible and you want to proceed.
4. Do not paste the key into ChatGPT, Claude, GitHub, an issue, or a source file. Do not send a screenshot showing the key.
5. Store it only in the eventual private runtime's secret manager/environment variable. Rotate it immediately if exposed.
6. The free tier has limits and its data-use terms differ from paid service; review current terms before sending confidential code, private reports, or any personal/broker data.
7. Do not enable billing until there is a measured need and you have checked payment eligibility and regional restrictions.

Official information:
- Getting started: https://aistudio.google.com/docs/get-started
- Pricing and free tier: https://ai.google.dev/gemini-api/docs/pricing
- Supported regions: https://ai.google.dev/gemini-api/docs/available-regions

## Current OpenFX status
- The Windows VPS has not been purchased.
- MT5 is not installed on a VPS.
- The worker in this repository is a prototype that validates and records job manifests only; it does not run MT5 and is not deployed.
- The OpenFX remote MCP endpoint has not been implemented. Therefore there is currently no valid connector URL to enter in Claude.
- AI provider selection should remain configurable so OpenFX is not locked to one vendor.
