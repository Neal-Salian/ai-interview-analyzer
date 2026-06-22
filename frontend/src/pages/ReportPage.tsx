import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import ReportChat from '../components/ReportChat';
import client from '../api/client';
import type { MetricResult } from '../types';
import type { StructuredReport } from '../types/report';
import PageTransition from '../components/PageTransition';
import { SkeletonCard, SkeletonText } from '../components/Skeleton';

// Dashboard Components
import ExecutiveSummaryCard from '../components/Report/ExecutiveSummaryCard';
import StrengthsConcernsCard from '../components/Report/StrengthsConcernsCard';
import InterviewAnalysisCard from '../components/Report/InterviewAnalysisCard';
import BehavioralAnalysisCard from '../components/Report/BehavioralAnalysisCard';
import IntegrityAssessmentCard from '../components/Report/IntegrityAssessmentCard';
import TranscriptEvidenceCard from '../components/Report/TranscriptEvidenceCard';
import AIInsightsCard from '../components/Report/AIInsightsCard';
import RecommendationCard from '../components/Report/RecommendationCard';

interface AnalysisResponse {
    session_id: string;
    candidate: string | null;
    job: string | null;
    status: string;
    started_at: string | null;
    ended_at: string | null;
    duration_minutes: number | null;
    emotion_breakdown: Record<string, number>;
    avg_confidence: number;
    emotion_timeline: { dominant_emotion: string; confidence: number; timestamp: string }[];
    total_frames_analyzed: number;
    transcript_chunks: number;
    full_transcript: string;
    big_five: Record<string, number>;
    overall_sentiment: { label: string; score: number };
    questions_generated: number;
    questions_asked: number;
    metrics: MetricResult[];
    integrity_events: { event_type: string; severity: string; details: string; timestamp: string }[];
}

export default function ReportPage() {
    const { id: sessionId } = useParams<{ id: string }>();
    const navigate = useNavigate();
    
    const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
    const [report, setReport] = useState<StructuredReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!sessionId) return;
        Promise.all([
            client.get(`/analysis/${sessionId}`),
            client.get(`/reports/${sessionId}`),
            new Promise(resolve => setTimeout(resolve, 500))
        ])
            .then(([analysisRes, reportRes]) => {
                if (analysisRes.data.status !== 'completed') {
                    setError('Report is only available for completed sessions.');
                    return;
                }
                setAnalysis(analysisRes.data);
                setReport(reportRes.data);
            })
            .catch(err => {
                console.error('Failed to load analysis or report', err);
                setError('Could not load analysis data.');
            })
            .finally(() => setLoading(false));
    }, [sessionId]);

    if (loading) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
                <Navbar />
                <PageTransition>
                    <header style={{ padding: '2rem', borderBottom: '1px solid var(--border)' }}>
                        <SkeletonText width="300px" height="28px" style={{ marginBottom: '16px' }} />
                    </header>
                    <main style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem', flex: 1 }}>
                        <SkeletonCard style={{ height: '180px' }} />
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                <SkeletonCard style={{ height: '280px' }} />
                                <SkeletonCard style={{ height: '220px' }} />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                <SkeletonCard style={{ height: '250px' }} />
                                <SkeletonCard style={{ height: '200px' }} />
                            </div>
                        </div>
                    </main>
                </PageTransition>
            </div>
        );
    }

    if (error || !analysis || !report) {
        return (
            <div>
                <Navbar />
                <div style={{ padding: '40px', color: 'var(--danger)' }}>
                    {error || 'No analysis data found for this session.'}
                </div>
            </div>
        );
    }

    const downloadPdf = async () => {
        try {
            const response = await client.get(`/reports/${sessionId}/pdf`, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `interview_report_${analysis?.candidate}_${sessionId?.substring(0,8)}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.parentNode?.removeChild(link);
        } catch (err) {
            console.error('Failed to download PDF', err);
            alert('Failed to download PDF');
        }
    };

    const evaluation = report.knowledge_assessment && report.knowledge_assessment.length > 0 
        ? report.knowledge_assessment[0] 
        : null;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />

            <PageTransition>
                {/* Page Header */}
                <header style={{ padding: '1.5rem 2rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <button onClick={() => navigate('/sessions')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, paddingRight: '12px' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>arrow_back</span>
                            Back to Sessions
                        </button>
                        <h1 style={{ fontSize: '20px', fontWeight: 600, margin: 0 }}>
                            Executive Report
                        </h1>
                    </div>
                    <button 
                        onClick={downloadPdf}
                        style={{ 
                            fontSize: '13px', color: '#fff', background: 'var(--accent)', 
                            border: 'none', borderRadius: '6px', padding: '8px 16px', 
                            cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px'
                        }}
                    >
                        📄 Download PDF
                    </button>
                </header>

                <main style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1200px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
                    {/* Section 1: Executive Summary */}
                    <ExecutiveSummaryCard summary={report.executive_summary} evaluation={evaluation} />

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                        {/* LEFT COLUMN */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                            {/* Section 2: Strengths & Concerns */}
                            <StrengthsConcernsCard evaluation={evaluation} />

                            {/* Section 6: Transcript Evidence */}
                            <TranscriptEvidenceCard evaluation={evaluation} />

                            {/* Section 7: AI Analysis Insights */}
                            <AIInsightsCard metrics={analysis.metrics} />

                            {/* Explainability Chat */}
                            <div style={{
                                background: 'var(--bg-surface)',
                                borderRadius: '12px',
                                border: '1px solid var(--border)',
                                padding: '1.5rem',
                                boxShadow: 'var(--shadow-card)',
                            }}>
                                <h3 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 1rem 0', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                                    💬 Ask about this report
                                </h3>
                                <ReportChat sessionId={sessionId!} />
                            </div>
                        </div>

                        {/* RIGHT COLUMN */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                            {/* Section 3: Interview Analysis Overview */}
                            <InterviewAnalysisCard 
                                sentiment={analysis.overall_sentiment}
                                confidence={analysis.avg_confidence}
                                emotionBreakdown={analysis.emotion_breakdown}
                                transcriptChunks={analysis.transcript_chunks}
                                wordCount={report.communication_analysis.word_count}
                            />

                            {/* Section 4: Behavioral Analysis */}
                            <BehavioralAnalysisCard emotionTimeline={analysis.emotion_timeline} />

                            {/* Section 5: Integrity Assessment */}
                            <IntegrityAssessmentCard integrityData={{ events: analysis.integrity_events }} />
                        </div>
                    </div>

                    {/* Section 8: Final Recommendation */}
                    <RecommendationCard evaluation={evaluation} />

                </main>
            </PageTransition>
        </div>
    );
}