import type { ReportEvaluation } from '../../types/report';

interface Props {
    evaluation: ReportEvaluation | null;
}

export default function TranscriptEvidenceCard({ evaluation }: Props) {
    if (!evaluation || !evaluation.evidence || evaluation.evidence.length === 0) return null;

    const evidenceList = evaluation.evidence.map(e => typeof e === 'string' ? e : e.quote);

    return (
        <div style={{
            background: 'var(--bg-surface)',
            borderRadius: '12px',
            border: '1px solid var(--border)',
            padding: '1.5rem',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
        }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0, paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                📝 Transcript Evidence
            </h3>
            
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                Direct quotes from the candidate supporting the recommendation.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem', maxHeight: '250px', overflowY: 'auto', paddingRight: '8px' }}>
                {evidenceList.map((quote, i) => (
                    <div key={i} style={{ 
                        fontSize: '13px', 
                        lineHeight: 1.5,
                        color: 'var(--text-secondary)', 
                        background: 'var(--bg)', 
                        padding: '12px', 
                        borderRadius: '6px',
                        borderLeft: '3px solid var(--border)',
                        fontStyle: 'italic'
                    }}>
                        "{quote}"
                    </div>
                ))}
            </div>
        </div>
    );
}
