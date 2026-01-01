import React from 'react';
import PropTypes from 'prop-types';
import { Shield, ShieldCheck, Globe, Lock } from 'lucide-react';

/**
 * Compliance types with their display configurations
 */
const COMPLIANCE_CONFIG = {
  GDPR: {
    label: 'GDPR',
    fullLabel: 'GDPR Compliant',
    description: 'General Data Protection Regulation',
    icon: ShieldCheck,
    variant: 'primary',
    color: 'blue',
  },
  EU_GDPR: {
    label: 'GDPR',
    fullLabel: 'EU GDPR Compliant',
    description: 'European Union Data Protection',
    icon: ShieldCheck,
    variant: 'primary',
    color: 'blue',
  },
  US_ONLY: {
    label: 'US Only',
    fullLabel: 'US Data Residency',
    description: 'Data stored in United States',
    icon: Shield,
    variant: 'gray',
    color: 'gray',
  },
  APAC_ONLY: {
    label: 'APAC',
    fullLabel: 'APAC Data Residency',
    description: 'Asia-Pacific Region',
    icon: Globe,
    variant: 'gray',
    color: 'gray',
  },
  HIPAA: {
    label: 'HIPAA',
    fullLabel: 'HIPAA Eligible',
    description: 'Health Insurance Portability and Accountability Act',
    icon: Lock,
    variant: 'success',
    color: 'green',
  },
  SOC2: {
    label: 'SOC2',
    fullLabel: 'SOC 2 Compliant',
    description: 'Service Organization Control 2',
    icon: ShieldCheck,
    variant: 'success',
    color: 'green',
  },
};

/**
 * RegionComplianceBadge Component
 *
 * Displays compliance badges for regions indicating data residency
 * and regulatory compliance (e.g., GDPR for EU regions).
 *
 * Can display badges based on:
 * - is_eu flag (boolean) - Shows GDPR badge for EU regions
 * - compliance_tags array - Shows badges for each compliance tag
 * - data_residency_requirement string - Shows specific residency badge
 *
 * @example
 * // Simple EU region check
 * <RegionComplianceBadge isEu={true} />
 *
 * // With compliance tags
 * <RegionComplianceBadge complianceTags={['GDPR', 'SOC2']} />
 *
 * // Using region data directly
 * <RegionComplianceBadge region={regionData} />
 */
const RegionComplianceBadge = ({
  isEu,
  region,
  complianceTags,
  dataResidencyRequirement,
  size = 'sm',
  showIcon = true,
  showTooltip = false,
  compact = false,
  className = '',
}) => {
  // Determine compliance indicators from various sources
  const badges = [];

  // Check is_eu flag (from props or region object)
  const euFlag = isEu ?? region?.is_eu ?? false;
  if (euFlag) {
    badges.push('GDPR');
  }

  // Check compliance_tags array (from props or region object)
  const tags = complianceTags || region?.compliance_tags || [];
  tags.forEach((tag) => {
    if (tag && COMPLIANCE_CONFIG[tag] && !badges.includes(tag)) {
      badges.push(tag);
    }
  });

  // Check data_residency_requirement
  const residency = dataResidencyRequirement || region?.data_residency_requirement;
  if (residency && COMPLIANCE_CONFIG[residency] && !badges.includes(residency)) {
    badges.push(residency);
  }

  // If no badges to show, return null
  if (badges.length === 0) {
    return null;
  }

  // Custom badge rendering for better styling control
  const renderBadge = (type, index) => {
    const config = COMPLIANCE_CONFIG[type];
    if (!config) return null;

    const IconComponent = config.icon;

    // Color classes based on compliance type
    const colorClasses = {
      blue: {
        bg: 'bg-blue-100 dark:bg-blue-500/20',
        text: 'text-blue-600 dark:text-blue-400',
        border: 'border-blue-200 dark:border-blue-500/30',
      },
      green: {
        bg: 'bg-green-100 dark:bg-green-500/20',
        text: 'text-green-600 dark:text-green-400',
        border: 'border-green-200 dark:border-green-500/30',
      },
      gray: {
        bg: 'bg-gray-100 dark:bg-gray-500/20',
        text: 'text-gray-600 dark:text-gray-400',
        border: 'border-gray-200 dark:border-gray-500/30',
      },
    };

    const colors = colorClasses[config.color] || colorClasses.gray;

    // Size classes
    const sizeClasses = {
      xs: {
        padding: 'px-1.5 py-0.5',
        text: 'text-[9px]',
        icon: 'w-2.5 h-2.5',
        gap: 'gap-0.5',
      },
      sm: {
        padding: 'px-2 py-0.5',
        text: 'text-[10px]',
        icon: 'w-3 h-3',
        gap: 'gap-1',
      },
      md: {
        padding: 'px-2.5 py-1',
        text: 'text-xs',
        icon: 'w-3.5 h-3.5',
        gap: 'gap-1.5',
      },
      lg: {
        padding: 'px-3 py-1.5',
        text: 'text-sm',
        icon: 'w-4 h-4',
        gap: 'gap-2',
      },
    };

    const sizes = sizeClasses[size] || sizeClasses.sm;

    // Compact mode shows only icon
    if (compact) {
      return (
        <span
          key={`${type}-${index}`}
          className={`
            inline-flex items-center justify-center
            rounded-full
            ${colors.bg} ${colors.text}
            ${size === 'xs' ? 'w-4 h-4' : size === 'sm' ? 'w-5 h-5' : size === 'md' ? 'w-6 h-6' : 'w-7 h-7'}
          `}
          title={showTooltip ? config.fullLabel : undefined}
        >
          <IconComponent className={sizes.icon} />
        </span>
      );
    }

    return (
      <span
        key={`${type}-${index}`}
        className={`
          inline-flex items-center
          rounded-full
          font-medium
          ${sizes.padding} ${sizes.text} ${sizes.gap}
          ${colors.bg} ${colors.text}
          transition-colors
        `}
        title={showTooltip ? config.description : undefined}
      >
        {showIcon && <IconComponent className={sizes.icon} />}
        <span>{config.label}</span>
      </span>
    );
  };

  return (
    <div className={`inline-flex items-center gap-1.5 ${className}`}>
      {badges.map((badge, index) => renderBadge(badge, index))}
    </div>
  );
};

