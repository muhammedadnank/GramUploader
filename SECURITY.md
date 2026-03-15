# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.6.x   | ✅        |
| < 2.6   | ❌        |

## Reporting a Vulnerability

If you discover a security vulnerability in GramUploader, please **do not open a public issue**.

Report privately via Telegram: [@adnanxpkd](https://t.me/adnanxpkd)

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Your suggested fix (optional)

### What to expect

- Acknowledgement within **48 hours**
- Status update within **7 days**
- Fix released within **14 days** for confirmed vulnerabilities

### Scope

The following are in scope:

- Authentication bypass or token leakage (OAuth2 / YouTube tokens)
- Unauthorized access to another user's data or uploads
- Bot command injection or privilege escalation
- MongoDB injection via user input
- Denial of service via the upload queue

The following are **out of scope**:

- Rate limiting bypass for non-destructive actions
- Issues in third-party dependencies (report upstream)
- Self-XSS in the OAuth callback page
