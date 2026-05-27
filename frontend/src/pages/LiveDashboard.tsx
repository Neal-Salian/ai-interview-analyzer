import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Navbar from '../components/Navbar'
import type { EmotionFrame, TranscriptChunk, SuggestedQuestion, WSMessage } from '../types'

const EMOTION_COLOR: Record<string, string> = {
    happy: '#34d399',
    neutral: '#60a5fa',
    sad: '#818cf8',
    angry: '#f87171',
    fear: '#fbbf24',
    surprise: '#f472b6',
    disgust: '#a78bfa',
}

// Mock questions since questions pipeline isn't built yet
const MOCK_QUESTIONS: SuggestedQuestion[] = [
    { id: '1', question_text: 'Can you walk me through a specific example of a challenging project you led?', triggered_by: 'leadership experience', was_asked: false, created_at: '' },
    { id: '2', question_text: 'How did you handle the technical debt you mentioned?', triggered_by: 'technical debt', was_asked: false, created_at: '' },
    { id: '3', question_text: 'What metrics did you use to measure success in that role?', triggered_by: 'success metrics', was_asked: false, created_at: '' },
]

export default function LiveDashboard() {
    const { id: sessionId } = useParams<{ id: string }>()
    const [emotions, setEmotions] = useState<EmotionFrame[]>([])
    const [transcripts, setTranscripts] = useState<TranscriptChunk[]>([])
    const [questions, setQuestions] = useState<SuggestedQuestion[]>(MOCK_QUESTIONS)
    const [currentEmotion, setCurrentEmotion] = useState<string>('—')
    const [currentConfidence, setCurrentConfidence] = useState<number>(0)
    const [connected, setConnected] = useState(false)
    const transcriptRef = useRef<HTMLDivElement>(null)
    const wsRef = useRef<WebSocket | null>(null)

    // Chart data — last 20 emotion readings as confidence over time
    const chartData = emotions.slice(-20).map((e, i) => ({
        t: i,
        confidence: Math.round(e.confidence),
        emotion: e.dominant_emotion,
    }))

    useEffect(() => {
        if (!sessionId) return

        const ws = new WebSocket(`ws://localhost:8001/ws/live/${sessionId}`)
        wsRef.current = ws

        ws.onopen = () => setConnected(true)
        ws.onclose = () => setConnected(false)

        ws.onmessage = (event) => {
            const msg: WSMessage = JSON.parse(event.data)

            if (msg.type === 'ping') return

            if (msg.type === 'history') {
                if (msg.emotions) setEmotions(msg.emotions)
                if (msg.transcripts) setTranscripts(msg.transcripts)
                if (msg.emotions?.length) {
                    const last = msg.emotions[msg.emotions.length - 1]
                    setCurrentEmotion(last.dominant_emotion)
                    setCurrentConfidence(last.confidence)
                }
            }

            if (msg.type === 'emotion' && msg.dominant_emotion) {
                const frame: EmotionFrame = {
                    dominant_emotion: msg.dominant_emotion,
                    confidence: msg.confidence ?? 0,
                    timestamp: msg.timestamp ?? new Date().toISOString(),
                }
                setEmotions(prev => [...prev, frame])
                setCurrentEmotion(msg.dominant_emotion)
                setCurrentConfidence(msg.confidence ?? 0)
            }

            if (msg.type === 'transcript' && msg.text) {
                const chunk: TranscriptChunk = {
                    text: msg.text,
                    timestamp: msg.timestamp ?? new Date().toISOString(),
                }
                setTranscripts(prev => [...prev, chunk])
            }
        }

        return () => ws.close()
    }, [sessionId])

    // Auto-scroll transcript
    useEffect(() => {
        if (transcriptRef.current) {
            transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight
        }
    }, [transcripts])

    const markAsked = (id: string) => {
        setQuestions(prev => prev.map(q => q.id === id ? { ...q, was_asked: true } : q))
    }

    const emotionColor = EMOTION_COLOR[currentEmotion] ?? 'var(--text-secondary)'

    return (
        <div>
            <Navbar />
            <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto 1fr', gap: '16px', maxWidth: '1400px', margin: '0 auto' }}>

                {/* Header */}
                <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <h1 style={{ fontSize: '20px', fontWeight: 600 }}>Live Interview</h1>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Session {sessionId?.slice(0, 8)}...</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{
                            width: '8px', height: '8px', borderRadius: '50%',
                            background: connected ? 'var(--success)' : 'var(--danger)',
                            display: 'inline-block',
                            boxShadow: connected ? '0 0 6px var(--success)' : 'none',
                        }} />
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                            {connected ? 'Live' : 'Disconnected'}
                        </span>
                    </div>
                </div>

                {/* Left column — emotion + chart */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                    {/* Current emotion card */}
                    <div style={cardStyle}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>
                            Current Emotion
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                fontSize: '40px', fontWeight: 700, color: emotionColor,
                                textTransform: 'capitalize',
                            }}>
                                {currentEmotion}
                            </div>
                            <div style={{
                                fontSize: '13px', color: 'var(--text-secondary)',
                                background: 'var(--bg)',
                                padding: '4px 12px',
                                borderRadius: '20px',
                            }}>
                                {currentConfidence.toFixed(1)}% confidence
                            </div>
                        </div>
                    </div>

                    {/* Emotion chart */}
                    <div style={{ ...cardStyle, flex: 1 }}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '16px' }}>
                            Confidence Over Time
                        </div>
                        {chartData.length === 0 ? (
                            <div style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', paddingTop: '40px' }}>
                                Waiting for stream...
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height={200}>
                                <LineChart data={chartData}>
                                    <XAxis dataKey="t" hide />
                                    <YAxis domain={[0, 100]} hide />
                                    <Tooltip
                                        contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '12px' }}
                                        formatter={(val, _name, props) => [`${val}%`, props.payload.emotion]}
                                    />
                                    <Line type="monotone" dataKey="confidence" stroke="var(--accent)" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </div>

                    {/* Suggested questions */}
                    <div style={cardStyle}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>
                            Suggested Questions
                            <span style={{ marginLeft: '8px', color: 'var(--text-secondary)', fontStyle: 'italic', textTransform: 'none', fontSize: '11px' }}>(mock — pipeline coming soon)</span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {questions.map(q => (
                                <div key={q.id} style={{
                                    background: 'var(--bg)',
                                    border: `1px solid ${q.was_asked ? 'var(--border)' : 'var(--accent)'}`,
                                    borderRadius: 'var(--radius-sm)',
                                    padding: '12px',
                                    opacity: q.was_asked ? 0.5 : 1,
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'flex-start',
                                    gap: '12px',
                                }}>
                                    <span style={{ fontSize: '13px', lineHeight: 1.5 }}>{q.question_text}</span>
                                    {!q.was_asked && (
                                        <button
                                            onClick={() => markAsked(q.id)}
                                            style={{
                                                flexShrink: 0,
                                                background: 'var(--accent-bg)',
                                                color: 'var(--accent)',
                                                border: '1px solid var(--accent)',
                                                borderRadius: 'var(--radius-sm)',
                                                padding: '4px 10px',
                                                fontSize: '12px',
                                                whiteSpace: 'nowrap',
                                            }}
                                        >
                                            Mark asked
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right column — transcript */}
                <div style={cardStyle}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>
                        Live Transcript
                    </div>
                    <div
                        ref={transcriptRef}
                        style={{
                            height: '600px',
                            overflowY: 'auto',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px',
                        }}
                    >
                        {transcripts.length === 0 && (
                            <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                                Transcript will appear here as the candidate speaks...
                            </p>
                        )}
                        {transcripts.map((chunk, i) => (
                            <div key={i} style={{
                                background: 'var(--bg)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-sm)',
                                padding: '12px',
                            }}>
                                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                                    {new Date(chunk.timestamp).toLocaleTimeString()}
                                </div>
                                <div style={{ fontSize: '14px', lineHeight: 1.6 }}>{chunk.text}</div>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    )
}

const cardStyle: React.CSSProperties = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '20px',
}