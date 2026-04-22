# @fazri/npm-sdk

Internal TypeScript SDK for [Nginx Proxy Manager](https://nginxproxymanager.com/) API. Used by `apps/auth` for programmatic proxy host management and SSL certificate provisioning.

Zero dependencies. Works with Node.js 18+.

## Usage

```typescript
import { NpmClient } from '@fazri/npm-sdk';

const client = new NpmClient({
  baseUrl: 'http://127.0.0.1:81',
  email: 'admin@example.com',
  password: 'your-password',
});

// List all proxy hosts
const hosts = await client.proxyHosts.list();

// Create a proxy host with auto SSL
const host = await client.proxyHosts.create({
  domain_names: ['app.example.com'],
  forward_scheme: 'http',
  forward_host: '127.0.0.1',
  forward_port: 3000,
  certificate_id: 'new',
  ssl_forced: true,
  allow_websocket_upgrade: true,
});
```

## Authentication

The SDK supports two authentication methods. You can use either or both.

**Credentials (auto-managed):** The SDK logs in on the first request and refreshes the token automatically when it expires.

```typescript
const client = new NpmClient({
  baseUrl: 'http://127.0.0.1:81',
  email: 'admin@example.com',
  password: 'your-password',
});
```

**Token (manual):** Use a pre-obtained Bearer token directly.

```typescript
const client = new NpmClient({
  baseUrl: 'http://127.0.0.1:81',
  token: 'eyJhbGciOi...',
});
```

**Both:** If both are provided, the token is used first. Credentials are used as fallback when the token expires.

You can also call `login()` and `refreshToken()` manually:

```typescript
const tokenData = await client.login();
console.log(tokenData.token, tokenData.expires);

const refreshed = await client.refreshToken();
```

## API

### Proxy Hosts

```typescript
// List all proxy hosts
const hosts = await client.proxyHosts.list();

// List with expanded relations
const hosts = await client.proxyHosts.list({
  expand: ['owner', 'certificate', 'access_list'],
  query: 'example.com',
});

// Get a single proxy host
const host = await client.proxyHosts.get(1);

// Create a proxy host
const host = await client.proxyHosts.create({
  domain_names: ['app.example.com'],
  forward_scheme: 'http',
  forward_host: '127.0.0.1',
  forward_port: 3000,
  certificate_id: 'new',    // auto-provision Let's Encrypt SSL
  ssl_forced: true,
  http2_support: true,
  block_exploits: true,
  allow_websocket_upgrade: true,
  advanced_config: '',       // raw nginx config (optional)
  locations: [],             // custom location blocks (optional)
});

// Update a proxy host (partial update, only send changed fields)
const updated = await client.proxyHosts.update(1, {
  forward_port: 4000,
  ssl_forced: true,
});

// Delete a proxy host
await client.proxyHosts.delete(1);

// Enable / Disable
await client.proxyHosts.enable(1);
await client.proxyHosts.disable(1);
```

### Certificates

```typescript
// List all certificates
const certs = await client.certificates.list();

// Get a single certificate
const cert = await client.certificates.get(1);

// Create a Let's Encrypt certificate (HTTP-01 challenge)
const cert = await client.certificates.create({
  provider: 'letsencrypt',
  domain_names: ['app.example.com'],
  meta: { key_type: 'ecdsa' },
});

// Create a Let's Encrypt certificate (DNS challenge)
const cert = await client.certificates.create({
  provider: 'letsencrypt',
  domain_names: ['*.example.com'],
  meta: {
    dns_challenge: true,
    dns_provider: 'cloudflare',
    dns_provider_credentials: 'dns_cloudflare_api_token = xxxxx',
    propagation_seconds: 30,
    key_type: 'ecdsa',
  },
});

// Renew a certificate
const renewed = await client.certificates.renew(1);

// Delete a certificate
await client.certificates.delete(1);

// Test HTTP reachability before requesting a cert
const results = await client.certificates.testHttp(['app.example.com']);
// { 'app.example.com': 'ok' }
```

## SSL with Proxy Hosts

The `certificate_id` field on proxy hosts controls SSL:

| Value | Behavior |
|-------|----------|
| `'new'` | Auto-provision a Let's Encrypt certificate using the proxy host's domains |
| `0` (or omit) | No SSL |
| `<number>` | Use an existing certificate by ID |

When a certificate is assigned, SSL options cascade:
- No certificate = `ssl_forced`, `http2_support` forced to `false`
- No `ssl_forced` = `hsts_enabled` forced to `false`
- No `hsts_enabled` = `hsts_subdomains` forced to `false`

## Custom Location Blocks

Proxy hosts support custom location blocks for path-based routing:

```typescript
await client.proxyHosts.create({
  domain_names: ['app.example.com'],
  forward_scheme: 'http',
  forward_host: '127.0.0.1',
  forward_port: 3000,
  locations: [
    {
      path: '/api',
      forward_scheme: 'http',
      forward_host: '127.0.0.1',
      forward_port: 8080,
    },
    {
      path: '/ws',
      forward_scheme: 'http',
      forward_host: '127.0.0.1',
      forward_port: 8081,
      advanced_config: 'proxy_read_timeout 86400;',
    },
  ],
});
```

## Advanced Nginx Config

The `advanced_config` field injects raw nginx directives into the server block. Use with caution — syntax errors will break the proxy host.

```typescript
await client.proxyHosts.create({
  domain_names: ['app.example.com'],
  forward_scheme: 'http',
  forward_host: '127.0.0.1',
  forward_port: 3000,
  advanced_config: `
    proxy_read_timeout 86400;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  `,
});
```

## Error Handling

All API errors throw `NpmApiError` with the status code and error body:

```typescript
import { NpmClient, NpmApiError } from '@fazri/npm-sdk';

try {
  await client.proxyHosts.create({ ... });
} catch (err) {
  if (err instanceof NpmApiError) {
    console.error(err.statusCode);  // 400, 401, 404, etc.
    console.error(err.message);     // "Domains are invalid"
    console.error(err.body);        // { error: { code: 400, message: '...' } }
  }
}
```

## Timeouts

Default timeout is 30 seconds for standard API calls. Certificate creation and renewal use a 15-minute timeout to accommodate Let's Encrypt provisioning delays.

## Security

- **Clear credentials when done**: Call `client.clearCredentials()` to remove sensitive data from memory.
- **Use tokens when possible**: Prefer Bearer tokens over email/password to minimize credential exposure.
- **Domain validation**: The SDK rejects characters that would break nginx `server_name` (spaces, semicolons, braces).
- **Advanced config validation**: Checks for patterns that would break out of the server block context.

## TypeScript

Full type definitions are included. All payload interfaces are exported:

```typescript
import type {
  ProxyHost,
  CreateProxyHostPayload,
  UpdateProxyHostPayload,
  Certificate,
  CreateLetsEncryptCertPayload,
  CreateCustomCertPayload,
  ProxyHostLocation,
  TestHttpResult,
} from '@fazri/npm-sdk';
```

## Compatibility

- **Node.js:** 18+ (uses native `fetch`)
- **Nginx Proxy Manager:** v2.x (tested with v2.13.7)
- **Module format:** CommonJS (internal monorepo build)
