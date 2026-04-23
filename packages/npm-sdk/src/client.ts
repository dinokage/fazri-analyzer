import { ProxyHosts } from './proxy-hosts';
import { Certificates } from './certificates';
import type {
  NpmClientConfig,
  NpmApiErrorBody,
  TokenResponse,
  AuthResponse,
  RequestFn,
} from './types';

export class NpmApiError extends Error {
  constructor(
    public statusCode: number,
    public body: NpmApiErrorBody | null,
  ) {
    const msg = body?.error?.message ?? `NPM API responded with ${statusCode}`;
    super(msg);
    this.name = 'NpmApiError';
  }
}

export class NpmClient {
  private baseUrl: string;
  private token: string | null;
  private tokenExpires: Date | null = null;
  private email: string | null;
  private password: string | null;

  public readonly proxyHosts: ProxyHosts;
  public readonly certificates: Certificates;

  constructor(config: NpmClientConfig) {
    const url = config.baseUrl.replace(/\/+$/, '');
    try {
      const parsed = new URL(url);
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        throw new Error('baseUrl must use http or https protocol');
      }
      this.baseUrl = url;
    } catch (err) {
      throw new Error(`Invalid baseUrl: ${err instanceof Error ? err.message : 'Must be a valid URL'}`);
    }

    this.token = config.token ?? null;
    this.email = config.email ?? null;
    this.password = config.password ?? null;

    const requestFn: RequestFn = this.request.bind(this);
    this.proxyHosts = new ProxyHosts(requestFn);
    this.certificates = new Certificates(requestFn);
  }

  async login(email?: string, password?: string): Promise<TokenResponse> {
    const identity = email ?? this.email;
    const secret = password ?? this.password;

    if (!identity || !secret) {
      throw new Error('Email and password are required for login.');
    }

    const res = await fetch(`${this.baseUrl}/api/tokens`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identity, secret }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null) as NpmApiErrorBody | null;
      throw new NpmApiError(res.status, body);
    }

    const data = await res.json() as AuthResponse;

    if ('requires_2fa' in data) {
      throw new Error(
        '2FA is enabled on this NPM account. Pass a pre-authenticated token instead.',
      );
    }

    this.token = data.token;
    this.tokenExpires = new Date(data.expires);
    this.email = identity;
    this.password = secret;

    return data;
  }

  async refreshToken(): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>('GET', '/api/tokens');
    this.token = data.token;
    this.tokenExpires = new Date(data.expires);
    return data;
  }

  private async request<T>(
    method: string,
    path: string,
    options?: {
      body?: unknown;
      params?: Record<string, string>;
      timeout?: number;
    },
  ): Promise<T> {
    await this.ensureAuth();

    let url = `${this.baseUrl}${path}`;

    if (options?.params) {
      const search = new URLSearchParams(options.params);
      url += `?${search.toString()}`;
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const timeoutMs = options?.timeout ?? 30_000;
    const maxRetries = 2;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      try {
        const res = await fetch(url, {
          method,
          headers,
          body: options?.body ? JSON.stringify(options.body) : undefined,
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => null) as NpmApiErrorBody | null;
          throw new NpmApiError(res.status, body);
        }

        return await res.json() as T;
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          throw new Error(`Request timeout after ${timeoutMs}ms: ${method} ${path}`);
        }

        const isSocketError =
          err instanceof TypeError &&
          err.message === 'fetch failed' &&
          (err.cause as NodeJS.ErrnoException)?.code === 'UND_ERR_SOCKET';

        if (isSocketError && attempt < maxRetries) {
          await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
          continue;
        }

        throw err;
      } finally {
        clearTimeout(timer);
      }
    }

    throw new Error('Request failed after retries.');
  }

  private async ensureAuth(): Promise<void> {
    if (this.token && this.tokenExpires && this.tokenExpires > new Date()) {
      return;
    }

    if (this.email && this.password) {
      await this.login();
      return;
    }

    if (this.token && (!this.tokenExpires || this.tokenExpires <= new Date())) {
      throw new Error('NPM token expired and no credentials available for refresh');
    }

    if (!this.token) {
      throw new Error(
        'No authentication available. Provide a token or email+password.',
      );
    }
  }

  clearCredentials(): void {
    this.token = null;
    this.tokenExpires = null;
    this.email = null;
    this.password = null;
  }
}
