

type SessionStatus = 'active' | 'completed' | 'scheduled' | 'processing';

interface StatusBadgeProps {
    status: SessionStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    let config = {
        label: 'Unknown',
        bg: 'transparent',
        text: 'var(--text-secondary)',
        border: 'var(--border)',
        dot: undefined as string | undefined
    };

    switch (status) {
        case 'scheduled':
            config = {
                label: 'Scheduled',
                bg: 'rgba(245, 158, 11, 0.1)', // Amber
                text: '#f59e0b',
                border: 'rgba(245, 158, 11, 0.2)',
                dot: '#f59e0b'
            };
            break;
        case 'active':
            config = {
                label: 'Live',
                bg: 'rgba(16, 185, 129, 0.1)', // Green
                text: '#10b981',
                border: 'rgba(16, 185, 129, 0.2)',
                dot: '#10b981'
            };
            break;
        case 'processing':
            config = {
                label: 'Processing Report',
                bg: 'rgba(59, 130, 246, 0.1)', // Blue
                text: '#3b82f6',
                border: 'rgba(59, 130, 246, 0.2)',
                dot: '#3b82f6' // Or a spinner
            };
            break;
        case 'completed':
            config = {
                label: 'Completed',
                bg: 'rgba(156, 163, 175, 0.1)', // Gray
                text: 'var(--text-secondary)',
                border: 'rgba(156, 163, 175, 0.2)',
                dot: 'var(--text-secondary)'
            };
            break;
    }

    return (
        <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: config.bg,
            border: `1px solid ${config.border}`,
            padding: '4px 10px',
            borderRadius: '999px',
        }}>
            {status === 'processing' ? (
                <span className="material-symbols-outlined" style={{ fontSize: '12px', color: config.text, animation: 'spin 2s linear infinite' }}>sync</span>
            ) : config.dot ? (
                <div style={{ width: '6px', height: '6px', backgroundColor: config.dot, borderRadius: '50%' }} />
            ) : null}
            <span style={{ color: config.text, fontSize: '12px', fontWeight: 600, letterSpacing: '0.02em' }}>
                {config.label}
            </span>
        </div>
    );
}
