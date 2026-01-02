import { BarChart3 } from 'lucide-react'
import DashboardReports from '../components/DashboardReports'

export default function MetricsHub() {
  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-3">
              <BarChart3 className="w-6 h-6 text-brand-400" />
              Relatórios
            </h1>
            <p className="page-subtitle">Visão geral de economia, máquinas e confiabilidade</p>
          </div>
        </div>
      </div>

      {/* 3 Relatórios Principais */}
      <DashboardReports />
    </div>
  )
}
