import React from 'react';
import { useTheme } from '../context/ThemeContext';

export default function DumontLogo({ size = 64, className = '' }) {
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={className}
        >
            <path
                d="M26 16.5C26 13.46 23.54 11 20.5 11C20.17 11 19.85 11.03 19.54 11.08C18.44 8.17 15.62 6 12.32 6C8.11 6 4.68 9.36 4.53 13.55C2.47 14.17 1 16.06 1 18.32C1 21.16 3.34 23.5 6.18 23.5H25C28.04 23.5 30.5 21.04 30.5 18C30.5 15.35 28.62 13.13 26.12 12.58"
                fill="none"
                stroke={isDark ? "#10b981" : "#059669"}
                strokeWidth="2"
            />
            <path
                d="M10 11V20H13C15.76 20 18 17.76 18 15C18 12.24 15.76 10 13 10H10V11Z"
                fill={isDark ? "#1a1f1a" : "#ffffff"}
                stroke={isDark ? "#10b981" : "#059669"}
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
            <circle cx="22" cy="15" r="1.5" fill={isDark ? "#10b981" : "#059669"} />
            <circle cx="24" cy="18" r="1" fill={isDark ? "#34d399" : "#10b981"} />
            <defs>
                <linearGradient id="cloudGradientLogoDark" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#1a1f1a" />
                    <stop offset="1" stopColor="#131713" />
                </linearGradient>
                <linearGradient id="cloudGradientLogoLight" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#059669" />
                    <stop offset="1" stopColor="#10b981" />
                </linearGradient>
                <linearGradient id="cloudStrokeLogo" x1="1" y1="6" x2="30.5" y2="23.5" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#10b981" />
                    <stop offset="1" stopColor="#34d399" />
                </linearGradient>
            </defs>
        </svg>
    );
}
