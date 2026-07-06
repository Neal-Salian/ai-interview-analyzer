import type { ReportEvaluation } from '../../types/report';

interface Props {
    evaluation: ReportEvaluation | null;
}

export default function StrengthsConcernsCard({ evaluation }: Props) {
    if (!evaluation) return null;

    const strengths = evaluation.strengths || [];
    const concerns = evaluation.improvement_areas || [];

    if (strengths.length === 0 && concerns.length === 0) return null;

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
            <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0, paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                ✨ Key Strengths & Areas of Concern
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                {/* Strengths */}
                <div>
                    <h4 style={{ fontSize: '14px', color: '#34d399', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>check_circle</span>
                        Strengths
                    </h4>
                    {strengths.length > 0 ? (
                        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {strengths.map((str, i) => (
                                <li key={i} style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-secondary)', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                    <span style={{ color: '#34d399', fontSize: '16px', lineHeight: 1 }}>•</span>
                                    {str}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No specific strengths noted.</div>
                    )}
                </div>

                {/* Concerns */}
                <div>
                    <h4 style={{ fontSize: '14px', color: '#fbbf24', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>warning</span>
                        Areas of Concern
                    </h4>
                    {concerns.length > 0 ? (
                        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {concerns.map((conc, i) => (
                                <li key={i} style={{ fontSize: '13px', lineHeight: 1.5, color: 'var(--text-secondary)', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                    <span style={{ color: '#fbbf24', fontSize: '16px', lineHeight: 1 }}>•</span>
                                    {conc}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No major concerns noted.</div>
                    )}
                </div>
            </div>
        </div>
    );
}