RegionComplianceBadge.propTypes = {
  /** Whether the region is in the EU (triggers GDPR badge) */
  isEu: PropTypes.bool,
  /** Region object containing is_eu, compliance_tags, etc. */
  region: PropTypes.shape({
    is_eu: PropTypes.bool,
    compliance_tags: PropTypes.arrayOf(PropTypes.string),
    data_residency_requirement: PropTypes.string,
  }),
  /** Array of compliance tags to display */
  complianceTags: PropTypes.arrayOf(PropTypes.string),
  /** Data residency requirement type */
  dataResidencyRequirement: PropTypes.oneOf(['EU_GDPR', 'US_ONLY', 'APAC_ONLY']),
  /** Badge size: 'xs', 'sm', 'md', or 'lg' */
  size: PropTypes.oneOf(['xs', 'sm', 'md', 'lg']),
  /** Whether to show the icon */
  showIcon: PropTypes.bool,
  /** Whether to show tooltip on hover */
  showTooltip: PropTypes.bool,
  /** Compact mode shows only icons */
  compact: PropTypes.bool,
  /** Additional CSS classes */
  className: PropTypes.string,
};

/**
 * Standalone GDPR badge for quick use
 * Shows the GDPR compliance indicator
 */
export const GDPRBadge = ({ size = 'sm', showIcon = true, className = '' }) => (
  <RegionComplianceBadge
    isEu={true}
    size={size}
    showIcon={showIcon}
    className={className}
  />
);

GDPRBadge.propTypes = {
  size: PropTypes.oneOf(['xs', 'sm', 'md', 'lg']),
  showIcon: PropTypes.bool,
  className: PropTypes.string,
};

/**
 * Helper function to check if a region requires GDPR compliance badge
 * @param {object} region - Region object
 * @returns {boolean} Whether region should show GDPR badge
 */
export const isGDPRRegion = (region) => {
  if (!region) return false;
  return (
    region.is_eu === true ||
    region.compliance_tags?.includes('GDPR') ||
    region.compliance_tags?.includes('EU_GDPR') ||
    region.data_residency_requirement === 'EU_GDPR'
  );
};

/**
 * Helper function to get all compliance types for a region
 * @param {object} region - Region object
 * @returns {string[]} Array of compliance type strings
 */
export const getRegionCompliance = (region) => {
  const compliance = [];
  if (!region) return compliance;

  if (region.is_eu) {
    compliance.push('GDPR');
  }

  if (region.compliance_tags) {
    region.compliance_tags.forEach((tag) => {
      if (!compliance.includes(tag)) {
        compliance.push(tag);
      }
    });
  }

  return compliance;
};

export default RegionComplianceBadge;
