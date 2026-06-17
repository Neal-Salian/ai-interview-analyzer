import { useEffect, useCallback } from 'react';
import type { EnhancedSession } from '../../pages/SessionsPage';
import { PanelSection } from './PanelSection';
import { AvatarInitials } from './AvatarInitials';
import { StatusBadge } from './StatusBadge';
import { formatSessionDate } from './FormatDate';

interface SessionDetailsDrawerProps {
    session: EnhancedSession | null;
    isOpen: boolean;
    onClose: () => void;
    onStart: () => void;
    onEnd: () => void;
    onJoin: () => void;
    onViewReport: () => void;
}

export function SessionDetailsDrawer({ session, isOpen, onClose, onStart, onEnd, onJoin, onViewReport }: SessionDetailsDrawerProps) {
    // Escape key handler
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape' && isOpen) {
            onClose();
        }
    }, [isOpen, onClose]);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    // Lock body scroll when drawer is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => { document.body.style.overflow = ''; };
    }, [isOpen]);

    if (!isOpen || !session) return null;

    // Determine interview type from tags or default
    const interviewType = session.tags?.[0] || 'Technical Interview';

    return (
        <>
            {/* Backdrop */}
            <div
                className="drawer-backdrop"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Drawer */}
            <div
                className="drawer-panel"
                role="dialog"
                aria-modal="true"
                aria-label={`Session details for ${session.candidate || 'Unknown Candidate'}`}
            >
                {/* Header */}
                <div className="drawer-header">
                    <h2 className="drawer-header__title">Session Details</h2>
                    <button
                        className="drawer-close-btn"
                        onClick={onClose}
                        aria-label="Close drawer"
                    >
                        <span className="material-symbols-outlined" aria-hidden="true">close</span>
                    </button>
                </div>

                {/* Content */}
                <div className="drawer-body">
                    {/* Candidate Info */}
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                        <AvatarInitials name={session.candidate} size={56} />
                        <div>
                            <h3 style={{ fontSize: '20px', fontWeight: 600, margin: '0 0 4px 0', fontFamily: 'var(--font-heading)' }}>
                                {session.candidate || 'Unknown Candidate'}
                            </h3>
                            <div style={{ color: 'var(--text-secondary)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }} aria-hidden="true">work</span>
                                {session.job || 'No Role Specified'}
                            </div>
                        </div>
                    </div>

                    {/* Status & Details */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', backgroundColor: 'var(--bg-surface)', borderRadius: '12px', border: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Status</span>
                            <StatusBadge status={session.status} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Scheduled</span>
                            <span style={{ fontSize: '13px', fontWeight: 500 }}>{formatSessionDate(session.scheduled_at)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Duration</span>
                            <span style={{ fontSize: '13px', fontWeight: 500 }}>45 min</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Type</span>
                            <span style={{ fontSize: '13px', fontWeight: 500 }}>{interviewType}</span>
                        </div>
                    </div>

                    {/* Quick Actions based on Status */}
                    <div style={{ marginTop: '4px' }}>
                        {session.status === 'scheduled' && (
                            <button
                                onClick={onStart}
                                className="session-card__action session-card__action--primary"
                                style={{ width: '100%', padding: '12px', fontSize: '14px', borderRadius: '10px' }}
                                aria-label="Start this session"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">play_circle</span>
                                Start Session
                            </button>
                        )}
                        {session.status === 'active' && (
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button
                                    onClick={onJoin}
                                    className="session-card__action session-card__action--primary"
                                    style={{ flex: 2, padding: '12px', fontSize: '14px', borderRadius: '10px' }}
                                    aria-label="Join live session"
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">login</span>
                                    Join
                                </button>
                                <button
                                    onClick={onEnd}
                                    className="session-card__action session-card__action--danger"
                                    style={{ flex: 1, padding: '12px', fontSize: '14px', borderRadius: '10px' }}
                                    aria-label="End this session"
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">stop_circle</span>
                                    End
                                </button>
                            </div>
                        )}
                        {session.status === 'completed' && (
                            <button
                                onClick={onViewReport}
                                className="session-card__action session-card__action--secondary"
                                style={{ width: '100%', padding: '12px', fontSize: '14px', borderRadius: '10px' }}
                                aria-label="View interview report"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">assessment</span>
                                View Report
                            </button>
                        )}
                    </div>

                    <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '8px 0' }} />

                    {/* Panel Section */}
                    <div style={{ margin: '-24px -20px 0 -20px' }}>
                        <PanelSection sessionId={session.session_id} />
                    </div>
                </div>
            </div>
        </>
    );
}
