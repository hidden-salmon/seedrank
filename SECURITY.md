# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in Seedrank, please report it responsibly.

**Do not open a public issue.**

Instead, email **security@seedrank.dev** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 1 week
- **Fix or mitigation**: as soon as possible, depending on severity

## Scope

Seedrank handles API credentials (DataForSEO, OpenAI, Anthropic, Google OAuth) and stores data in local SQLite databases. Security issues we care about include:

- Credential exposure (API keys leaking to logs, error messages, or git)
- SQL injection in database queries
- Command injection via CLI inputs
- Insecure handling of OAuth tokens
- Dependencies with known vulnerabilities

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
