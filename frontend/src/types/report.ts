import type { MetricResult } from './index';

export interface ReportExecutiveSummary {
    candidate: string;
    job: string;
    duration_minutes: number | null;
    status: string;
    dominant_emotion: string;
    avg_confidence: number;
    overall_sentiment: string;
    metrics_computed: number;
    integrity_alerts: number;
    overall_confidence: number;
    data_quality: string;
}

export interface ReportInterviewOverview {
    started_at: string | null;
    ended_at: string | null;
    duration_minutes: number | null;
    total_frames: number;
    transcript_chunks: number;
    questions_generated: number;
    questions_asked: number;
}

export interface ReportCommunicationAnalysis {
    overall_sentiment: { label: string; score: number };
    big_five: Record<string, number>;
    communication_metric: MetricResult | null;
    transcript_chunks: number;
    word_count: number;
}

export interface ReportIntegrityIndicators {
    events: { event_type: string; severity: string; details: string; timestamp: string }[];
    total_alerts: number;
    severity_breakdown: Record<string, number>;
}

export interface ReportEvaluation {
    category: string;
    combined_score: number | null;
    strengths: string[];
    improvement_areas: string[];
    overall_assessment: string;
    correct_concepts: string[];
    missing_concepts: string[];
    potential_inaccuracies: string[];
    confidence_level: string;
    evidence: string[] | { quote: string }[]; // Evidence can be varied depending on DB structure
}

export interface StructuredReport {
    session_id: string;
    generated_at: string;
    executive_summary: ReportExecutiveSummary;
    interview_overview: ReportInterviewOverview;
    communication_analysis: ReportCommunicationAnalysis;
    behavioral_insights: {
        metrics: MetricResult[];
        total_metrics: number;
        overall_confidence: number;
    };
    attention_indicators: any;
    integrity_indicators: ReportIntegrityIndicators;
    stress_indicators: MetricResult | null;
    emotional_stability: {
        metric: MetricResult | null;
        emotion_breakdown: Record<string, number>;
        dominant_emotion: string;
        avg_confidence: number;
    };
    technical_summary: {
        job_title: string;
        job_skills: string[];
        seniority: string;
        confidence_metric: MetricResult | null;
    };
    evidence_observations: {
        metrics_with_evidence: {
            name: string;
            score: number;
            level: string;
            evidence: { quote: string; timestamp: string; source: string }[];
        }[];
    };
    transcript_appendix: {
        full_transcript: string;
        chunk_count: number;
        questions: { question_text: string; triggered_by: string; was_asked: boolean }[];
    };
    knowledge_assessment: ReportEvaluation[];
}
