# Runtime environments

SocialOS follows one rule: **local is a development provider, not the architecture**. Domain and application code use ports; environment variables choose adapters and runtime endpoints.

| Concern | Local development | Staging | Production |
| --- | --- | --- | --- |
| Public app URL | Loopback | Stable HTTPS | Stable HTTPS |
| PostgreSQL | Local container | External/private | External/private |
| Redis | Local container | External/private | External/private |
| Media | Local opaque-key volume | S3-compatible object storage | S3-compatible object storage |
| Meta | Development app or local provider | Disabled until explicitly configured | Not yet production verified |
| AI | Local zero-cost adapter | Configured adapter | Configured adapter |
| Debug/docs | Enabled | API docs allowed by policy | Disabled |

The validated configuration source is `socialos.config.Settings`. `DATABASE_URL`, `REDIS_URL`, public URLs, CORS origins, storage selection and provider flags change between environments; domain code does not.

Localhost, Windows paths and tunnel URLs are valid only in development instructions, fixtures and Compose. Staging and production reject insecure base URLs, wildcard CORS, development authentication and local media storage.

Secrets belong in ignored local env files during development and in the hosting platform's secret manager for staging/production. They must never be committed or copied into image layers.
