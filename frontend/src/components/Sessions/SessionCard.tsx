import React, { useEffect, useState } from 'react';
import type { EnhancedSession } from '../../pages/SessionsPage';
import { AvatarInitials } from './AvatarInitials';
import { StatusBadge } from './StatusBadge';
import { formatSessionDate } from './FormatDate';
import client from '../../api/client';

interface SessionCardProps {
    session: EnhancedSession;
    onClick: () => void;
    onStart: (e: React.MouseEvent) => void;
    onEnd: (e: React.MouseEvent) => void;
    onJoin: (e: React.MouseEvent) => void;
    onViewReport: (e: React.MouseEvent) => void;
    onStartZoom?: (e: React.MouseEvent) => void;
}

export function SessionCard({ session, onClick, onStart, onEnd, onJoin, onViewReport, onStartZoom }: SessionCardProps) {
    const [panelCount, setPanelCount] = useState<number | null>(null);

    useEffect(() => {
        let isMounted = true;
        const fetchPanelCount = async () => {
            try {
                const res = await client.get(`/sessions/${session.session_id}/panel`);
                if (isMounted) {
                    setPanelCount(res.data.length);
                }
            } catch (err) {
                console.error('Failed to fetch panel count', err);
            }
        };
        fetchPanelCount();
        return () => { isMounted = false; };
    }, [session.session_id]);

    const handleActionClick = (e: React.MouseEvent, action: (e: React.MouseEvent) => void) => {
        e.stopPropagation(); // Prevent opening drawer
        action(e);
    };

    // Determine interview type from tags or default
    const interviewType = session.tags?.[0] || 'Technical Interview';

    return (
        <div
            className={`session-card ${session.status === 'completed' ? 'session-card--completed' : ''}`}
            onClick={onClick}
            role="button"
            tabIndex={0}
            aria-label={`Session with ${session.candidate || 'Unknown Candidate'}, ${session.status}`}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(); } }}
        >
            {/* Card Header */}
            <div className="session-card__header">
                <div className="session-card__candidate-info">
                    <AvatarInitials name={session.candidate} size={44} />
                    <div style={{ minWidth: 0, flex: 1 }}>
                        <h2 className="session-card__candidate-name">
                            {session.candidate || 'Unknown Candidate'}
                        </h2>
                        <div className="session-card__candidate-role">
                            <span className="material-symbols-outlined" aria-hidden="true">work</span>
                            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {session.job || 'No Role Specified'}
                            </span>
                        </div>
                    </div>
                </div>
                <StatusBadge status={session.status} />
            </div>

            {/* Card Body — Structured Metadata */}
            <div className="session-card__body">
                <div className="session-card__meta-grid">
                    <div className="session-card__meta-item">
                        <div className="session-card__meta-icon">
                            <span className="material-symbols-outlined" aria-hidden="true">calendar_today</span>
                        </div>
                        <div>
                            <div className="session-card__meta-label">Date & Time</div>
                            <div className="session-card__meta-value">{formatSessionDate(session.scheduled_at)}</div>
                        </div>
                    </div>

                    <div className="session-card__meta-item">
                        <div className="session-card__meta-icon">
                            <span className="material-symbols-outlined" aria-hidden="true">group</span>
                        </div>
                        <div>
                            <div className="session-card__meta-label">Panel</div>
                            <div className="session-card__meta-value">
                                {panelCount !== null ? `${panelCount} Member${panelCount !== 1 ? 's' : ''}` : '—'}
                            </div>
                        </div>
                    </div>

                    <div className="session-card__meta-item">
                        <div className="session-card__meta-icon">
                            <span className="material-symbols-outlined" aria-hidden="true">timer</span>
                        </div>
                        <div>
                            <div className="session-card__meta-label">Duration</div>
                            <div className="session-card__meta-value">45 min</div>
                        </div>
                    </div>

                    <div className="session-card__meta-item">
                        <div className="session-card__meta-icon">
                            <span className="material-symbols-outlined" aria-hidden="true">location_on</span>
                        </div>
                        <div>
                            <div className="session-card__meta-label">Type</div>
                            <div className="session-card__meta-value" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '120px' }}>
                                {interviewType}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Card Footer — Actions */}
            <div className="session-card__footer">
                {session.status === 'active' && (
                    <>
                        <button
                            className="session-card__action session-card__action--primary"
                            onClick={(e) => handleActionClick(e, onJoin)}
                            aria-label="Join live session"
                        >
                            <span className="material-symbols-outlined" aria-hidden="true">login</span>
                            Join Session
                        </button>
                        <button
                            className="session-card__action session-card__action--danger"
                            onClick={(e) => handleActionClick(e, onEnd)}
                            aria-label="End session"
                            title="End Session"
                        >
                            <span className="material-symbols-outlined" aria-hidden="true">stop_circle</span>
                        </button>
                    </>
                )}
                {session.status === 'scheduled' && (
                    <div style={{ display: 'flex', gap: '6px', width: '100%' }}>
                        {session.zoom_meeting_id && onStartZoom && (
                            <button
                                className="session-card__action"
                                onClick={(e) => handleActionClick(e, onStartZoom)}
                                aria-label="Start Zoom meeting"
                                style={{
                                    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
                                    background: 'linear-gradient(135deg, #2d8cff 0%, #0b5fcc 100%)',
                                    color: '#fff', border: 'none', borderRadius: '8px',
                                    fontSize: '12px', fontWeight: 600, padding: '8px 10px', cursor: 'pointer',
                                    boxShadow: '0 2px 6px rgba(45, 140, 255, 0.25)'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }} aria-hidden="true">videocam</span>
                                Zoom
                            </button>
                        )}
                        <button
                            className="session-card__action session-card__action--secondary"
                            onClick={(e) => handleActionClick(e, onStart)}
                            aria-label="Start session"
                            style={{ flex: 2 }}
                        >
                            <span className="material-symbols-outlined" aria-hidden="true">play_circle</span>
                            Start Session
                        </button>
                    </div>
                )}
                {session.status === 'processing' && (
                    <button
                        className="session-card__action session-card__action--disabled"
                        disabled
                        aria-label="Processing report"
                        style={{ width: '100%' }}
                    >
                        <span className="material-symbols-outlined" style={{ animation: 'spin 2s linear infinite' }} aria-hidden="true">sync</span>
                        Processing...
                    </button>
                )}
                {session.status === 'completed' && (
                    <button
                        className="session-card__action session-card__action--ghost"
                        onClick={(e) => handleActionClick(e, onViewReport)}
                        aria-label="View interview report"
                    >
                        <span className="material-symbols-outlined" aria-hidden="true">assessment</span>
                        View Report
                    </button>
                )}
            </div>
        </div>
    );
}
