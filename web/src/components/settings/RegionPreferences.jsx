import React, { useState, useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Globe, MapPin, Shield, Check, AlertCircle, X, Plus, Loader2 } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Label,
  Badge,
  Alert,
  Button,
} from '../tailadmin-ui';
import {
  fetchRegions,
  fetchUserRegionPreferences,
  updateUserRegionPreferences,
  selectRegions,
  selectRegionPreferences,
  selectPreferencesLoading,
  selectRegionsLoading,
  selectEuRegions,
  selectRegionsError,
} from '../../store/slices/regionsSlice';

/**
 * Data residency requirement options
 */
const DATA_RESIDENCY_OPTIONS = [
  { value: 'none', label: 'Sem restricao', description: 'Qualquer regiao disponivel' },
  { value: 'EU_GDPR', label: 'GDPR (Europa)', description: 'Apenas regioes com conformidade GDPR' },
  { value: 'US_ONLY', label: 'Apenas EUA', description: 'Dados permanecem nos Estados Unidos' },
  { value: 'APAC_ONLY', label: 'Apenas APAC', description: 'Dados na regiao Asia-Pacifico' },
];

/**
 * RegionPreferences Component
 *
 * Allows users to configure their region preferences including:
 * - Preferred primary region
 * - Fallback regions (up to 5)
 * - Data residency requirements (GDPR, etc.)
 */
