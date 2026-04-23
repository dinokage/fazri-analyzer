import type {
  RequestFn,
  ProxyHost,
  CreateProxyHostPayload,
  UpdateProxyHostPayload,
} from './types';
import { validateAdvancedConfig, validateDomainNames } from './validation';

export class ProxyHosts {
  constructor(private request: RequestFn) {}

  async list(options?: {
    expand?: ('owner' | 'certificate' | 'access_list')[];
    query?: string;
  }): Promise<ProxyHost[]> {
    const params: Record<string, string> = {};

    if (options?.expand?.length) {
      params.expand = options.expand.join(',');
    }
    if (options?.query) {
      params.query = options.query;
    }

    return this.request<ProxyHost[]>('GET', '/api/nginx/proxy-hosts', { params });
  }

  async get(
    id: number,
    options?: { expand?: ('owner' | 'certificate' | 'access_list')[] },
  ): Promise<ProxyHost> {
    const params: Record<string, string> = {};

    if (options?.expand?.length) {
      params.expand = options.expand.join(',');
    }

    return this.request<ProxyHost>('GET', `/api/nginx/proxy-hosts/${id}`, { params });
  }

  async create(payload: CreateProxyHostPayload): Promise<ProxyHost> {
    validateDomainNames(payload.domain_names);
    validateAdvancedConfig(payload.advanced_config);

    if (payload.locations) {
      for (const location of payload.locations) {
        validateAdvancedConfig(location.advanced_config);
      }
    }

    return this.request<ProxyHost>('POST', '/api/nginx/proxy-hosts', {
      body: payload,
    });
  }

  async update(id: number, payload: UpdateProxyHostPayload): Promise<ProxyHost> {
    validateDomainNames(payload.domain_names);
    validateAdvancedConfig(payload.advanced_config);

    if (payload.locations) {
      for (const location of payload.locations) {
        validateAdvancedConfig(location.advanced_config);
      }
    }

    return this.request<ProxyHost>('PUT', `/api/nginx/proxy-hosts/${id}`, {
      body: payload,
    });
  }

  async delete(id: number): Promise<boolean> {
    return this.request<boolean>('DELETE', `/api/nginx/proxy-hosts/${id}`);
  }

  async enable(id: number): Promise<boolean> {
    return this.request<boolean>('POST', `/api/nginx/proxy-hosts/${id}/enable`);
  }

  async disable(id: number): Promise<boolean> {
    return this.request<boolean>('POST', `/api/nginx/proxy-hosts/${id}/disable`);
  }
}
