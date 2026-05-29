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
// TODO: remove when WebSocket is live with real session
const MOCK_EMOTIONS: EmotionFrame[] = [
    { dominant_emotion: 'neutral', confidence: 72.5, timestamp: new Date(Date.now() - 120000).toISOString() },
    { dominant_emotion: 'happy', confidence: 85.3, timestamp: new Date(Date.now() - 90000).toISOString() },
    { dominant_emotion: 'neutral', confidence: 68.1, timestamp: new Date(Date.now() - 60000).toISOString() },
    { dominant_emotion: 'surprise', confidence: 78.9, timestamp: new Date(Date.now() - 45000).toISOString() },
    { dominant_emotion: 'happy', confidence: 91.2, timestamp: new Date(Date.now() - 30000).toISOString() },
    { dominant_emotion: 'neutral', confidence: 74.4, timestamp: new Date(Date.now() - 15000).toISOString() },
]

const MOCK_TRANSCRIPTS: TranscriptChunk[] = [
    { text: 'I have been working with Python for over five years, primarily in backend development and distributed systems.', timestamp: new Date(Date.now() - 110000).toISOString() },
    { text: 'In my last role I led a team of three engineers to migrate our monolith to a microservices architecture.', timestamp: new Date(Date.now() - 80000).toISOString() },
    { text: 'The biggest challenge was maintaining uptime during the migration — we used a strangler fig pattern to do it incrementally.', timestamp: new Date(Date.now() - 50000).toISOString() },
    { text: 'We reduced deployment time from two hours down to eight minutes and cut incident rate by about forty percent.', timestamp: new Date(Date.now() - 20000).toISOString() },
]

export default function LiveDashboard() {
    const { id: sessionId } = useParams<{ id: string }>()
    const [emotions, setEmotions] = useState<EmotionFrame[]>([])
    const [transcripts, setTranscripts] = useState<TranscriptChunk[]>([])
    const [questions, setQuestions] = useState<SuggestedQuestion[]>([])
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
        ws.onclose = () => {
            setConnected(false)
            // Load mock data if WebSocket closed with no real data
            setEmotions(prev => prev.length === 0 ? MOCK_EMOTIONS : prev)
            setTranscripts(prev => prev.length === 0 ? MOCK_TRANSCRIPTS : prev)
            if (MOCK_EMOTIONS.length) {
                const last = MOCK_EMOTIONS[MOCK_EMOTIONS.length - 1]
                setCurrentEmotion(last.dominant_emotion)
                setCurrentConfidence(last.confidence)
            }
        }

        ws.onmessage = (event) => {
            const msg: WSMessage = JSON.parse(event.data)

            if (msg.type === 'ping') return

            if (msg.type === 'history') {
                if (msg.emotions) setEmotions(msg.emotions)
                if (msg.transcripts) setTranscripts(msg.transcripts)
                if (msg.questions) setQuestions(msg.questions)
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
            if (msg.type === 'question' && msg.question) {
                setQuestions(prev => {
                    const exists = prev.find(q => q.id === msg.question!.id)
                    if (exists) return prev
                    return [...prev, msg.question!]
                })
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

    const markAsked = async (id: string) => {
        setQuestions(prev => prev.map(q => q.id === id ? { ...q, was_asked: true } : q))
        try {
            await fetch(`/api/questions/${id}/asked`, { method: 'PATCH' })
        } catch (e) {
            console.error('Failed to mark question as asked', e)
        }
    }

    const emotionColor = EMOTION_COLOR[currentEmotion] ?? 'var(--text-secondary)'

    return (
        <div>
            <Navbar />
            <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto 1fr', gap: '16px', maxWidth: '1400px', margin: '0 auto' }}>

                {/* Header */}
                <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <h1 style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em' }}>Live Interview</h1>
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
                        <div style={{ fontSize: '14px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontWeight: 700, fontFamily: 'var(--font-heading)', }}>
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
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px', fontFamily: 'var(--font-heading)' }}>
                            Emotions Over Time
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
                                    <Line type="monotone" dataKey="confidence" stroke="#0055ff" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </div>

                    {/* Suggested questions */}
                    <div style={cardStyle}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: 'var(--font-heading)' }}>
                            Suggested Questions
                            <span style={{ marginLeft: '8px', color: 'var(--text-secondary)', fontStyle: 'italic', textTransform: 'none', fontSize: '11px' }}></span>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {questions.map(q => (
                                <div key={q.id} style={{
                                    background: 'var(--bg)',
                                    border: `2px solid ${q.was_asked ? 'var(--border)' : 'var(--accent)'}`,
                                    borderRadius: 'var(--radius)',
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
                                                background: 'var(--accent)',
                                                color: '#ffffff',
                                                border: 'none',
                                                borderRadius: 'var(--radius)',
                                                fontFamily: 'var(--font-heading)',
                                                fontWeight: 500,
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
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: 'var(--font-heading)' }}>
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
                                borderRadius: 'var(--radius)',
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
    border: '2px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px',
}