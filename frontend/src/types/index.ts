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
    raw_score?: number
    level: string
    confidence: number
    confidence_details?: { signal: string; score: number; confidence: number; weight_applied: number }[]
    evidence: { quote: string; timestamp: string; source: string }[]
    explanation: string
    signals_used: string[]
}

// Live competency evidence tracking — progressive display during interview
export interface LiveCompetencyItem {
    competency_key: string
    display_name: string
    evidence_count: number
    confidence: 'Low' | 'Medium' | 'High'
    status: 'Collecting' | 'Building' | 'Ready'
    question_ids: string[]
    latest_observations: string[]
}

export interface LiveEvidenceGroup {
    competency: string
    observations: string[]
}

export interface WSMessage {
    type: 'history' | 'emotion' | 'transcript' | 'question' | 'metric_update' | 'ping' | 'attention' | 'integrity_alert' | 'sentiment' | 'enrollment_status' | 'tracking_status' | 'live_competency'
    // history
    emotions?: EmotionFrame[]
    transcripts?: TranscriptChunk[]
    questions?: SuggestedQuestion[]
    // live
    dominant_emotion?: string
    confidence?: number
    text?: string
    question?: SuggestedQuestion
    metric?: MetricResult
    timestamp?: string
    // attention
    direction?: string
    // integrity_alert
    event_type?: string
    severity?: string
    details?: string
    // sentiment
    label?: string
    score?: number
    // enrollment / tracking
    status?: string
    reason?: string
    // live competency evidence tracking
    competencies?: LiveCompetencyItem[]
    latest_evidence?: LiveEvidenceGroup[]
}