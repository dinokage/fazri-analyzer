import type {
  RequestFn,
  Certificate,
  CreateCertificatePayload,
  TestHttpResult,
} from './types';
import { validateDomainNames } from './validation';

const CERT_TIMEOUT = 900_000; // 15 minutes, matching NPM backend

export class Certificates {
  constructor(private request: RequestFn) {}

  async list(options?: {
    expand?: ('owner' | 'proxy_hosts' | 'redirection_hosts' | 'dead_hosts' | 'streams')[];
    query?: string;
  }): Promise<Certificate[]> {
    const params: Record<string, string> = {};

    if (options?.expand?.length) {
      params.expand = options.expand.join(',');
    }
    if (options?.query) {
      params.query = options.query;
    }

    return this.request<Certificate[]>('GET', '/api/nginx/certificates', { params });
  }

  async get(
    id: number,
    options?: {
      expand?: ('owner' | 'proxy_hosts' | 'redirection_hosts' | 'dead_hosts' | 'streams')[];
    },
  ): Promise<Certificate> {
    const params: Record<string, string> = {};

    if (options?.expand?.length) {
      params.expand = options.expand.join(',');
    }

    return this.request<Certificate>('GET', `/api/nginx/certificates/${id}`, { params });
  }

  async create(payload: CreateCertificatePayload): Promise<Certificate> {
    if (payload.provider === 'letsencrypt' && 'domain_names' in payload) {
      validateDomainNames(payload.domain_names);
    }

    return this.request<Certificate>('POST', '/api/nginx/certificates', {
      body: payload,
      timeout: CERT_TIMEOUT,
    });
  }

  async delete(id: number): Promise<boolean> {
    return this.request<boolean>('DELETE', `/api/nginx/certificates/${id}`);
  }

  async renew(id: number): Promise<Certificate> {
    return this.request<Certificate>('POST', `/api/nginx/certificates/${id}/renew`, {
      timeout: CERT_TIMEOUT,
    });
  }

  async testHttp(domains: string[]): Promise<TestHttpResult> {
    validateDomainNames(domains);

    return this.request<TestHttpResult>('POST', '/api/nginx/certificates/test-http', {
      body: { domains },
    });
  }
}
