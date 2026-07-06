

const EMOTION_COLOR: Record<string, string> = {
    happy: '#34d399',
    neutral: '#60a5fa',
    sad: '#818cf8',
    angry: '#f87171',
    fear: '#fbbf24',
    surprise: '#f472b6',
    disgust: '#a78bfa',
};

interface Props {
    sentiment: { label: string; score: number };
    confidence: number;
    emotionBreakdown: Record<string, number>;
    transcriptChunks: number;
    wordCount: number;
}

export default function InterviewAnalysisCard({ sentiment, confidence, emotionBreakdown, transcriptChunks, wordCount }: Props) {
    const sentimentPositive = sentiment?.label === 'POSITIVE';
    const confidencePercent = Math.round(confidence);
    const emotionEntries = Object.entries(emotionBreakdown).sort((a, b) => b[1] - a[1]);
    const dominantEmotion = emotionEntries[0]?.[0] ?? 'neutral';

    const circumference = 251.2; // 2 * pi * 40
    const dashOffset = circumference - (circumference * (confidencePercent / 100));

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
                📊 Interview Analysis Overview
            </h3>

            {/* Sentiment Summary */}
            <div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Overall Communication Sentiment</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                        fontSize: '24px', fontWeight: 700,
                        color: sentimentPositive ? 'var(--success)' : 'var(--danger)',
                        textTransform: 'capitalize'
                    }}>
                        {sentiment?.label ?? '—'}
                    </div>
                    {sentiment?.score && (
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'var(--bg)', padding: '4px 10px', borderRadius: '12px' }}>
                            {Math.round(sentiment.score * 100)}% confidence
                        </div>
                    )}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                    Based on {transcriptChunks} transcript chunks ({wordCount} words)
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1.5rem', alignItems: 'center' }}>
                {/* Confidence Ring */}
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Avg. Confidence</div>
                    <div style={{ position: 'relative', width: '96px', height: '96px', margin: '0 auto' }}>
                        <svg width="96" height="96" viewBox="0 0 96 96">
                            <circle cx="48" cy="48" r="40" fill="none" stroke="var(--border)" strokeWidth="8" />
                            <circle
                                cx="48" cy="48" r="40"
                                fill="none"
                                stroke={EMOTION_COLOR[dominantEmotion] ?? 'var(--accent)'}
                                strokeWidth="8"
                                strokeDasharray={circumference}
                                strokeDashoffset={dashOffset}
                                strokeLinecap="round"
                                transform="rotate(-90 48 48)"
                            />
                        </svg>
                        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', fontWeight: 700 }}>
                            {confidencePercent}%
                        </div>
                    </div>
                </div>

                {/* Emotion Breakdown */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Emotion Breakdown</div>
                    {emotionEntries.slice(0, 4).map(([emotion, pct]) => (
                        <div key={emotion}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '4px' }}>
                                <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{emotion}</span>
                                <span style={{ color: EMOTION_COLOR[emotion] ?? 'var(--text-secondary)', fontWeight: 600 }}>{pct}%</span>
                            </div>
                            <div style={{ width: '100%', height: '4px', backgroundColor: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                                <div style={{ width: `${pct}%`, height: '100%', backgroundColor: EMOTION_COLOR[emotion] ?? 'var(--accent)' }} />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
