export function SkeletonCard({ className = '', style = {}, children }: { className?: string, style?: React.CSSProperties, children?: React.ReactNode }) {
    return (
        <div className={`skeleton-card ${className}`} style={{
            padding: '1.5rem',
            ...style
        }}>
            {children}
        </div>
    );
}

export function SkeletonText({ width = '100%', height = '16px', style = {} }: { width?: string, height?: string, style?: React.CSSProperties }) {
    return (
        <div className="skeleton-shimmer" style={{
            width,
            height,
            ...style
        }} />
    );
}

export function SessionCardSkeleton() {
    return (
        <div className="skeleton-card" aria-hidden="true">
            {/* Header skeleton */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '20px 20px 0 20px' }}>
                <div style={{ display: 'flex', gap: '14px', flex: 1 }}>
                    <div className="skeleton-shimmer" style={{ width: '44px', height: '44px', borderRadius: '50%', minWidth: '44px' }} />
                    <div style={{ flex: 1 }}>
                        <div className="skeleton-shimmer" style={{ width: '65%', height: '18px', marginBottom: '8px' }} />
                        <div className="skeleton-shimmer" style={{ width: '45%', height: '14px' }} />
                    </div>
                </div>
                <div className="skeleton-shimmer" style={{ width: '90px', height: '26px', borderRadius: '999px' }} />
            </div>

            {/* Body skeleton — meta grid */}
            <div style={{ padding: '16px 20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                {[1, 2, 3, 4].map((i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div className="skeleton-shimmer" style={{ width: '32px', height: '32px', borderRadius: '8px', minWidth: '32px' }} />
                        <div style={{ flex: 1 }}>
                            <div className="skeleton-shimmer" style={{ width: '50%', height: '10px', marginBottom: '4px' }} />
                            <div className="skeleton-shimmer" style={{ width: '80%', height: '14px' }} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Footer skeleton */}
            <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border)' }}>
                <div className="skeleton-shimmer" style={{ width: '100%', height: '38px', borderRadius: '6px' }} />
            </div>
        </div>
    );
}

export function StatCardSkeleton() {
    return (
        <div className="skeleton-stat-card" aria-hidden="true">
            <div className="skeleton-shimmer" style={{ width: '44px', height: '44px', borderRadius: '12px', minWidth: '44px' }} />
            <div>
                <div className="skeleton-shimmer" style={{ width: '48px', height: '24px', marginBottom: '6px' }} />
                <div className="skeleton-shimmer" style={{ width: '80px', height: '14px' }} />
            </div>
        </div>
    );
}
