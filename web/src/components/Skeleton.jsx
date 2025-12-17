import './Skeleton.css'

// Skeleton base com shimmer effect
export function Skeleton({ className = '', width, height, borderRadius = '4px' }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width: width || '100%',
        height: height || '20px',
        borderRadius
      }}
    />
  )
}

// Skeleton para texto (uma linha)
export function SkeletonText({ width = '100%', lines = 1 }) {
  return (
    <div className="skeleton-text-container">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 && lines > 1 ? '70%' : width}
          height="14px"
        />
      ))}
    </div>
  )
}

// Skeleton para card de oferta (Dashboard)
export function SkeletonOfferCard() {
  return (
    <div className="skeleton-offer-card">
      <div className="skeleton-offer-header">
        <Skeleton width="120px" height="24px" />
        <Skeleton width="80px" height="20px" />
      </div>
      <div className="skeleton-offer-body">
        <div className="skeleton-offer-row">
          <Skeleton width="60px" height="16px" />
          <Skeleton width="100px" height="16px" />
        </div>
        <div className="skeleton-offer-row">
          <Skeleton width="80px" height="16px" />
          <Skeleton width="60px" height="16px" />
        </div>
        <div className="skeleton-offer-row">
          <Skeleton width="70px" height="16px" />
          <Skeleton width="90px" height="16px" />
        </div>
      </div>
      <div className="skeleton-offer-footer">
        <Skeleton width="100%" height="36px" borderRadius="6px" />
      </div>
    </div>
  )
}

// Skeleton para card de máquina (Machines)
export function SkeletonMachineCard() {
  return (
    <div className="skeleton-machine-card">
      <div className="skeleton-machine-header">
        <Skeleton width="150px" height="24px" />
        <Skeleton width="70px" height="22px" borderRadius="12px" />
      </div>
      <div className="skeleton-machine-tags">
        <Skeleton width="100px" height="24px" borderRadius="4px" />
        <Skeleton width="60px" height="24px" borderRadius="4px" />
        <Skeleton width="80px" height="24px" borderRadius="4px" />
      </div>
      <div className="skeleton-machine-stats">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="skeleton-stat">
            <Skeleton width="40px" height="28px" />
            <Skeleton width="30px" height="12px" />
          </div>
        ))}
      </div>
      <div className="skeleton-machine-buttons">
        <Skeleton width="100%" height="36px" borderRadius="6px" />
        <Skeleton width="100%" height="36px" borderRadius="6px" />
      </div>
    </div>
  )
}

// Container para múltiplos skeletons
export function SkeletonList({ count = 3, type = 'offer' }) {
  const Component = type === 'offer' ? SkeletonOfferCard : SkeletonMachineCard

  return (
    <div className={`skeleton-list skeleton-list-${type}`}>
      {Array.from({ length: count }).map((_, i) => (
        <Component key={i} />
      ))}
    </div>
  )
}

export default Skeleton
