

type SessionStatus = 'active' | 'completed' | 'scheduled' | 'processing' | 'cancelled' | 'expired';

interface StatusBadgeProps {
    status: SessionStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    let config = {
        label: 'Unknown',
        bg: 'transparent',
        text: 'var(--text-secondary)',
        border: 'var(--border)',
        dot: undefined as string | undefined,
        pulse: false
    };

    switch (status) {
        case 'scheduled':
            config = {
                label: 'Scheduled',
                bg: 'rgba(59, 130, 246, 0.1)',
                text: '#3b82f6',
                border: 'rgba(59, 130, 246, 0.2)',
                dot: '#3b82f6',
                pulse: false
            };
            break;
        case 'active':
            config = {
                label: 'In Progress',
                bg: 'rgba(245, 158, 11, 0.1)',
                text: '#d97706',
                border: 'rgba(245, 158, 11, 0.2)',
                dot: '#d97706',
                pulse: true
            };
            break;
        case 'processing':
            config = {
                label: 'Processing',
                bg: 'rgba(139, 92, 246, 0.1)',
                text: '#7c3aed',
                border: 'rgba(139, 92, 246, 0.2)',
                dot: '#7c3aed',
                pulse: false
            };
            break;
        case 'completed':
            config = {
                label: 'Completed',
                bg: 'rgba(34, 197, 94, 0.1)',
                text: '#16a34a',
                border: 'rgba(34, 197, 94, 0.2)',
                dot: '#16a34a',
                pulse: false
            };
            break;
        case 'cancelled':
            config = {
                label: 'Cancelled',
                bg: 'rgba(239, 68, 68, 0.1)',
                text: '#dc2626',
                border: 'rgba(239, 68, 68, 0.2)',
                dot: '#dc2626',
                pulse: false
            };
            break;
        case 'expired':
            config = {
                label: 'Expired',
                bg: 'rgba(156, 163, 175, 0.1)',
                text: '#6b7280',
                border: 'rgba(156, 163, 175, 0.2)',
                dot: '#6b7280',
                pulse: false
            };
            break;
    }

    return (
        <div
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: config.bg,
                border: `1px solid ${config.border}`,
                padding: '4px 12px',
                borderRadius: '999px',
                whiteSpace: 'nowrap',
            }}
            role="status"
            aria-label={`Status: ${config.label}`}
        >
            {status === 'processing' ? (
                <span
                    className="material-symbols-outlined"
                    style={{ fontSize: '12px', color: config.text, animation: 'spin 2s linear infinite' }}
                    aria-hidden="true"
                >
                    sync
                </span>
            ) : config.dot ? (
                <div
                    style={{
                        width: '7px',
                        height: '7px',
                        backgroundColor: config.dot,
                        borderRadius: '50%',
                        animation: config.pulse ? 'pulse-dot 2s ease-in-out infinite' : 'none',
                    }}
                    aria-hidden="true"
                />
            ) : null}
            <span style={{ color: config.text, fontSize: '12px', fontWeight: 600, letterSpacing: '0.02em' }}>
                {config.label}
            </span>
        </div>
    );
}
