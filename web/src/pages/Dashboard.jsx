import React, { useState } from 'react';
import { ComposableMap, Geographies, Geography, Marker } from 'react-simple-maps';

const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Mapeamento de regiões para países
const regionCountries = {
  'EUA': ['USA'],
  'Europa': ['GBR', 'FRA', 'DEU', 'ITA', 'ESP', 'PRT', 'NLD', 'BEL', 'CHE', 'AUT', 'POL', 'CZE', 'SVK', 'HUN', 'ROU', 'BGR', 'GRC', 'SWE', 'NOR', 'DNK', 'FIN', 'IRL'],
  'Asia': ['CHN', 'JPN', 'KOR', 'IND', 'THA', 'VNM', 'SGP', 'MYS', 'IDN', 'PHL', 'PAK', 'BGD'],
  'AmericaDoSul': ['BRA', 'ARG', 'CHL', 'COL', 'PER', 'VEN', 'ECU', 'BOL', 'PRY', 'URY']
};

// Marcadores de servidores
const markers = [
  { name: 'EUA', coordinates: [-95, 37], region: 'EUA' },
  { name: 'Europa', coordinates: [10, 50], region: 'Europa' },
  { name: 'Asia', coordinates: [105, 35], region: 'Asia' },
  { name: 'Brasil', coordinates: [-52, -15], region: 'AmericaDoSul' }
];

// World Map com React Simple Maps - Agrupado por Continente
const WorldMap = ({ activeRegion, onRegionClick }) => {
  const getRegionForCountry = (countryCode) => {
    for (const [region, countries] of Object.entries(regionCountries)) {
      if (countries.includes(countryCode)) {
        return region;
      }
    }
    return null;
  };

  const getCountryFill = (geo) => {
    const countryCode = geo.id;
    const region = getRegionForCountry(countryCode);

    if (activeRegion === 'Global') {
      // Modo Global - todas as regiões em verde brilhante
      return region ? '#4ade80' : '#1a1f1a';
    }

    if (region === activeRegion) {
      // Região ativa - verde brilhante destacado
      return '#4ade80';
    }

    if (region) {
      // Outras regiões - cinza escuro
      return '#1a1f1a';
    }

    // Países fora das regiões - muito escuros
    return '#0f120f';
  };

  return (
    <div className="relative w-full h-full overflow-hidden rounded-lg" style={{ backgroundColor: '#1c211c' }}>
      {/* Dot grid pattern */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
        <defs>
          <pattern id="dotGrid" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
            <circle cx="4" cy="4" r="0.8" fill="#2a352a" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dotGrid)" />
      </svg>

      <div className="relative w-full h-full" style={{ zIndex: 1 }}>
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            scale: 100,
            center: [0, 20]
          }}
          width={800}
          height={400}
          style={{ width: '100%', height: '100%' }}
        >
          {/* Renderizar países agrupados por região */}
          <Geographies geography={geoUrl}>
            {({ geographies }) => {
              // Agrupar países por região
              const regions = {
                EUA: [],
                Europa: [],
                Asia: [],
                AmericaDoSul: []
              };

              geographies.forEach((geo) => {
                const region = getRegionForCountry(geo.id);
                if (region && regions[region]) {
                  regions[region].push(geo);
                }
              });

              return (
                <>
                  {/* Renderizar cada região como um grupo clicável */}
                  {Object.entries(regions).map(([regionName, geos]) => {
                    const isActiveRegion = regionName === activeRegion;
                    const regionFill = isActiveRegion || activeRegion === 'Global' ? '#4ade80' : '#1a1f1a';
                    const regionHover = '#22c55e';

                    return (
                      <g key={regionName} onClick={() => onRegionClick(regionName)} style={{ cursor: 'pointer' }}>
                        {geos.map((geo) => (
                          <Geography
                            key={geo.rsmKey}
                            geography={geo}
                            fill={regionFill}
                            stroke="#0a0d0a"
                            strokeWidth={0.3}
                            style={{
                              default: {
                                outline: 'none',
                                fill: regionFill
                              },
                              hover: {
                                fill: regionHover,
                                outline: 'none',
                                stroke: '#0a0d0a'
                              },
                              pressed: {
                                fill: '#4ade80',
                                outline: 'none'
                              }
                            }}
                          />
                        ))}
                      </g>
                    );
                  })}

                  {/* Países que não pertencem a nenhuma região */}
                  {geographies
                    .filter((geo) => !getRegionForCountry(geo.id))
                    .map((geo) => (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill="#0f120f"
                        stroke="#1c211c"
                        strokeWidth={0.5}
                        style={{
                          default: { outline: 'none', pointerEvents: 'none' },
                          hover: { fill: '#0f120f' },
                          pressed: { fill: '#0f120f' }
                        }}
                      />
                    ))}
                </>
              );
            }}
          </Geographies>

          {/* Markers animados */}
          {markers.map(({ name, coordinates, region }) => {
            const isActive = activeRegion === region || activeRegion === 'Global';
            return isActive ? (
              <Marker key={name} coordinates={coordinates}>
                {/* Círculo pulsante */}
                <circle r={8} fill="#22c55e" opacity={0.25}>
                  <animate attributeName="r" values="8;12;8" dur="1.5s" repeatCount="indefinite" />
                </circle>
                {/* Círculo central */}
                <circle r={3} fill="#4ade80" />
              </Marker>
            ) : null;
          })}
        </ComposableMap>
      </div>
    </div>
  );
};

