# Runtime security contract

- CORS uses an explicit environment allowlist; wildcard authenticated origins are rejected outside local/test.
- HTTPS base URLs and public media delivery are mandatory in staging/production.
- HSTS belongs at the TLS-terminating proxy and must only be enabled for stable HTTPS hosts.
- API and web send clickjacking, MIME-sniffing, referrer and permissions headers. CSP should be tightened with the selected authentication and media domains before public launch; it must preserve the Meta OAuth popup/redirect flow.
- PostgreSQL, Redis, Docker sockets and worker internals stay on private networks.
- Frontend variables may contain only public values. Database URLs, Redis URLs, Meta secrets, encryption keys and object-storage credentials remain server-side.
- Rate-limit integration points are OAuth authorization/callback, uploads, publication creation and future intelligence analysis. A distributed limiter is deliberately not claimed until the hosting topology is selected.
- Structured logs carry safe correlation fields. Tokens, authorization codes, credentials, passwords, binary content and complete provider payloads are prohibited.
- `UNCERTAIN` publication semantics remain unchanged: reconcile before retrying.
