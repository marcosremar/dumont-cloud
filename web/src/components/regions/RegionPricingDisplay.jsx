import React, { useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { DollarSign, TrendingDown, TrendingUp, Loader2, AlertCircle, Clock, Cpu } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Badge,
} from '../tailadmin-ui';
import {
  fetchRegionPricing,
  selectSelectedRegion,
  selectPricingForRegion,
  selectPricingLoading,
  selectRegionById,
} from '../../store/slices/regionsSlice';

/**
 * Format a price value for display
 * @param {number} price - Price value
 * @param {string} currency - Currency code (default: USD)
 * @returns {string} Formatted price string
 */
const formatPrice = (price, currency = 'USD') => {
  if (price === null || price === undefined || isNaN(price)) {
    return '---';
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 3,
  }).format(price);
};

/**
 * Calculate the percentage difference between two prices
 * @param {number} price - Current price
 * @param {number} avgPrice - Average price to compare against
 * @returns {object} Object with percentage and whether it's below average
 */
const calculatePriceDiff = (price, avgPrice) => {
  if (!price || !avgPrice || avgPrice === 0) {
    return { percent: 0, isBelowAverage: false };
  }
  const diff = ((price - avgPrice) / avgPrice) * 100;
  return {
    percent: Math.abs(diff).toFixed(0),
    isBelowAverage: diff < 0,
  };
};

/**
 * Format a timestamp for display
 * @param {string} timestamp - ISO timestamp string
 * @returns {string} Formatted time string
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'agora';
    if (diffMins < 60) return `${diffMins}m atras`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h atras`;

    return date.toLocaleDateString('pt-BR');
  } catch {
    return '';
  }
};

/**
 * RegionPricingDisplay Component
 *
 * Displays pricing information for a selected region with:
 * - Overall price range (min, max, avg)
 * - Price breakdown by GPU type
 * - Loading and error states
 * - Cache timestamp indicator
 *
 * Can operate in controlled mode (via props) or uncontrolled mode (via Redux).
 */