// Speed bars component
const SpeedBars = ({ level, color }) => {
  const colors = { gray: '#6b7280', yellow: '#eab308', orange: '#ea580c', green: '#4ade80' };
  return (
    <div className="flex items-end gap-px">
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          style={{
            width: '3px',
            height: `${4 + i * 3}px`,
            backgroundColor: i <= level ? colors[color] : '#374151',
            borderRadius: '1px'
          }}
        />
      ))}
    </div>
  );
};

// Tier Card
const TierCard = ({ tier, isSelected, onClick }) => (
  <button
    onClick={onClick}
    className={`flex flex-col p-3 md:p-4 rounded-lg border text-left transition-all ${
      isSelected ? 'border-green-500/50 bg-[#1a2418]' : 'border-gray-700/30 bg-[#161a16] hover:border-gray-600'
    }`}
    style={{ minHeight: '140px' }}
  >
    <div className="flex items-center justify-between mb-2">
      <span className="text-white font-semibold text-xs md:text-sm tracking-tight">{tier.name}</span>
      <SpeedBars level={tier.level} color={tier.color} />
    </div>
    <div className="text-green-400 text-[10px] md:text-xs font-mono font-medium tracking-tight">{tier.speed}</div>
    <div className="text-gray-400 text-[9px] md:text-[10px] mb-1.5">{tier.time}</div>
    <div className="text-gray-500 text-[9px] md:text-[10px] leading-relaxed">{tier.line1}</div>
    <div className="text-gray-500 text-[9px] md:text-[10px] leading-relaxed mb-1.5">{tier.line2}</div>
    <div className="mt-auto pt-2 border-t border-gray-700/30">
      <p className="text-gray-500 text-[8px] md:text-[9px] leading-relaxed">{tier.description}</p>
    </div>
  </button>
);

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('EUA');
  const [selectedTier, setSelectedTier] = useState('Rapido');
  const [selectedGPU, setSelectedGPU] = useState('Qualquer GPU');
  const [hotStart, setHotStart] = useState(true);

  const tabs = ['EUA', 'Europa', 'Ásia', 'América do Sul', 'Global'];
  const tabIds = ['EUA', 'Europa', 'Asia', 'AmericaDoSul', 'Global'];

  const tiers = [
    { name: 'Lento', level: 1, color: 'gray', speed: '100-250 Mbps', time: '~5 min', line1: 'Sem storage', line2: '~6 Máquinas', description: 'Trade-off: é + custo da transferência(s). Interro. e/rradas.' },
    { name: 'Medio', level: 2, color: 'yellow', speed: '50K-1000 mbps', time: '~1-2 Min', line1: 'Sem Disk es', line2: '5 mik Ativos', description: 'Irede oifter ve enste de tempo de reitmeri Lo chamando conectado.' },
    { name: 'Rapido', level: 3, color: 'orange', speed: '900+-1100 k/ops', time: '~30s', line1: '40,00 ~31,90ft.', line2: '5 mautres', description: 'Trade-off - o custo de tempo d aternmada qibagos arveles' },
    { name: 'Ultra', level: 4, color: 'green', speed: '4000-AE50+ k/ops', time: '~1s', line1: '15, (9.0.1) Atm', line2: '1% mefyr bes.', description: 'Trade-off 5: a caufe de. Tempo veremos fos 1finadow.' }
  ];

  return (
    <div className="min-h-screen flex items-center justify-center p-4 md:p-6 lg:p-8" style={{ backgroundColor: '#0e110e', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        .font-mono { font-family: 'JetBrains Mono', monospace; }
      `}</style>

      <div className="w-full max-w-md md:max-w-2xl lg:max-w-4xl xl:max-w-5xl rounded-xl overflow-hidden border border-gray-800/50 shadow-2xl" style={{ backgroundColor: '#131713' }}>

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center px-4 md:px-6 py-3 md:py-4 border-b border-gray-800/50 gap-3 sm:gap-0">
          <div className="flex items-center gap-2 mr-4">
            <div className="w-6 h-6 md:w-7 md:h-7 rounded-md bg-green-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 md:w-5 md:h-5 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <span className="text-white text-base md:text-lg font-semibold tracking-tight">Deploy 2 Migrate</span>
          </div>

          <div className="flex flex-wrap gap-1 sm:ml-auto">
            {tabs.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tabIds[i])}
                className={`px-3 py-1.5 md:px-4 md:py-2 text-xs md:text-sm font-medium transition-all rounded ${
                  activeTab === tabIds[i]
                    ? 'text-green-400 bg-green-500/10'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 md:p-6 lg:p-8">
          {/* Region + GPU */}
          <div className="flex flex-col md:flex-row gap-4 md:gap-6 mb-4 md:mb-6">
            <div className="flex-1">
              <div className="text-gray-400 text-xs md:text-sm font-medium mb-2 tracking-wide">Region</div>
              <div className="h-40 md:h-48 lg:h-56 rounded-lg overflow-hidden border border-gray-800/40">
                <WorldMap activeRegion={activeTab} onRegionClick={setActiveTab} />
              </div>
            </div>
            <div className="w-full md:w-48 lg:w-56">
              <div className="text-gray-400 text-xs md:text-sm font-medium mb-2 tracking-wide">GPU</div>
              <select
                value={selectedGPU}
                onChange={(e) => setSelectedGPU(e.target.value)}
                className="w-full px-4 py-3 md:py-3.5 rounded-lg text-xs md:text-sm text-white border border-gray-700/40 focus:outline-none focus:border-green-500 font-medium"
                style={{ backgroundColor: '#1a1f1a' }}
              >
                <option>Qualquer GPU</option>
                <option>RTX 4090</option>
                <option>RTX 4080</option>
                <option>A100</option>
                <option>H100</option>
              </select>
            </div>
          </div>

          {/* Label */}
          <div className="text-gray-500 text-xs md:text-sm mb-3 md:mb-4 tracking-wide">Velocidade & Custo (Cuelo vs. Tempo de Restauração$s)</div>

          {/* Tier cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3 mb-4 md:mb-6">
            {tiers.map((tier) => (
              <TierCard key={tier.name} tier={tier} isSelected={selectedTier === tier.name} onClick={() => setSelectedTier(tier.name)} />
            ))}
          </div>

          {/* Slider */}
          <div className="relative h-2 md:h-2.5 rounded-full mb-5 md:mb-6 mx-1" style={{ backgroundColor: '#252a25' }}>
            <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: '75%', background: 'linear-gradient(to right, #4b5563, #ca8a04, #ea580c, #22c55e)' }} />
            <div className="absolute top-1/2 -translate-y-1/2 w-4 h-4 md:w-5 md:h-5 bg-white rounded-full border-2 border-green-500 shadow-lg" style={{ left: 'calc(75% - 8px)' }} />
          </div>

          {/* Hot Start */}
          <div className="rounded-xl p-4 md:p-5 mb-5 md:mb-6 border border-gray-800/30" style={{ backgroundColor: '#1a1f1a' }}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-orange-400 text-lg md:text-xl">🔥</span>
                <div>
                  <div className="text-white text-xs md:text-sm font-semibold tracking-tight">Hot Start ✓ Migrate</div>
                  <div className="text-gray-500 text-[10px] md:text-xs">Inooc fepacu, asbo usbe diégone</div>
                </div>
              </div>
              <button
                onClick={() => setHotStart(!hotStart)}
                className={`relative w-11 h-6 md:w-12 md:h-7 rounded-full transition-colors ${hotStart ? 'bg-green-500' : 'bg-gray-600'}`}
              >
                <div className={`absolute top-0.5 w-5 h-5 md:w-6 md:h-6 bg-white rounded-full transition-transform shadow-md ${hotStart ? 'translate-x-5 md:translate-x-5' : 'translate-x-0.5'}`} />
              </button>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex justify-around gap-3 md:gap-6 mb-5 md:mb-6">
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 rounded-full border border-gray-700 flex items-center justify-center mb-2 hover:border-green-500/50 transition-colors cursor-pointer">
                <svg className="w-6 h-6 md:w-7 md:h-7 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <span className="text-white text-[10px] md:text-xs font-semibold">Start Fast</span>
              <span className="text-green-400 text-[8px] md:text-[10px] font-medium">Hlaowwclve</span>
              <span className="text-gray-500 text-[8px] md:text-[10px] text-center">Attila.A.d. 1rofi Cirgatevo</span>
            </div>
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 rounded-full border border-gray-700 flex items-center justify-center mb-2 hover:border-blue-500/50 transition-colors cursor-pointer">
                <svg className="w-6 h-6 md:w-7 md:h-7 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </div>
              <span className="text-white text-[10px] md:text-xs font-semibold">Transfer</span>
            </div>
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 rounded-full border border-gray-700 flex items-center justify-center mb-2 hover:border-yellow-500/50 transition-colors cursor-pointer">
                <svg className="w-6 h-6 md:w-7 md:h-7 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <span className="text-white text-[10px] md:text-xs font-semibold">Continue Slow</span>
              <span className="text-yellow-400 text-[8px] md:text-[10px] font-medium">(Cheap)</span>
              <span className="text-gray-500 text-[8px] md:text-[10px] text-center">Crualuartiest Oneaa</span>
            </div>
          </div>

          {/* CTA Button */}
          <button className="w-full py-3 md:py-4 lg:py-5 rounded-lg text-white text-sm md:text-base font-semibold tracking-wide transition-all bg-gradient-to-r from-green-600 to-green-500 hover:from-green-500 hover:to-green-400 shadow-lg shadow-green-500/20">
            Criar Maquina ✓ Restore
          </button>
        </div>
      </div>
    </div>
  );
}
