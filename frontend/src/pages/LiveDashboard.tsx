import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Navbar from '../components/Navbar'
import type { EmotionFrame, TranscriptChunk, SuggestedQuestion, WSMessage } from '../types'
import client from '../api/client'
import PageTransition from '../components/PageTransition';
import { SkeletonCard, SkeletonText } from '../components/Skeleton';
import { useRuntimeStatus } from '../hooks/useRuntimeStatus';

const EMOTION_COLOR: Record<string, string> = {
    happy: '#34d399',
    neutral: '#60a5fa',
    sad: '#818cf8',
    angry: '#f87171',
    fear: '#fbbf24',
    surprise: '#f472b6',
    disgust: '#a78bfa',
}

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
    const [currentAttention, setCurrentAttention] = useState<string>('—')
    const [currentSentiment, setCurrentSentiment] = useState<string>('—')
    const [integrityAlerts, setIntegrityAlerts] = useState<{event_type: string, severity: string, details: string, timestamp: string}[]>([])
    const [connected, setConnected] = useState(false)
    const [sessionInfo, setSessionInfo] = useState<{ candidate: string, job: string, status?: string, zoom_join_url?: string, meeting_provider?: string, zoom_meeting_id?: string } | null>(null)
    
    // Enrollment / Tracking
    const [enrollmentStatus, setEnrollmentStatus] = useState<'idle' | 'enrolling' | 'failed' | 'success' | 'timeout'>('idle')
    const [trackingStatus, setTrackingStatus] = useState<'not_enrolled' | 'tracking' | 'lost' | 'reverifying' | 'session_ended'>('not_enrolled')
    const [enrollmentReason, setEnrollmentReason] = useState<string>('')
    const [toasts, setToasts] = useState<{id: string, message: string, type: 'info'|'success'|'warning'|'error'}[]>([])
    const lastToastRef = useRef<Record<string, number>>({})

    const showToast = (message: string, type: 'info'|'success'|'warning'|'error' = 'info') => {
        const now = Date.now()
        if (lastToastRef.current[message] && now - lastToastRef.current[message] < 5000) return
        lastToastRef.current[message] = now
        const id = Math.random().toString(36).substring(7)
        setToasts(prev => [...prev, { id, message, type }])
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
    }

    const { aiRuntime, aiRuntimeDetails, retryInitialization } = useRuntimeStatus(sessionId, sessionInfo?.status === 'active')
    const transcriptRef = useRef<HTMLDivElement>(null)
    const wsRef = useRef<WebSocket | null>(null)

    const chartData = emotions.slice(-20).map((e, i) => ({
        t: i,
        confidence: Math.round(e.confidence),
        emotion: e.dominant_emotion,
    }))

    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)

    // Fetch session info
    useEffect(() => {
        if (!sessionId) return
        Promise.all([
            client.get(`/sessions/${sessionId}`),
            new Promise(resolve => setTimeout(resolve, 500))
        ])
            .then(([res]) => {
                if (res.data.status === 'completed') {
                    navigate(`/sessions/${sessionId}/report`, { replace: true })
                    return
                }
                setSessionInfo({
                    candidate: res.data.candidate || 'Unknown',
                    job: res.data.job || 'No role specified',
                    status: res.data.status,
                    zoom_join_url: res.data.zoom_join_url,
                    meeting_provider: res.data.meeting_provider,
                    zoom_meeting_id: res.data.zoom_meeting_id
                })
            })
            .catch(err => console.error('Failed to fetch session info', err))
            .finally(() => setLoading(false))
    }, [sessionId])

    const handleRetryInitialization = async () => {
        await retryInitialization();
    }

    const handleStartAnalysis = async () => {
        try {
            await client.post(`/sessions/${sessionId}/start-analysis`)
        } catch (e) {
            console.error('Failed to start analysis', e)
        }
    }

    // WebSocket
    useEffect(() => {
        if (!sessionId) return

        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8001'
        const token = localStorage.getItem('token')
        const ws = new WebSocket(`${wsUrl}/ws/live/${sessionId}?token=${token}`)
        wsRef.current = ws

        ws.onopen = () => setConnected(true)
        ws.onclose = () => {
            setConnected(false)
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

            if (msg.type === 'attention' && msg.direction) {
                setCurrentAttention(msg.direction)
            }

            if (msg.type === 'sentiment' && msg.label) {
                setCurrentSentiment(msg.label)
            }

            if (msg.type === 'integrity_alert' && msg.event_type) {
                setIntegrityAlerts(prev => [...prev, {
                    event_type: msg.event_type!,
                    severity: msg.severity || 'warning',
                    details: msg.details || '',
                    timestamp: new Date().toISOString()
                }].slice(-5)) // Keep last 5
            }

            if (msg.type === 'enrollment_status' && msg.status) {
                setEnrollmentStatus(msg.status as any)
                if (msg.reason) setEnrollmentReason(msg.reason)
                
                if (msg.status === 'success' || msg.status === 'enrolled') {
                    showToast('Candidate enrolled successfully.', 'success')
                    setEnrollmentStatus('idle') // temporary workflow ends
                } else if (msg.status === 'failed') {
                    const reasonStr = msg.reason === 'multiple_faces_detected' ? 'Multiple faces detected' : msg.reason
                    showToast(`Enrollment failed: ${reasonStr}`, 'error')
                } else if (msg.status === 'timeout') {
                    showToast('Enrollment timed out.', 'warning')
                } else if (msg.status === 'enrolling') {
                    showToast('Enrollment started...', 'info')
                }
            }

            if (msg.type === 'tracking_status' && msg.status) {
                setTrackingStatus(msg.status as any)
                
                if (msg.status === 'lost') {
                    showToast('Candidate tracking lost.', 'warning')
                } else if (msg.status === 'tracking') {
                    showToast('Candidate tracking active.', 'success')
                }
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
            await client.patch(`/questions/${id}/asked`)
        } catch (e) {
            console.error('Failed to mark question as asked', e)
        }
    }

    const emotionColor = EMOTION_COLOR[currentEmotion] ?? 'var(--text-secondary)'

    if (loading) {
        return (
            <div>
                <Navbar />
                <PageTransition>
                    <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto 1fr', gap: '16px', maxWidth: '1400px', margin: '0 auto' }}>
                        <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div>
                                <SkeletonText width="200px" height="24px" style={{ marginBottom: '8px' }} />
                                <SkeletonText width="150px" height="16px" />
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <SkeletonText width="80px" height="20px" />
                            </div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <SkeletonCard style={{ height: '180px' }} />
                            <SkeletonCard style={{ height: '250px', flex: 1 }} />
                            <SkeletonCard style={{ height: '200px' }} />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <SkeletonCard style={{ height: '600px', flex: 1 }} />
                        </div>
                    </div>
                </PageTransition>
            </div>
        )
    }

    return (
        <div>
            <Navbar />
            <PageTransition>
            <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto 1fr', gap: '16px', maxWidth: '1400px', margin: '0 auto' }}>

                {/* Header */}
                <div style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <button onClick={() => navigate('/sessions')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 600, padding: '0 0 8px 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>arrow_back</span>
                            Back to Sessions
                        </button>
                        <h1 style={{ fontSize: '20px', fontWeight: 700, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em' }}>
                            {sessionInfo?.candidate ?? 'Live Interview'}
                        </h1>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                            {sessionInfo?.job ?? `Session ${sessionId?.slice(0, 8)}...`}
                        </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {sessionInfo?.status === 'active' && (
                            <button
                                onClick={async () => {
                                    try {
                                        await client.patch(`/sessions/${sessionId}/end`)
                                        navigate('/sessions')
                                    } catch (e) {
                                        console.error('Failed to end session', e)
                                    }
                                }}
                                style={{
                                    marginRight: '12px',
                                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                                    backgroundColor: 'transparent', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '0.4rem 0.8rem',
                                    borderRadius: '6px', fontWeight: 600, cursor: 'pointer', fontSize: '12px'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>stop_circle</span>
                                End Session
                            </button>
                        )}
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

                {sessionInfo?.status === 'scheduled' ? (
                    <div style={{ gridColumn: '1 / -1', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '64px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: '48px', color: 'var(--text-secondary)', marginBottom: '16px' }}>event</span>
                        <h2 style={{ fontSize: '24px', fontWeight: 600, marginBottom: '8px' }}>Interview has not started.</h2>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>Wait for the scheduled time to begin the session.</p>
                        {sessionInfo.zoom_join_url && (
                            <a href={sessionInfo.zoom_join_url} target="_blank" rel="noopener noreferrer" style={{ padding: '12px 24px', background: 'linear-gradient(135deg, #2d8cff 0%, #0b5fcc 100%)', color: '#fff', borderRadius: '8px', textDecoration: 'none', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span className="material-symbols-outlined">videocam</span>
                                Join Meeting
                            </a>
                        )}
                    </div>
                ) : (
                    <>
                        {/* Meeting Live & AI Runtime Status Bar */}
                        <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '16px', marginBottom: '8px' }}>
                            {sessionInfo?.meeting_provider === 'mock' ? (
                                <div style={{ flex: 1, padding: '16px', background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.2)', borderRadius: 'var(--radius)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontWeight: 600, marginBottom: '4px' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>developer_mode</span>
                                        Development Mode (OBS)
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
                                        <span style={{ color: 'var(--text-secondary)' }}>Server:</span>
                                        <code style={{ background: 'var(--bg)', padding: '2px 6px', borderRadius: '4px', cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText('rtmp://localhost:1935/stream')}>rtmp://localhost:1935/stream</code>
                                    </div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px' }}>
                                        <span style={{ color: 'var(--text-secondary)' }}>Stream Key:</span>
                                        <code style={{ background: 'var(--bg)', padding: '2px 6px', borderRadius: '4px', cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText(sessionInfo.zoom_meeting_id || '')}>{sessionInfo.zoom_meeting_id}</code>
                                    </div>
                                </div>
                            ) : (
                                <div style={{ flex: 1, padding: '16px', background: 'rgba(45, 140, 255, 0.05)', border: '1px solid rgba(45, 140, 255, 0.2)', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    <span className="material-symbols-outlined" style={{ color: '#2d8cff', fontSize: '24px' }}>videocam</span>
                                    <div>
                                        <div style={{ fontWeight: 600, color: '#2d8cff' }}>Meeting Live</div>
                                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Audio & Video streams connected</div>
                                    </div>
                                </div>
                            )}
                            
                            <div style={{ flex: 2, padding: '16px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    {aiRuntime === 'not_initialized' && <><span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)' }}>power_settings_new</span><div><div style={{ fontWeight: 600 }}>AI Engine Not Initialized</div></div></>}
                                    {aiRuntime === 'initializing' && <><span className="material-symbols-outlined" style={{ color: '#f59e0b', animation: 'spin 2s linear infinite' }}>sync</span><div><div style={{ fontWeight: 600, color: '#f59e0b' }}>AI Engine Initializing... {aiRuntimeDetails.progress}%</div><div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{aiRuntimeDetails.current_step || 'Loading interview engine...'}</div></div></>}
                                    {aiRuntime === 'ready' && <><span className="material-symbols-outlined" style={{ color: 'var(--success)' }}>check_circle</span><div><div style={{ fontWeight: 600, color: 'var(--success)' }}>AI Engine Ready {aiRuntimeDetails.duration_ms ? `(${aiRuntimeDetails.duration_ms}ms)` : ''}</div><div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Ready for analysis</div></div></>}
                                    {aiRuntime === 'starting_rtmp' && <><span className="material-symbols-outlined" style={{ color: '#f59e0b', animation: 'spin 2s linear infinite' }}>stream</span><div><div style={{ fontWeight: 600, color: '#f59e0b' }}>Starting RTMP Stream...</div><div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{aiRuntimeDetails.current_step || 'Connecting to video stream...'}</div></div></>}
                                    {aiRuntime === 'running' && <><span className="material-symbols-outlined" style={{ color: 'var(--success)' }}>play_circle</span><div><div style={{ fontWeight: 600, color: 'var(--success)' }}>AI Analysis Running</div><div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Live analysis active</div></div></>}
                                    {aiRuntime === 'failed' && <><span className="material-symbols-outlined" style={{ color: 'var(--danger)' }}>error</span><div><div style={{ fontWeight: 600, color: 'var(--danger)' }}>AI Engine Failed</div><div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{aiRuntimeDetails.current_step || `Failed at component: ${aiRuntimeDetails.failed_component}`}</div></div></>}
                                </div>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    {aiRuntime === 'failed' && (
                                        <button onClick={handleRetryInitialization} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--border)', borderRadius: '6px', cursor: 'pointer', fontWeight: 500 }}>
                                            Retry AI Initialization
                                        </button>
                                    )}
                                    {aiRuntime === 'running' ? (
                                        <span style={{ padding: '8px 16px', background: 'rgba(52, 211, 153, 0.1)', color: 'var(--success)', border: '1px solid var(--success)', borderRadius: '6px', fontWeight: 500, fontSize: '13px' }}>🟢 AI Analysis Running</span>
                                    ) : aiRuntime === 'starting_rtmp' ? (
                                        <span style={{ padding: '8px 16px', background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: '1px solid #f59e0b', borderRadius: '6px', fontWeight: 500, fontSize: '13px', animation: 'pulse 2s ease-in-out infinite' }}>⏳ Connecting...</span>
                                    ) : (
                                        <button 
                                            onClick={handleStartAnalysis}
                                            disabled={aiRuntime !== 'ready'} 
                                            style={{ padding: '8px 16px', background: aiRuntime === 'ready' ? 'var(--accent)' : 'var(--bg)', color: aiRuntime === 'ready' ? '#fff' : 'var(--text-secondary)', border: '1px solid var(--border)', borderRadius: '6px', cursor: aiRuntime === 'ready' ? 'pointer' : 'not-allowed', fontWeight: 500, opacity: aiRuntime === 'ready' ? 1 : 0.6 }}
                                        >
                                            Start AI Analysis
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>

                {/* Left column — emotion + chart */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                    {/* Current emotion card */}
                    <div style={cardStyle}>
                        <div style={{ fontSize: '14px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>
                            Live Vitals
                        </div>
                        {aiRuntime !== 'running' ? (
                            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', background: 'var(--bg)', borderRadius: 'var(--radius)' }}>
                                Vitals will appear after AI Analysis starts.
                            </div>
                        ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                            <div>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Emotion</div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <div style={{ fontSize: '24px', fontWeight: 700, color: emotionColor, textTransform: 'capitalize' }}>
                                        {currentEmotion}
                                    </div>
                                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{currentConfidence.toFixed(1)}%</div>
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Attention</div>
                                <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                                    {currentAttention}
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Sentiment</div>
                                <div style={{ fontSize: '18px', fontWeight: 600, color: currentSentiment === 'POSITIVE' ? 'var(--success)' : currentSentiment === 'NEGATIVE' ? 'var(--danger)' : 'var(--text-primary)', textTransform: 'capitalize' }}>
                                    {currentSentiment}
                                </div>
                            </div>
                        </div>
                        )}
                    </div>

                    {/* Emotion chart */}
                    <div style={{ ...cardStyle, flex: 1 }}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px', fontFamily: 'var(--font-heading)' }}>
                            Emotions Over Time
                        </div>
                        {aiRuntime !== 'running' ? (
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--border)', borderRadius: 'var(--radius)', padding: '2rem', minHeight: '150px', marginTop: '10px' }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)', fontSize: '24px', marginBottom: '8px' }}>monitoring</span>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Waiting for AI analysis...</span>
                            </div>
                        ) : chartData.length === 0 ? (
                            <div style={{
                                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                border: '1px dashed var(--border)', borderRadius: 'var(--radius)', padding: '2rem', minHeight: '150px', marginTop: '10px'
                            }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)', fontSize: '24px', marginBottom: '8px' }}>monitoring</span>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Waiting for stream...</span>
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
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: 'var(--font-heading)' }}>
                            Suggested Questions
                        </div>
                        {aiRuntime !== 'running' ? (
                            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', background: 'var(--bg)', borderRadius: 'var(--radius)' }}>
                                Questions will appear after AI Analysis starts.
                            </div>
                        ) : (
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
                                                backgroundImage: 'var(--accent-gradient)',
                                                boxShadow: 'var(--accent-glow)',
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
                        )}
                    </div>
                </div>

                {/* Right column — transcript */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {/* Candidate Tracking Card */}
                    <div style={cardStyle}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: 'var(--font-heading)' }}>
                            Candidate Tracking
                        </div>
                        {aiRuntime !== 'running' ? (
                            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', background: 'var(--bg)', borderRadius: 'var(--radius)' }}>
                                Tracking will be available after AI Analysis starts.
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                {/* Status Indicator */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', background: 'var(--bg)', borderRadius: 'var(--radius)' }}>
                                    {trackingStatus === 'tracking' && <><span style={{ fontSize: '18px' }}>🟢</span><div style={{ fontWeight: 600 }}>Tracking Candidate</div></>}
                                    {enrollmentStatus === 'enrolling' && <><span style={{ fontSize: '18px' }}>🟡</span><div style={{ fontWeight: 600 }}>Enrolling...</div></>}
                                    {trackingStatus === 'reverifying' && <><span style={{ fontSize: '18px' }}>🟠</span><div style={{ fontWeight: 600 }}>Re-verifying...</div></>}
                                    {trackingStatus === 'lost' && <><span style={{ fontSize: '18px' }}>🔴</span><div style={{ fontWeight: 600, color: 'var(--danger)' }}>Candidate Lost</div></>}
                                    {trackingStatus === 'not_enrolled' && enrollmentStatus !== 'enrolling' && <><span style={{ fontSize: '18px' }}>⚪</span><div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Not Enrolled</div></>}
                                    
                                    {/* Sub-status text */}
                                    <div style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                        {trackingStatus === 'lost' && 'Visual analysis paused.'}
                                        {trackingStatus === 'tracking' && 'Visual analysis active.'}
                                    </div>
                                </div>
                                
                                {/* Instructions & Button */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    {trackingStatus === 'not_enrolled' && enrollmentStatus !== 'enrolling' && (
                                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                            {enrollmentStatus === 'failed' && enrollmentReason === 'multiple_faces_detected' ? (
                                                <span style={{ color: '#f59e0b' }}>⚠️ More than one face detected. Please ask interviewers or panel members to temporarily disable their cameras. Then retry enrollment.</span>
                                            ) : (
                                                "Ask only the candidate to keep their camera on for a few seconds. When ready, press Enroll Candidate."
                                            )}
                                        </div>
                                    )}
                                    
                                    {(trackingStatus === 'not_enrolled' || trackingStatus === 'lost' || enrollmentStatus === 'failed' || enrollmentStatus === 'timeout') && (
                                        <button 
                                            onClick={() => {
                                                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                                                    wsRef.current.send(JSON.stringify({ type: 'enroll_candidate' }))
                                                    setEnrollmentStatus('enrolling')
                                                }
                                            }}
                                            disabled={enrollmentStatus === 'enrolling' || aiRuntime !== 'running'}
                                            style={{
                                                padding: '10px 16px', background: enrollmentStatus === 'enrolling' ? 'var(--bg)' : 'var(--accent)', 
                                                color: enrollmentStatus === 'enrolling' ? 'var(--text-secondary)' : '#fff', 
                                                border: '1px solid var(--border)', borderRadius: '6px', cursor: enrollmentStatus === 'enrolling' ? 'not-allowed' : 'pointer', fontWeight: 500, alignSelf: 'flex-start'
                                            }}
                                        >
                                            {enrollmentStatus === 'failed' || enrollmentStatus === 'timeout' || trackingStatus === 'lost' ? 'Retry Enrollment' : 'Enroll Candidate'}
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {integrityAlerts.length > 0 && (
                        <div style={{ ...cardStyle, borderColor: 'var(--danger)', borderLeftWidth: '4px' }}>
                            <div style={{ fontSize: '12px', color: 'var(--danger)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', fontFamily: 'var(--font-heading)', fontWeight: 700 }}>
                                ⚠️ Integrity Alerts
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {integrityAlerts.map((alert, i) => (
                                    <div key={i} style={{ fontSize: '13px', background: 'var(--bg)', padding: '8px', borderRadius: '4px' }}>
                                        <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{alert.event_type}</span>
                                        {alert.details && <span style={{ color: 'var(--text-secondary)', marginLeft: '8px' }}>— {alert.details}</span>}
                                        <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                            {new Date(alert.timestamp).toLocaleTimeString()}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div style={{ ...cardStyle, flex: 1 }}>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px', fontFamily: 'var(--font-heading)' }}>
                            Live Transcript
                        </div>
                        {aiRuntime !== 'running' ? (
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--border)', borderRadius: 'var(--radius)', padding: '2rem', marginTop: '10px' }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)', fontSize: '24px', marginBottom: '8px' }}>forum</span>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center' }}>Waiting for AI analysis...</span>
                            </div>
                        ) : (
                    <div
                        ref={transcriptRef}
                        style={{ height: '600px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}
                    >
                        {transcripts.length === 0 && (
                            <div style={{
                                flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                                border: '1px dashed var(--border)', borderRadius: 'var(--radius)', padding: '2rem', marginTop: '10px'
                            }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)', fontSize: '24px', marginBottom: '8px' }}>forum</span>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center' }}>Transcript will appear here as the candidate speaks...</span>
                            </div>
                        )}
                        {transcripts.map((chunk, i) => (
                            <div key={i} style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px' }}>
                                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                                    {new Date(chunk.timestamp).toLocaleTimeString()}
                                </div>
                                <div style={{ fontSize: '14px', lineHeight: 1.6 }}>{chunk.text}</div>
                            </div>
                        ))}
                    </div>
                        )}
                    </div>
                </div>

                    </>
                )}

            </div>

            {/* Toasts */}
            <div style={{ position: 'fixed', bottom: '24px', right: '24px', display: 'flex', flexDirection: 'column', gap: '8px', zIndex: 9999 }}>
                {toasts.map(toast => (
                    <div key={toast.id} style={{
                        background: 'var(--bg-surface)', border: `1px solid var(--border)`, 
                        borderLeft: `4px solid ${toast.type === 'success' ? 'var(--success)' : toast.type === 'error' ? 'var(--danger)' : toast.type === 'warning' ? '#f59e0b' : 'var(--accent)'}`,
                        padding: '12px 16px', borderRadius: '4px', boxShadow: 'var(--shadow-lg)',
                        fontSize: '13px', fontWeight: 500, minWidth: '250px',
                        animation: 'slideIn 0.3s ease-out'
                    }}>
                        {toast.message}
                    </div>
                ))}
            </div>
            
            </PageTransition>
        </div>
    )
}

const cardStyle: React.CSSProperties = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    boxShadow: 'var(--shadow-card)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px',
}