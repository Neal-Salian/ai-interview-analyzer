import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
    emotionTimeline: { dominant_emotion: string; confidence: number; timestamp: string }[];
}

export default function BehavioralAnalysisCard({ emotionTimeline }: Props) {
    if (!emotionTimeline || emotionTimeline.length === 0) return null;

    const chartData = emotionTimeline.map((e, i) => ({
        t: i,
        confidence: e.confidence,
        emotion: e.dominant_emotion,
    }));

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
                📈 Behavioral & Engagement Analysis
            </h3>
            
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                Emotion confidence levels over the course of the interview session.
            </p>

            <div style={{ height: '200px', width: '100%', marginTop: '0.5rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <XAxis dataKey="t" hide />
                        <YAxis domain={[0, 100]} hide />
                        <Tooltip
                            contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', fontSize: '12px', borderRadius: '8px' }}
                            formatter={(val: any, _name: string, props: any) => [`${val}%`, props.payload.emotion]}
                            labelStyle={{ display: 'none' }}
                        />
                        <Line 
                            type="monotone" 
                            dataKey="confidence" 
                            stroke="var(--accent)" 
                            strokeWidth={3} 
                            dot={false}
                            activeDot={{ r: 6, fill: 'var(--accent)', stroke: 'var(--bg)', strokeWidth: 2 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
