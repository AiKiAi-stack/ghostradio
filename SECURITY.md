# Security Assessment: Token Handling in GhostRadio

## Overview
GhostRadio currently implements a "flexible" token handling mechanism where API keys can be injected from the frontend. While convenient for multi-user shared instances without server-side configuration, this pattern introduces several security risks.

## Identified Risks

### 1. Base64 "Obfuscation" is Not Encryption
The frontend encodes API keys using `btoa()` before transmission.
- **Vulnerability**: Any attacker intercepting the network traffic can decode this instantly (`atob()`). 
- **Impact**: Exposure of API keys to any party in the network path (ISPs, proxy servers, etc.) if HTTPS is not used.

### 2. LocalStorage Exposure (XSS)
API keys are stored in the browser's `localStorage`.
- **Vulnerability**: `localStorage` is accessible via JavaScript on the same origin. If the application has a Cross-Site Scripting (XSS) vulnerability, an attacker can steal all stored keys.
- **Impact**: Full compromise of user API keys.

### 3. Client-to-Server Secret Transmission
Sending secrets from a client to a server in every request is fundamentally less secure than server-side secret management.
- **Vulnerability**: Increases the "attack surface" for the secret. It exists in the browser memory, the browser storage, and the network request.
- **Impact**: Multiple points of potential failure.

## Recommendations

### Short-term: Use Server-Side Configuration (Highly Recommended)
Store your API keys in the server's environment variables or `config.yaml`.
- Set `VOLCENGINE_TOKEN` and `VOLCENGINE_APPID` on your VPS.
- The server will prioritize these over any keys sent from the frontend.

### Medium-term: Enable HTTPS
Always serve GhostRadio over HTTPS (using a reverse proxy like Nginx with Let's Encrypt). This protects the Base64-encoded strings from being read in transit.

### Long-term: Identity Management
Implement a proper login system where the server handles authentication and keys are never transmitted from the client in raw or obfuscated form.

---
*Note: GhostRadio is designed as a minimalist tool for personal use. If you are hosting this for public use, please be aware of these risks.*
