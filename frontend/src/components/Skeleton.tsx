export function SkeletonCard({ className = '', style = {}, children }: { className?: string, style?: React.CSSProperties, children?: React.ReactNode }) {
    return (
        <div className={`animate-pulse ${className}`} style={{
            backgroundColor: 'var(--bg-surface)',
            borderRadius: '10px',
            border: '1px solid var(--border)',
            padding: '1.5rem',
            ...style
        }}>
            {children}
        </div>
    );
}

export function SkeletonText({ width = '100%', height = '16px', className = '', style = {} }: { width?: string, height?: string, className?: string, style?: React.CSSProperties }) {
    return (
        <div className={`animate-pulse ${className}`} style={{
            width,
            height,
            backgroundColor: 'var(--border)',
            borderRadius: '4px',
            ...style
        }} />
    );
}

export function SessionCardSkeleton() {
    return (
        <div className="animate-pulse" style={{
            backgroundColor: 'var(--bg-surface)',
            borderRadius: '10px',
            border: '1px solid var(--border)',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ width: '140px', height: '22px', backgroundColor: 'var(--border)', borderRadius: '4px', marginBottom: '8px' }}></div>
                    <div style={{ width: '100px', height: '16px', backgroundColor: 'var(--bg)', borderRadius: '4px', marginBottom: '6px' }}></div>
                    <div style={{ width: '80px', height: '16px', backgroundColor: 'var(--bg)', borderRadius: '4px' }}></div>
                </div>
                <div style={{ width: '80px', height: '24px', backgroundColor: 'var(--border)', borderRadius: '12px' }}></div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: 'auto' }}>
                <div style={{ width: '100%', height: '60px', backgroundColor: 'var(--bg)', borderRadius: '6px' }}></div>
                <div style={{ width: '100%', height: '60px', backgroundColor: 'var(--bg)', borderRadius: '6px' }}></div>
            </div>
            <div style={{ marginTop: 'auto', paddingTop: '1.25rem', borderTop: '1px solid var(--border)' }}>
                <div style={{ width: '100%', height: '36px', backgroundColor: 'var(--border)', borderRadius: '6px' }}></div>
            </div>
        </div>
    );
}
