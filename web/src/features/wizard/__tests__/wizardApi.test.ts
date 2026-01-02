/**
 * Wizard API Service Tests
 *
 * Tests for the API service with mock HTTP client.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WizardApiService, createWizardApi, ApiError, HttpClient } from '../services/wizardApi';
import { MachineOffer, OffersApiParams } from '../types';

// ============================================================================
// Mock HTTP Client Factory
// ============================================================================

function createMockHttpClient(overrides: Partial<HttpClient> = {}): HttpClient {
  return {
    get: vi.fn().mockResolvedValue({ offers: [], count: 0 }),
    post: vi.fn().mockResolvedValue({ success: true }),
    ...overrides,
  };
}

// ============================================================================
// Tests
// ============================================================================

describe('WizardApiService', () => {
  describe('fetchOffers', () => {
    it('should call API with correct query params', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockResolvedValue({
          offers: [
            { id: 1, gpu_name: 'RTX 4090', dph_total: 0.50 },
            { id: 2, gpu_name: 'RTX 3090', dph_total: 0.30 },
          ],
          count: 2,
        }),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const params: OffersApiParams = {
        limit: 5,
        order_by: 'dph_total',
        region: 'US',
        min_gpu_ram: 16,
      };

      const offers = await api.fetchOffers(params);

      expect(mockClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/instances/offers?'),
      );
      expect(mockClient.get).toHaveBeenCalledWith(expect.stringContaining('limit=5'));
      expect(mockClient.get).toHaveBeenCalledWith(expect.stringContaining('order_by=dph_total'));
      expect(mockClient.get).toHaveBeenCalledWith(expect.stringContaining('region=US'));
      expect(mockClient.get).toHaveBeenCalledWith(expect.stringContaining('min_gpu_ram=16'));
      expect(offers).toHaveLength(2);
    });

    it('should return empty array when API returns no offers', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockResolvedValue({ offers: [], count: 0 }),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const offers = await api.fetchOffers({ limit: 5 });

      expect(offers).toEqual([]);
    });

    it('should handle API errors gracefully', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockRejectedValue(new ApiError(500, 'Internal Server Error')),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      await expect(api.fetchOffers({ limit: 5 })).rejects.toThrow(ApiError);
    });
  });

  describe('fetchOffersByTier', () => {
    it('should add labels to first 3 offers', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockResolvedValue({
          offers: [
            { id: 1, gpu_name: 'RTX 4090', dph_total: 0.50, geolocation: 'US' },
            { id: 2, gpu_name: 'RTX 3090', dph_total: 0.30, geolocation: 'US' },
            { id: 3, gpu_name: 'RTX 3080', dph_total: 0.25, geolocation: 'US' },
            { id: 4, gpu_name: 'RTX 3070', dph_total: 0.20, geolocation: 'US' },
          ],
          count: 4,
        }),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const offers = await api.fetchOffersByTier('Rapido', 'US');

      expect(offers).toHaveLength(3);
      expect(offers[0].label).toBe('Mais econômico');
      expect(offers[1].label).toBe('Melhor custo-benefício');
      expect(offers[2].label).toBe('Mais rápido');
    });

    it('should include provider and reliability info', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockResolvedValue({
          offers: [{ id: 1, gpu_name: 'RTX 4090', dph_total: 0.50, geolocation: 'US', verified: true }],
          count: 1,
        }),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const offers = await api.fetchOffersByTier('Rapido');

      expect(offers[0].provider).toBe('Vast.ai');
      expect(offers[0].reliability).toBe(99); // verified = 99%
    });
  });

  describe('fetchBalance', () => {
    it('should return credit value', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockResolvedValue({ credit: 10.50 }),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const balance = await api.fetchBalance();

      expect(balance).toBe(10.50);
    });

    it('should fallback to balance field', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockResolvedValue({ balance: 5.25 }),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const balance = await api.fetchBalance();

      expect(balance).toBe(5.25);
    });

    it('should return 0 on error', async () => {
      const mockClient = createMockHttpClient({
        get: vi.fn().mockRejectedValue(new Error('Network error')),
      });

      const api = new WizardApiService({
        baseUrl: 'http://test.com',
        httpClient: mockClient,
      });

      const balance = await api.fetchBalance();

      expect(balance).toBe(0);
    });
  });
});

describe('ApiError', () => {
  it('should have correct status and body', () => {
    const error = new ApiError(404, 'Not Found');

    expect(error.status).toBe(404);
    expect(error.body).toBe('Not Found');
    expect(error.message).toContain('404');
  });

  it('should correctly identify error types', () => {
    expect(new ApiError(401, 'Unauthorized').isUnauthorized).toBe(true);
    expect(new ApiError(404, 'Not Found').isNotFound).toBe(true);
    expect(new ApiError(500, 'Server Error').isServerError).toBe(true);
    expect(new ApiError(200, 'OK').isServerError).toBe(false);
  });
});

describe('createWizardApi', () => {
  it('should create instance with default config', () => {
    const api = createWizardApi();

    expect(api).toBeInstanceOf(WizardApiService);
  });

  it('should accept custom base URL', () => {
    const api = createWizardApi({ baseUrl: 'http://custom.api.com' });

    expect(api).toBeInstanceOf(WizardApiService);
  });

  it('should accept custom HTTP client', () => {
    const mockClient = createMockHttpClient();
    const api = createWizardApi({ httpClient: mockClient });

    expect(api).toBeInstanceOf(WizardApiService);
  });
});
