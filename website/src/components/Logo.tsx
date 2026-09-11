/**
 * The MediaGrab mark: a download arrow caught by a pair of brackets.
 *
 * Inline SVG rather than the PNG so it stays crisp at every size and picks up
 * a unique gradient id per instance (two marks on one page would otherwise
 * share, and clash over, the same defs).
 */
import { useId } from 'react';

interface LogoProps {
    size?: number;
    className?: string;
    /** Draw only the glyph, for placing on an existing coloured surface. */
    bare?: boolean;
}

export default function Logo({ size = 40, className = '', bare = false }: LogoProps) {
    const uid = useId().replace(/:/g, '');
    const tile = `mg-tile-${uid}`;
    const sheen = `mg-sheen-${uid}`;

    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 96 96"
            className={className}
            role="img"
            aria-label="MediaGrab"
        >
            <defs>
                <linearGradient id={tile} x1="0" y1="0" x2="96" y2="96" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#60a5fa" />
                    <stop offset="0.5" stopColor="#3b82f6" />
                    <stop offset="1" stopColor="#8b5cf6" />
                </linearGradient>
                <linearGradient id={sheen} x1="0" y1="0" x2="0" y2="96" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#ffffff" stopOpacity="0.22" />
                    <stop offset="0.55" stopColor="#ffffff" stopOpacity="0" />
                </linearGradient>
            </defs>

            {!bare && (
                <>
                    <rect width="96" height="96" rx="22" fill={`url(#${tile})`} />
                    <rect width="96" height="96" rx="22" fill={`url(#${sheen})`} />
                </>
            )}

            <rect x="40.5" y="18" width="15" height="27" rx="7.5" fill="#ffffff" />
            <path d="M27 40 H69 L48 64 Z" fill="#ffffff" stroke="#ffffff" strokeWidth="5" strokeLinejoin="round" />

            <g fill="none" stroke="#ffffff" strokeWidth="7.5" strokeLinecap="round" opacity="0.92">
                <path d="M21 57 v11 a8 8 0 0 0 8 8 h7" />
                <path d="M75 57 v11 a8 8 0 0 1 -8 8 h-7" />
            </g>
        </svg>
    );
}
