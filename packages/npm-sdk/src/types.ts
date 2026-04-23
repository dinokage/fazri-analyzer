/**
 * SDK configuration. Pass either a token or email+password for authentication.
 * If both are provided, the token is used first. Credentials are used as fallback
 * and for automatic re-authentication when the token expires.
 */
export interface NpmClientConfig {
  baseUrl: string;
  token?: string;
  email?: string;
  password?: string;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface TokenResponse {
  token: string;
  expires: string;
}

export interface TokenChallengeResponse {
  requires_2fa: true;
  challenge_token: string;
}

export type AuthResponse = TokenResponse | TokenChallengeResponse;

// ---------------------------------------------------------------------------
// Proxy Hosts
// ---------------------------------------------------------------------------

export interface ProxyHostLocation {
  path: string;
  forward_scheme: 'http' | 'https';
  forward_host: string;
  forward_port: number;
  forward_path?: string;
  advanced_config?: string;
}

export interface CreateProxyHostPayload {
  domain_names: string[];
  forward_scheme: 'http' | 'https';
  forward_host: string;
  forward_port: number;
  certificate_id?: number | 'new';
  ssl_forced?: boolean;
  hsts_enabled?: boolean;
  hsts_subdomains?: boolean;
  trust_forwarded_proto?: boolean;
  http2_support?: boolean;
  block_exploits?: boolean;
  caching_enabled?: boolean;
  allow_websocket_upgrade?: boolean;
  access_list_id?: number;
  advanced_config?: string;
  enabled?: boolean;
  meta?: Record<string, unknown>;
  locations?: ProxyHostLocation[];
}

export type UpdateProxyHostPayload = Partial<CreateProxyHostPayload>;

export interface ProxyHost {
  id: number;
  created_on: string;
  modified_on: string;
  owner_user_id: number;
  domain_names: string[];
  forward_scheme: 'http' | 'https';
  forward_host: string;
  forward_port: number;
  certificate_id: number;
  ssl_forced: boolean;
  hsts_enabled: boolean;
  hsts_subdomains: boolean;
  trust_forwarded_proto: boolean;
  http2_support: boolean;
  block_exploits: boolean;
  caching_enabled: boolean;
  allow_websocket_upgrade: boolean;
  access_list_id: number;
  advanced_config: string;
  enabled: boolean;
  meta: Record<string, unknown>;
  locations: ProxyHostLocation[];
  owner?: Owner;
  certificate?: Certificate;
  access_list?: AccessList;
}

// ---------------------------------------------------------------------------
// Certificates
// ---------------------------------------------------------------------------

export interface CertificateMeta {
  dns_challenge?: boolean;
  dns_provider?: string;
  dns_provider_credentials?: string;
  propagation_seconds?: number;
  key_type?: 'rsa' | 'ecdsa';
  [key: string]: unknown;
}

export interface CreateLetsEncryptCertPayload {
  provider: 'letsencrypt';
  domain_names: string[];
  meta?: CertificateMeta;
}

export interface CreateCustomCertPayload {
  provider: 'other';
  nice_name: string;
}

export type CreateCertificatePayload =
  | CreateLetsEncryptCertPayload
  | CreateCustomCertPayload;

export interface Certificate {
  id: number;
  created_on: string;
  modified_on: string;
  owner_user_id: number;
  provider: string;
  nice_name: string;
  domain_names: string[];
  expires_on: string;
  meta: CertificateMeta;
  owner?: Owner;
}

export interface TestHttpResult {
  [domain: string]: 'ok' | 'no-host' | 'failed' | '404' | 'wrong-data' | (string & {});
}

// ---------------------------------------------------------------------------
// Shared / Expansion types
// ---------------------------------------------------------------------------

export interface Owner {
  id: number;
  created_on: string;
  modified_on: string;
  is_disabled: boolean;
  email: string;
  name: string;
  nickname: string;
  avatar: string;
  roles: string[];
}

export interface AccessList {
  id: number;
  created_on: string;
  modified_on: string;
  owner_user_id: number;
  name: string;
  meta: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// API Error
// ---------------------------------------------------------------------------

export interface NpmApiErrorBody {
  error: {
    code: number;
    message: string;
  };
}

// ---------------------------------------------------------------------------
// Internal: shared request function signature
// ---------------------------------------------------------------------------

export type RequestFn = <T>(
  method: string,
  path: string,
  options?: {
    body?: unknown;
    params?: Record<string, string>;
    timeout?: number;
  },
) => Promise<T>;
