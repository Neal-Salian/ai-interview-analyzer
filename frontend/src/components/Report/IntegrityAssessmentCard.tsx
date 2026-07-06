import type { ReportIntegrityIndicators } from '../../types/report';

interface Props {
    integrityData: ReportIntegrityIndicators | { events: { event_type: string; severity: string; details: string; timestamp: string }[] };
}

export default function IntegrityAssessmentCard({ integrityData }: Props) {
    const events = integrityData?.events || [];

    return (
        <div style={{
            background: 'var(--bg-surface)',
            borderRadius: '12px',
            border: '1px solid var(--border)',
            padding: '1.5rem',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0 }}>
                    🛡️ Integrity Assessment
                </h3>
                {events.length === 0 ? (
                    <span style={{ fontSize: '12px', color: 'var(--success)', background: 'rgba(52, 211, 153, 0.1)', padding: '4px 10px', borderRadius: '12px', fontWeight: 600 }}>
                        All Clear
                    </span>
                ) : (
                    <span style={{ fontSize: '12px', color: 'var(--danger)', background: 'rgba(248, 113, 113, 0.1)', padding: '4px 10px', borderRadius: '12px', fontWeight: 600 }}>
                        {events.length} Flags Detected
                    </span>
                )}
            </div>

            {events.length === 0 ? (
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', padding: '1rem 0' }}>
                    No integrity issues or suspicious activities detected during the session.
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {events.map((event, i) => {
                        const isHighSeverity = event.severity.toLowerCase() === 'high';
                        return (
                            <div key={i} style={{ 
                                display: 'flex', 
                                gap: '1rem', 
                                padding: '12px', 
                                background: 'var(--bg)', 
                                borderRadius: '8px',
                                borderLeft: `3px solid ${isHighSeverity ? 'var(--danger)' : 'var(--warning)'}`
                            }}>
                                <span className="material-symbols-outlined" style={{ 
                                    color: isHighSeverity ? 'var(--danger)' : 'var(--warning)', 
                                    fontSize: '20px' 
                                }}>
                                    {isHighSeverity ? 'error' : 'warning'}
                                </span>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                        <span style={{ fontSize: '13px', fontWeight: 600, textTransform: 'capitalize', color: 'var(--text-primary)' }}>
                                            {event.event_type.replace(/_/g, ' ')}
                                        </span>
                                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                                            {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                                        {event.details}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
