import type { ReportEvaluation } from '../../types/report';

interface Props {
    evaluation: ReportEvaluation | null;
}

export default function RecommendationCard({ evaluation }: Props) {
    if (!evaluation || !evaluation.overall_assessment) return null;

    const recommendation = evaluation.overall_assessment;

    const recLabel = recommendation.split('.')[0] || recommendation;

    let recColor = 'var(--text-secondary)';
    let recBg = 'var(--bg-surface)';
    if (recLabel.toLowerCase().includes('strongly recommend')) {
        recColor = '#10b981'; // green-500
        recBg = 'rgba(16, 185, 129, 0.05)';
    } else if (recLabel.toLowerCase().includes('recommend')) {
        recColor = '#34d399'; // green-400
        recBg = 'rgba(52, 211, 153, 0.05)';
    } else if (recLabel.toLowerCase().includes('consider')) {
        recColor = '#fbbf24'; // amber-400
        recBg = 'rgba(251, 191, 36, 0.05)';
    } else if (recLabel.toLowerCase().includes('not')) {
        recColor = '#f87171'; // red-400
        recBg = 'rgba(248, 113, 113, 0.05)';
    }

    return (
        <div style={{
            background: recBg,
            borderRadius: '12px',
            border: `1px solid ${recColor}40`,
            padding: '2rem',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
        }}>
            <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: recColor, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="material-symbols-outlined" style={{ fontSize: '24px' }}>gavel</span>
                Final Recommendation
            </h3>
            
            <p style={{ fontSize: '14px', lineHeight: 1.6, color: 'var(--text-primary)', margin: 0, whiteSpace: 'pre-wrap' }}>
                {recommendation}
            </p>
        </div>
    );
}
