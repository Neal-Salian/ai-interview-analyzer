export interface Session {
    session_id: string
    candidate: string | null
    job: string | null
    scheduled_at: string | null
    status: 'active' | 'completed'
}

export interface EmotionFrame {
    dominant_emotion: string
    confidence: number
    timestamp: string
}

export interface TranscriptChunk {
    text: string
    timestamp: string
}

export interface SuggestedQuestion {
    id: string
    question_text: string
    triggered_by: string
    was_asked: boolean
    created_at: string
}

// Extensible metric framework — Phase 10
// Every behavioral metric returns this standardized shape.
// The frontend renders metrics dynamically using this interface.
export interface MetricResult {
    name: string
    score: number
    level: string
    confidence: number
    evidence: { quote: string; timestamp: string; source: string }[]
    explanation: string
    signals_used: string[]
}

export interface WSMessage {
    type: 'history' | 'emotion' | 'transcript' | 'question' | 'metric_update' | 'ping'
    // history
    emotions?: EmotionFrame[]
    transcripts?: TranscriptChunk[]
    // live
    dominant_emotion?: string
    confidence?: number
    text?: string
    question?: SuggestedQuestion
    metric?: MetricResult
    timestamp?: string
}