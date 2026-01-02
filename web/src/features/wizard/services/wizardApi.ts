/**
 * Wizard API Service
 *
 * Testable API service with dependency injection support.
 * All API calls are abstracted here for easy mocking in tests.
 */

import {
  MachineOffer,
  OffersApiParams,
  OffersApiResponse,
  BalanceApiResponse,
  ProvisioningConfig,
  ProvisioningCandidate,
  RecommendedMachine,
} from '../types';
import { getTierFilterParams } from '../constants';

// ============================================================================
// Types for Dependency Injection
// ============================================================================

export interface HttpClient {
  get: <T>(url: string, options?: RequestInit) => Promise<T>;
  post: <T>(url: string, body: unknown, options?: RequestInit) => Promise<T>;
}

export interface WizardApiConfig {
  baseUrl: string;
  httpClient?: HttpClient;
  getAuthToken?: () => string | null;
}

// ============================================================================
// Default HTTP Client (uses fetch)
// ============================================================================

const createDefaultHttpClient = (baseUrl: string, getToken: () => string | null): HttpClient => ({
  get: async <T>(url: string, options?: RequestInit): Promise<T> => {
    const token = getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    };

    const response = await fetch(`${baseUrl}${url}`, {
      ...options,
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  },

  post: async <T>(url: string, body: unknown, options?: RequestInit): Promise<T> => {
    const token = getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    };

    const response = await fetch(`${baseUrl}${url}`, {
      ...options,
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  },
});

// ============================================================================
// Custom Error Class
// ============================================================================

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`API Error ${status}: ${body}`);
    this.name = 'ApiError';
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }
}

// ============================================================================
// Wizard API Service Class
// ============================================================================

export class WizardApiService {
  private httpClient: HttpClient;
  private baseUrl: string;

  constructor(config: WizardApiConfig) {
    this.baseUrl = config.baseUrl;
    this.httpClient = config.httpClient ?? createDefaultHttpClient(
      config.baseUrl,
      config.getAuthToken ?? (() => localStorage.getItem('auth_token')),
    );
  }

  /**
   * Fetch GPU offers from the API
   */
  async fetchOffers(params: OffersApiParams): Promise<MachineOffer[]> {
    const queryParams = new URLSearchParams();

    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.order_by) queryParams.append('order_by', params.order_by);
    if (params.region) queryParams.append('region', params.region);
    if (params.min_gpu_ram) queryParams.append('min_gpu_ram', params.min_gpu_ram.toString());
    if (params.max_price) queryParams.append('max_price', params.max_price.toString());
    if (params.verified_only) queryParams.append('verified_only', 'true');

    const url = `/api/v1/instances/offers?${queryParams.toString()}`;
    const response = await this.httpClient.get<OffersApiResponse>(url);

    return response.offers ?? [];
  }

  /**
   * Fetch offers filtered by tier
   */
  async fetchOffersByTier(
    tierName: string,
    regionCode?: string,
    limit: number = 5,
  ): Promise<RecommendedMachine[]> {
    const tierFilter = getTierFilterParams(tierName as any);

    const params: OffersApiParams = {
      limit,
      order_by: 'dph_total',
      ...tierFilter,
    };

    if (regionCode) {
      params.region = regionCode;
    }

    const offers = await this.fetchOffers(params);

    // Add labels to first 3 offers
    const labels: Array<RecommendedMachine['label']> = [
      'Mais econômico',
      'Melhor custo-benefício',
      'Mais rápido',
    ];

    return offers.slice(0, 3).map((offer, idx) => ({
      ...offer,
      label: labels[idx] ?? labels[0],
      provider: 'Vast.ai',
      location: this.formatLocation(offer.geolocation),
      reliability: offer.verified ? 99 : 95,
    }));
  }

  /**
   * Fetch user balance
   */
  async fetchBalance(): Promise<number> {
    try {
      const response = await this.httpClient.get<BalanceApiResponse>('/api/v1/balance');
      return response.credit ?? response.balance ?? 0;
    } catch (error) {
      console.error('Failed to fetch balance:', error);
      return 0;
    }
  }

  /**
   * Start provisioning a machine
   */
  async startProvisioning(config: ProvisioningConfig): Promise<{ candidates: ProvisioningCandidate[] }> {
    // In a real implementation, this would call the provisioning API
    // For now, we'll simulate by fetching offers and treating them as candidates
    const offers = await this.fetchOffersByTier(
      config.tier,
      config.location.codes[0],
      5,
    );

    const candidates: ProvisioningCandidate[] = offers.map(offer => ({
      ...offer,
      status: 'pending',
      progress: 0,
    }));

    return { candidates };
  }

  /**
   * Provision a specific machine (calls real VAST.ai API)
   */
  async provisionMachine(machineId: number, config: ProvisioningConfig): Promise<{ success: boolean; instanceId?: string }> {
    try {
      // Build ports array from config
      const ports = config.exposedPorts.length > 0
        ? config.exposedPorts.map(p => parseInt(p.port, 10)).filter(p => !isNaN(p))
        : [8080]; // Default port for VS Code Online

      const response = await this.httpClient.post<{ id: number }>('/api/v1/instances', {
        offer_id: machineId,
        image: config.dockerImage || 'pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime',
        disk_size: 100,
        label: `Wizard Deploy - ${config.tier}`,
        ports: ports,
        skip_standby: config.failoverStrategy === 'no_failover',
      });

      return { success: true, instanceId: String(response.id) };
    } catch (error) {
      console.error('Failed to provision machine:', error);
      return { success: false };
    }
  }

  /**
   * Format geolocation code to readable name
   */
  private formatLocation(geolocation: string): string {
    const locationMap: Record<string, string> = {
      US: 'Estados Unidos',
      CA: 'Canadá',
      GB: 'Reino Unido',
      DE: 'Alemanha',
      FR: 'França',
      NL: 'Holanda',
      JP: 'Japão',
      SG: 'Singapura',
      BR: 'Brasil',
    };
    return locationMap[geolocation] ?? geolocation;
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * Create a WizardApiService instance
 * Use this factory for easy testing with mock HTTP clients
 */
export function createWizardApi(config?: Partial<WizardApiConfig>): WizardApiService {
  return new WizardApiService({
    baseUrl: config?.baseUrl ?? '',
    httpClient: config?.httpClient,
    getAuthToken: config?.getAuthToken,
  });
}

/**
 * Default singleton instance
 */
let defaultInstance: WizardApiService | null = null;

export function getWizardApi(): WizardApiService {
  if (!defaultInstance) {
    defaultInstance = createWizardApi();
  }
  return defaultInstance;
}

/**
 * Reset default instance (useful for testing)
 */
export function resetWizardApi(): void {
  defaultInstance = null;
}