const RegionPricingDisplay = ({
  regionId: propRegionId,
  pricing: propPricing,
  showBreakdown = true,
  compact = false,
  className = '',
}) => {
  const dispatch = useDispatch();

  // Redux state
  const reduxSelectedRegion = useSelector(selectSelectedRegion);
  const pricingLoading = useSelector(selectPricingLoading);

  // Use props or redux state
  const regionId = propRegionId !== undefined ? propRegionId : reduxSelectedRegion;

  // Get pricing from Redux if not provided via props
  const reduxPricing = useSelector((state) => selectPricingForRegion(state, regionId));
  const pricing = propPricing !== undefined ? propPricing : reduxPricing;

  // Get region metadata
  const regionData = useSelector((state) => selectRegionById(state, regionId));

  // Fetch pricing when region changes
  useEffect(() => {
    if (regionId && !pricing && !propPricing) {
      dispatch(fetchRegionPricing(regionId));
    }
  }, [dispatch, regionId, pricing, propPricing]);

  // Extract pricing data
  const computePrice = useMemo(() => {
    if (!pricing) return null;
    return pricing.compute_price || {
      min: pricing.min_price,
      max: pricing.max_price,
      avg: pricing.avg_price,
    };
  }, [pricing]);

  const byGpu = useMemo(() => {
    if (!pricing?.by_gpu) return [];
    return pricing.by_gpu.slice(0, 5); // Limit to 5 GPU types
  }, [pricing]);

  // Loading state
  if (pricingLoading && !pricing) {
    return (
      <Card className={`overflow-hidden ${className}`}>
        <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-500/20 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <CardTitle className="text-sm">Preco Regional</CardTitle>
              <CardDescription className="text-[10px]">Carregando...</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  // No region selected
  if (!regionId) {
    return (
      <Card className={`overflow-hidden ${className}`}>
        <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-500/20 flex items-center justify-center">
              <DollarSign className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </div>
            <div>
              <CardTitle className="text-sm">Preco Regional</CardTitle>
              <CardDescription className="text-[10px]">Selecione uma regiao</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-xs text-gray-500 text-center">
            Escolha uma regiao para ver os precos disponiveis
          </p>
        </CardContent>
      </Card>
    );
  }

  // No pricing available or error
  if (!pricing || pricing.available === false) {
    return (
      <Card className={`overflow-hidden ${className}`}>
        <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-yellow-100 dark:bg-yellow-500/20 flex items-center justify-center">
              <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
            </div>
            <div>
              <CardTitle className="text-sm">Preco Regional</CardTitle>
              <CardDescription className="text-[10px]">
                {regionData?.name || regionData?.region_name || regionId}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-xs text-gray-500 text-center">
            {pricing?.error || 'Nenhuma oferta disponivel nesta regiao'}
          </p>
        </CardContent>
      </Card>
    );
  }

  // Main pricing display
  const regionName = regionData?.name || regionData?.region_name || regionId;
  const currency = pricing.currency || 'USD';
  const offerCount = pricing.offer_count || 0;
  const fetchedAt = pricing.fetched_at;

  return (
    <Card className={`overflow-hidden ${className}`}>
      {/* Header */}
      <CardHeader className="flex-row items-center justify-between space-y-0 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-500/20 flex items-center justify-center">
            <DollarSign className="w-4 h-4 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <CardTitle className="text-sm">Preco Regional</CardTitle>
            <CardDescription className="text-[10px]">{regionName}</CardDescription>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {offerCount > 0 && (
            <span className="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-500/20 text-gray-600 dark:text-gray-400 text-[10px] font-medium">
              {offerCount} {offerCount === 1 ? 'oferta' : 'ofertas'}
            </span>
          )}
          {regionData?.is_eu && (
            <Badge variant="primary" size="sm">GDPR</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-3">
        {/* Price Overview */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          {/* Min Price */}
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <div className="flex items-center gap-1.5 mb-1">
              <TrendingDown className="w-3 h-3 text-green-500" />
              <span className="text-[10px] text-gray-400 uppercase">Min</span>
            </div>
            <p className="text-sm font-bold text-green-400">
              {formatPrice(computePrice?.min, currency)}
            </p>
            <p className="text-[10px] text-gray-500">/hora</p>
          </div>

          {/* Avg Price */}
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center gap-1.5 mb-1">
              <DollarSign className="w-3 h-3 text-gray-400" />
              <span className="text-[10px] text-gray-400 uppercase">Media</span>
            </div>
            <p className="text-sm font-bold text-white">
              {formatPrice(computePrice?.avg, currency)}
            </p>
            <p className="text-[10px] text-gray-500">/hora</p>
          </div>

          {/* Max Price */}
          <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/20">
            <div className="flex items-center gap-1.5 mb-1">
              <TrendingUp className="w-3 h-3 text-orange-500" />
              <span className="text-[10px] text-gray-400 uppercase">Max</span>
            </div>
            <p className="text-sm font-bold text-orange-400">
              {formatPrice(computePrice?.max, currency)}
            </p>
            <p className="text-[10px] text-gray-500">/hora</p>
          </div>
        </div>

        {/* GPU Breakdown */}
        {showBreakdown && byGpu.length > 0 && !compact && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700/50">
            <div className="flex items-center gap-1.5 mb-2">
              <Cpu className="w-3 h-3 text-gray-400" />
              <span className="text-[10px] text-gray-400 uppercase font-medium">Por GPU</span>
            </div>
            <div className="space-y-1.5">
              {byGpu.map((gpu, index) => {
                const priceDiff = calculatePriceDiff(gpu.avg, computePrice?.avg);
                return (
                  <div
                    key={gpu.gpu_name || index}
                    className="flex items-center justify-between p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white font-medium">{gpu.gpu_name}</span>
                      <span className="text-[10px] text-gray-500">({gpu.count} ofertas)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-white font-semibold">
                        {formatPrice(gpu.avg || gpu.min, currency)}
                      </span>
                      {priceDiff.percent > 0 && (
                        <span className={`text-[10px] font-medium ${
                          priceDiff.isBelowAverage
                            ? 'text-green-400'
                            : 'text-orange-400'
                        }`}>
                          {priceDiff.isBelowAverage ? '-' : '+'}{priceDiff.percent}%
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Cache Timestamp */}
        {fetchedAt && (
          <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700/50 flex items-center justify-between">
            <div className="flex items-center gap-1 text-[10px] text-gray-500">
              <Clock className="w-3 h-3" />
              <span>Atualizado {formatTimestamp(fetchedAt)}</span>
            </div>
            {pricingLoading && (
              <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RegionPricingDisplay;