const RegionPreferences = ({ className = '' }) => {
  const dispatch = useDispatch();

  // Redux state
  const regions = useSelector(selectRegions);
  const preferences = useSelector(selectRegionPreferences);
  const preferencesLoading = useSelector(selectPreferencesLoading);
  const regionsLoading = useSelector(selectRegionsLoading);
  const euRegions = useSelector(selectEuRegions);
  const error = useSelector(selectRegionsError);

  // Local form state
  const [localPreferences, setLocalPreferences] = useState({
    preferred_region: null,
    fallback_regions: [],
    data_residency_requirement: 'none',
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load data on mount
  useEffect(() => {
    if (regions.length === 0 && !regionsLoading) {
      dispatch(fetchRegions());
    }
    dispatch(fetchUserRegionPreferences());
  }, [dispatch, regions.length, regionsLoading]);

  // Sync local state with redux preferences
  useEffect(() => {
    if (preferences) {
      setLocalPreferences({
        preferred_region: preferences.preferred_region || null,
        fallback_regions: preferences.fallback_regions || [],
        data_residency_requirement: preferences.data_residency_requirement || 'none',
      });
      setHasChanges(false);
    }
  }, [preferences]);

  // Get available regions filtered by residency requirement
  const availableRegions = useMemo(() => {
    if (localPreferences.data_residency_requirement === 'EU_GDPR') {
      return euRegions;
    }
    if (localPreferences.data_residency_requirement === 'US_ONLY') {
      return regions.filter(r => r.country_code === 'US');
    }
    if (localPreferences.data_residency_requirement === 'APAC_ONLY') {
      return regions.filter(r =>
        ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW', 'AU', 'NZ'].includes(r.country_code)
      );
    }
    return regions;
  }, [regions, euRegions, localPreferences.data_residency_requirement]);

  // Get region display name
  const getRegionName = (regionId) => {
    const region = regions.find(r => r.id === regionId || r.region_id === regionId);
    return region?.name || region?.region_name || regionId || 'Desconhecido';
  };

  // Get region data
  const getRegionData = (regionId) => {
    return regions.find(r => r.id === regionId || r.region_id === regionId);
  };

  // Handle preferred region change
  const handlePreferredRegionChange = (value) => {
    const newValue = value === 'none' ? null : value;
    setLocalPreferences(prev => ({
      ...prev,
      preferred_region: newValue,
      // Remove from fallback if it was there
      fallback_regions: prev.fallback_regions.filter(r => r !== newValue),
    }));
    setHasChanges(true);
    setSaveSuccess(false);
  };

  // Handle data residency change
  const handleResidencyChange = (value) => {
    setLocalPreferences(prev => {
      // When changing residency, validate current selections
      const newAvailableIds = getFilteredRegionIds(value);
      return {
        ...prev,
        data_residency_requirement: value,
        // Clear selections that are no longer valid
        preferred_region: newAvailableIds.includes(prev.preferred_region)
          ? prev.preferred_region
          : null,
        fallback_regions: prev.fallback_regions.filter(r => newAvailableIds.includes(r)),
      };
    });
    setHasChanges(true);
    setSaveSuccess(false);
  };

  // Get region IDs filtered by residency requirement
  const getFilteredRegionIds = (residency) => {
    let filtered = regions;
    if (residency === 'EU_GDPR') {
      filtered = euRegions;
    } else if (residency === 'US_ONLY') {
      filtered = regions.filter(r => r.country_code === 'US');
    } else if (residency === 'APAC_ONLY') {
      filtered = regions.filter(r =>
        ['JP', 'CN', 'KR', 'SG', 'IN', 'TH', 'VN', 'ID', 'MY', 'PH', 'TW', 'AU', 'NZ'].includes(r.country_code)
      );
    }
    return filtered.map(r => r.id || r.region_id);
  };

  // Add fallback region
  const handleAddFallback = (value) => {
    if (!value || value === 'none' || localPreferences.fallback_regions.length >= 5) {
      return;
    }
    if (value !== localPreferences.preferred_region &&
        !localPreferences.fallback_regions.includes(value)) {
      setLocalPreferences(prev => ({
        ...prev,
        fallback_regions: [...prev.fallback_regions, value],
      }));
      setHasChanges(true);
      setSaveSuccess(false);
    }
  };

  // Remove fallback region
  const handleRemoveFallback = (regionId) => {
    setLocalPreferences(prev => ({
      ...prev,
      fallback_regions: prev.fallback_regions.filter(r => r !== regionId),
    }));
    setHasChanges(true);
    setSaveSuccess(false);
  };

  // Save preferences
  const handleSave = async () => {
    const payload = {
      preferred_region: localPreferences.preferred_region,
      fallback_regions: localPreferences.fallback_regions,
      data_residency_requirement: localPreferences.data_residency_requirement === 'none'
        ? null
        : localPreferences.data_residency_requirement,
    };

    const result = await dispatch(updateUserRegionPreferences(payload));
    if (!result.error) {
      setHasChanges(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    }
  };

  // Get regions available for fallback selection (excluding preferred and already selected)
  const fallbackOptions = useMemo(() => {
    return availableRegions.filter(r => {
      const regionId = r.id || r.region_id;
      return regionId !== localPreferences.preferred_region &&
             !localPreferences.fallback_regions.includes(regionId);
    });
  }, [availableRegions, localPreferences.preferred_region, localPreferences.fallback_regions]);

  const isLoading = regionsLoading && regions.length === 0;

  if (isLoading) {
    return (
      <Card className={`overflow-hidden ${className}`}>
        <CardHeader className="flex-row items-center justify-between space-y-0 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-brand-500/10">
              <Globe className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <CardTitle className="text-lg font-semibold text-white">Preferencias de Regiao</CardTitle>
              <CardDescription className="text-sm text-gray-500">Carregando...</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`overflow-hidden border-white/10 bg-dark-surface-card ${className}`}>
      {/* Header */}
      <CardHeader className="flex-row items-center justify-between space-y-0 py-4 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-brand-500/10">
            <Globe className="w-5 h-5 text-brand-400" />
          </div>
          <div>
            <CardTitle className="text-lg font-semibold text-white">Preferencias de Regiao</CardTitle>
            <CardDescription className="text-sm text-gray-500">
              Configure sua regiao preferida e opcoes de failover
            </CardDescription>
          </div>
        </div>
        {hasChanges && (
          <Badge variant="warning" size="sm">Nao salvo</Badge>
        )}
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {/* Error Message */}
        {error && (
          <Alert variant="error" icon={AlertCircle}>
            {error}
          </Alert>
        )}

        {/* Success Message */}
        {saveSuccess && (
          <Alert variant="success" icon={Check}>
            Preferencias salvas com sucesso!
          </Alert>
        )}

        {/* Data Residency Requirement */}
        <div className="space-y-2">
          <Label className="text-gray-300 flex items-center gap-2">
            <Shield className="w-4 h-4 text-blue-400" />
            Requisito de Residencia de Dados
          </Label>
          <p className="text-xs text-gray-500 mb-2">
            Restrinja suas instancias a regioes especificas para conformidade regulatoria.
          </p>
          <Select
            value={localPreferences.data_residency_requirement}
            onValueChange={handleResidencyChange}
          >
            <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-gray-800">
              <SelectValue placeholder="Selecione um requisito" />
            </SelectTrigger>
            <SelectContent>
              {DATA_RESIDENCY_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>
                  <div className="flex flex-col">
                    <span>{opt.label}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[10px] text-gray-500 mt-1">
            {DATA_RESIDENCY_OPTIONS.find(o => o.value === localPreferences.data_residency_requirement)?.description}
          </p>
        </div>

        {/* Preferred Region */}
        <div className="space-y-2">
          <Label className="text-gray-300 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-brand-400" />
            Regiao Preferida
          </Label>
          <p className="text-xs text-gray-500 mb-2">
            Regiao primaria para provisionamento de instancias GPU.
          </p>
          <Select
            value={localPreferences.preferred_region || 'none'}
            onValueChange={handlePreferredRegionChange}
          >
            <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-gray-800">
              <SelectValue placeholder="Selecione uma regiao" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Automatico (melhor disponibilidade)</SelectItem>
              {availableRegions.map(region => {
                const regionId = region.id || region.region_id;
                return (
                  <SelectItem key={regionId} value={regionId}>
                    <div className="flex items-center gap-2">
                      <span>{region.name || region.region_name || regionId}</span>
                      {region.is_eu && (
                        <Shield className="w-3 h-3 text-blue-500" />
                      )}
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
          {localPreferences.preferred_region && (
            <div className="mt-2 p-2 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-xs text-white font-medium">
                {getRegionName(localPreferences.preferred_region)}
              </span>
              {getRegionData(localPreferences.preferred_region)?.is_eu && (
                <Badge variant="primary" size="sm">GDPR</Badge>
              )}
            </div>
          )}
        </div>

        {/* Fallback Regions */}
        <div className="space-y-2">
          <Label className="text-gray-300 flex items-center gap-2">
            <Globe className="w-4 h-4 text-gray-400" />
            Regioes de Fallback
            <span className="text-[10px] text-gray-500 font-normal">
              ({localPreferences.fallback_regions.length}/5)
            </span>
          </Label>
          <p className="text-xs text-gray-500 mb-2">
            Regioes alternativas caso a regiao preferida nao esteja disponivel.
          </p>

          {/* Current Fallback Regions */}
          {localPreferences.fallback_regions.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {localPreferences.fallback_regions.map((regionId, index) => {
                const regionData = getRegionData(regionId);
                return (
                  <div
                    key={regionId}
                    className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/10"
                  >
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-gray-700 flex items-center justify-center text-[10px] text-gray-400 font-medium">
                        {index + 1}
                      </span>
                      <span className="text-sm text-white">{getRegionName(regionId)}</span>
                      {regionData?.is_eu && (
                        <Shield className="w-3 h-3 text-blue-500" />
                      )}
                    </div>
                    <button
                      onClick={() => handleRemoveFallback(regionId)}
                      className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Add Fallback Button */}
          {localPreferences.fallback_regions.length < 5 && fallbackOptions.length > 0 && (
            <Select
              value="none"
              onValueChange={handleAddFallback}
            >
              <SelectTrigger className="bg-gray-100 dark:bg-dark-surface-secondary border-gray-200 dark:border-gray-800 border-dashed">
                <div className="flex items-center gap-2 text-gray-400">
                  <Plus className="w-4 h-4" />
                  <span>Adicionar regiao de fallback</span>
                </div>
              </SelectTrigger>
              <SelectContent>
                {fallbackOptions.map(region => {
                  const regionId = region.id || region.region_id;
                  return (
                    <SelectItem key={regionId} value={regionId}>
                      <div className="flex items-center gap-2">
                        <span>{region.name || region.region_name || regionId}</span>
                        {region.is_eu && (
                          <Shield className="w-3 h-3 text-blue-500" />
                        )}
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          )}

          {localPreferences.fallback_regions.length === 0 && (
            <p className="text-[10px] text-gray-500 italic">
              Nenhuma regiao de fallback configurada
            </p>
          )}
        </div>

        {/* Info Box */}
        <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-gray-300">
              <p className="font-medium text-blue-400 mb-1">Como funciona o failover?</p>
              <p className="text-gray-400">
                Quando sua regiao preferida nao tiver disponibilidade, o sistema tentara automaticamente
                as regioes de fallback na ordem configurada. Isso garante maior disponibilidade para
                suas cargas de trabalho.
              </p>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="pt-4 border-t border-gray-700">
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!hasChanges || preferencesLoading}
            loading={preferencesLoading}
            className="w-full sm:w-auto"
          >
            <Check className="w-4 h-4 mr-2" />
            Salvar Preferencias
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default RegionPreferences;
