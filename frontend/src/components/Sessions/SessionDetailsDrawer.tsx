import { useEffect, useCallback, useState } from 'react';
import type { EnhancedSession } from '../../pages/SessionsPage';
import { PanelSection } from './PanelSection';
import { AvatarInitials } from './AvatarInitials';
import { StatusBadge } from './StatusBadge';
import { formatSessionDate } from './FormatDate';
import { useRuntimeStatus } from '../../hooks/useRuntimeStatus';

interface SessionDetailsDrawerProps {
    session: EnhancedSession | null;
    isOpen: boolean;
    onClose: () => void;
    onStart: () => void;
    onEnd: () => void;
    onJoin: () => void;
    onViewReport: () => void;
    onCancel?: () => void;
    onNoShow?: () => void;
    onSchedule?: (payload: { scheduled_at: string, interview_type?: string, notes?: string }) => void;
    onDelete?: () => void;
    onAssignJob?: (jobId: string) => void;
    onStartZoom?: () => void;
    onCopyJoinLink?: () => void;
    jobs?: { id: string, title: string }[];
}

export function SessionDetailsDrawer({ session, isOpen, onClose, onStart, onEnd, onJoin, onViewReport, onCancel, onNoShow, onSchedule, onDelete, onAssignJob, onStartZoom, onCopyJoinLink, jobs = [] }: SessionDetailsDrawerProps) {
    const [confirmAction, setConfirmAction] = useState<'cancel' | 'no_show' | null>(null);
    const [isScheduling, setIsScheduling] = useState(false);
    const [copiedLink, setCopiedLink] = useState(false);
    const [scheduleForm, setScheduleForm] = useState({
        scheduled_at: '',
        interview_type: '',
        notes: ''
    });

    const { aiRuntime, aiRuntimeDetails, retryInitialization } = useRuntimeStatus(
        session?.session_id, 
        isOpen && ['scheduled', 'active'].includes(session?.status || '')
    );

    // Reset confirmation state when drawer closes or session changes
    useEffect(() => {
        setConfirmAction(null);
        setIsScheduling(false);
        setCopiedLink(false);
        setScheduleForm({ scheduled_at: '', interview_type: '', notes: '' });
    }, [isOpen, session?.session_id]);
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
                            {session.status === 'draft' ? (
                                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: '16px', color: 'var(--text-secondary)' }} aria-hidden="true">work</span>
                                    <select 
                                        value={session.job_id || ''} 
                                        onChange={(e) => onAssignJob && onAssignJob(e.target.value)}
                                        style={{ 
                                            padding: '4px 8px', 
                                            borderRadius: '6px', 
                                            border: '1px solid var(--border)', 
                                            background: 'var(--bg-surface-high)', 
                                            color: 'var(--text-primary)', 
                                            fontSize: '13px' 
                                        }}
                                        aria-label="Assign Job"
                                    >
                                        <option value="" disabled>Assign a Job...</option>
                                        {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
                                    </select>
                                </div>
                            ) : (
                                <div style={{ color: 'var(--text-secondary)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }} aria-hidden="true">work</span>
                                    {session.job || 'No Role Specified'}
                                </div>
                            )}
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

                    {/* Zoom Meeting Info — only for scheduled/active with a meeting */}
                    {session.zoom_meeting_id && ['scheduled', 'active'].includes(session.status) && (
                        <div style={{
                            display: 'flex', flexDirection: 'column', gap: '10px', padding: '14px 16px',
                            backgroundColor: 'rgba(45, 140, 255, 0.06)', borderRadius: '12px',
                            border: '1px solid rgba(45, 140, 255, 0.15)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: '18px', color: '#2d8cff' }} aria-hidden="true">videocam</span>
                                <span style={{ fontSize: '14px', fontWeight: 600, color: '#2d8cff' }}>Zoom Meeting</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Meeting ID</span>
                                <span style={{ fontSize: '13px', fontWeight: 500, fontFamily: 'monospace', letterSpacing: '0.5px' }}>
                                    {session.zoom_meeting_id}
                                </span>
                            </div>

                            {session.status === 'scheduled' && (
                                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                                    <button
                                        onClick={() => onStartZoom && onStartZoom()}
                                        style={{
                                            flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                                            padding: '10px 14px', fontSize: '13px', fontWeight: 600, borderRadius: '8px',
                                            border: 'none', cursor: 'pointer', color: '#fff',
                                            background: 'linear-gradient(135deg, #2d8cff 0%, #0b5fcc 100%)',
                                            boxShadow: '0 2px 8px rgba(45, 140, 255, 0.3)',
                                            transition: 'all 0.2s ease'
                                        }}
                                        aria-label="Start Zoom meeting as host"
                                    >
                                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }} aria-hidden="true">videocam</span>
                                        Start Zoom Meeting
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (onCopyJoinLink) {
                                                onCopyJoinLink();
                                                setCopiedLink(true);
                                                setTimeout(() => setCopiedLink(false), 2000);
                                            }
                                        }}
                                        style={{
                                            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px',
                                            padding: '10px 12px', fontSize: '13px', fontWeight: 500, borderRadius: '8px',
                                            border: '1px solid var(--border)', cursor: 'pointer',
                                            color: copiedLink ? '#10b981' : 'var(--text-secondary)',
                                            backgroundColor: copiedLink ? 'rgba(16, 185, 129, 0.08)' : 'var(--bg-surface-high)',
                                            transition: 'all 0.2s ease'
                                        }}
                                        aria-label="Copy candidate join link"
                                    >
                                        <span className="material-symbols-outlined" style={{ fontSize: '16px' }} aria-hidden="true">
                                            {copiedLink ? 'check' : 'content_copy'}
                                        </span>
                                        {copiedLink ? 'Copied!' : 'Copy Link'}
                                    </button>
                                </div>
                            )}

                            {session.status === 'active' && (
                                <button
                                    onClick={() => onStartZoom && onStartZoom()}
                                    style={{
                                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                                        padding: '10px 14px', fontSize: '13px', fontWeight: 600, borderRadius: '8px',
                                        border: 'none', cursor: 'pointer', color: '#fff', marginTop: '4px',
                                        background: 'linear-gradient(135deg, #2d8cff 0%, #0b5fcc 100%)',
                                        boxShadow: '0 2px 8px rgba(45, 140, 255, 0.3)',
                                        transition: 'all 0.2s ease'
                                    }}
                                    aria-label="Join the current Zoom meeting"
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }} aria-hidden="true">videocam</span>
                                    Join Current Meeting
                                </button>
                            )}
                        </div>
                    )}

                    {/* No Zoom meeting warning for scheduled/active */}
                    {!session.zoom_meeting_id && ['scheduled', 'active'].includes(session.status) && (
                        <div style={{
                            display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px',
                            backgroundColor: 'rgba(245, 158, 11, 0.08)', borderRadius: '10px',
                            border: '1px solid rgba(245, 158, 11, 0.2)', fontSize: '13px', color: 'var(--text-secondary)'
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '18px', color: '#f59e0b' }} aria-hidden="true">warning</span>
                            This session does not have an associated Zoom meeting.
                        </div>
                    )}

                    {/* AI Engine Status (only for scheduled/active) */}
                    {['scheduled', 'active'].includes(session.status) && (
                        <div style={{
                            display: 'flex', flexDirection: 'column', gap: '10px', padding: '14px 16px',
                            backgroundColor: 'var(--bg-surface-high)', borderRadius: '12px',
                            border: '1px solid var(--border)', marginTop: '4px'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: '18px', color: 'var(--text-secondary)' }} aria-hidden="true">psychology</span>
                                <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>AI Engine</span>
                            </div>
                            
                            {aiRuntime === 'not_initialized' && (
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, marginBottom: '4px' }}>
                                        ⚪ Waiting for Meeting
                                    </div>
                                    The AI engine will automatically prepare once the Zoom meeting starts.
                                </div>
                            )}

                            {(aiRuntime === 'initializing' || aiRuntime === 'starting_rtmp') && (
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, color: '#f59e0b', marginBottom: '8px' }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: '16px', animation: 'spin 2s linear infinite' }}>sync</span>
                                        Preparing AI... ({aiRuntimeDetails.progress}%)
                                    </div>
                                    <div style={{ marginBottom: '8px', fontStyle: 'italic' }}>
                                        {aiRuntimeDetails.current_step || 'Connecting components...'}
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            {aiRuntimeDetails.progress >= 25 ? '✓' : (aiRuntimeDetails.progress > 0 ? '⏳' : '○')} RTMP Stream
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            {aiRuntimeDetails.progress >= 50 ? '✓' : (aiRuntimeDetails.progress >= 25 ? '⏳' : '○')} Ollama Engine
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            {aiRuntimeDetails.progress >= 75 ? '✓' : (aiRuntimeDetails.progress >= 50 ? '⏳' : '○')} Whisper Model
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            {aiRuntimeDetails.progress >= 100 ? '✓' : (aiRuntimeDetails.progress >= 75 ? '⏳' : '○')} DeepFace Service
                                        </div>
                                    </div>
                                </div>
                            )}

                            {aiRuntime === 'ready' && (
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, color: 'var(--success)', marginBottom: '8px' }}>
                                        🟢 AI Ready
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        <div>✓ RTMP Stream</div>
                                        <div>✓ Ollama Engine</div>
                                        <div>✓ Whisper Model</div>
                                        <div>✓ DeepFace Service</div>
                                    </div>
                                </div>
                            )}

                            {aiRuntime === 'running' && (
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, color: 'var(--success)' }}>
                                        🟢 AI Analysis Running
                                    </div>
                                </div>
                            )}

                            {aiRuntime === 'failed' && (
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, color: 'var(--danger)', marginBottom: '8px' }}>
                                        🔴 AI Initialization Failed
                                    </div>
                                    <div style={{ marginBottom: '4px' }}>
                                        <strong>Component:</strong> {aiRuntimeDetails.failed_component || 'Unknown'}
                                    </div>
                                    <div style={{ marginBottom: '12px' }}>
                                        <strong>Reason:</strong> {aiRuntimeDetails.current_step || 'An error occurred during startup.'}
                                    </div>
                                    <button 
                                        onClick={() => retryInitialization()}
                                        style={{
                                            padding: '8px 12px', fontSize: '13px', fontWeight: 500, borderRadius: '6px',
                                            border: '1px solid var(--border)', cursor: 'pointer', background: 'var(--bg-surface)'
                                        }}
                                    >
                                        Retry Initialization
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Quick Actions based on Status */}
                    <div style={{ marginTop: '4px' }}>
                        {isScheduling ? (
                            <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-high)', borderRadius: '12px', border: '1px solid var(--border)' }}>
                                <h4 style={{ margin: '0 0 12px 0', fontSize: '15px' }}>Schedule Session</h4>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    <div>
                                        <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Date & Time</label>
                                        <input
                                            type="datetime-local"
                                            value={scheduleForm.scheduled_at}
                                            onChange={e => setScheduleForm({...scheduleForm, scheduled_at: e.target.value})}
                                            className="modal-input"
                                            style={{ width: '100%', boxSizing: 'border-box' }}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Interview Type</label>
                                        <input
                                            type="text"
                                            value={scheduleForm.interview_type}
                                            onChange={e => setScheduleForm({...scheduleForm, interview_type: e.target.value})}
                                            className="modal-input"
                                            placeholder="e.g. Technical, Behavioral"
                                            style={{ width: '100%', boxSizing: 'border-box' }}
                                        />
                                    </div>
                                    <div>
                                        <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Notes</label>
                                        <textarea
                                            value={scheduleForm.notes}
                                            onChange={e => setScheduleForm({...scheduleForm, notes: e.target.value})}
                                            className="modal-input"
                                            placeholder="Optional notes"
                                            style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical', minHeight: '60px' }}
                                        />
                                    </div>
                                    <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                                        <button
                                            onClick={() => setIsScheduling(false)}
                                            className="session-card__action session-card__action--secondary"
                                            style={{ flex: 1, padding: '10px', fontSize: '13px', borderRadius: '8px' }}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (onSchedule) onSchedule(scheduleForm);
                                            }}
                                            disabled={!scheduleForm.scheduled_at}
                                            className="session-card__action session-card__action--primary"
                                            style={{ flex: 1, padding: '10px', fontSize: '13px', borderRadius: '8px', opacity: !scheduleForm.scheduled_at ? 0.5 : 1 }}
                                        >
                                            Schedule
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : confirmAction ? (
                            <div style={{ padding: '16px', backgroundColor: 'var(--bg-surface-high)', borderRadius: '12px', border: '1px solid var(--border)', textAlign: 'center' }}>
                                <p style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text-primary)' }}>
                                    {confirmAction === 'cancel' 
                                        ? "This interview will be cancelled and will not proceed."
                                        : "Mark this candidate as absent for the interview."}
                                </p>
                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <button
                                        onClick={() => setConfirmAction(null)}
                                        className="session-card__action session-card__action--secondary"
                                        style={{ flex: 1, padding: '10px', fontSize: '14px', borderRadius: '8px' }}
                                    >
                                        Go Back
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (confirmAction === 'cancel' && onCancel) onCancel();
                                            if (confirmAction === 'no_show' && onNoShow) onNoShow();
                                            setConfirmAction(null);
                                        }}
                                        className="session-card__action session-card__action--danger"
                                        style={{ flex: 1, padding: '10px', fontSize: '14px', borderRadius: '8px' }}
                                    >
                                        Confirm
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <>
                                {session.status === 'draft' && (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <button
                                            onClick={() => setIsScheduling(true)}
                                            className="session-card__action session-card__action--primary"
                                            style={{ width: '100%', padding: '12px', fontSize: '14px', borderRadius: '10px' }}
                                            aria-label="Schedule this session"
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">event</span>
                                            Schedule Session
                                        </button>
                                        <button
                                            onClick={() => { if (onDelete) onDelete(); }}
                                            className="session-card__action session-card__action--danger"
                                            style={{ width: '100%', padding: '10px', fontSize: '13px', borderRadius: '8px' }}
                                        >
                                            Delete Draft
                                        </button>
                                    </div>
                                )}
                                {session.status === 'scheduled' && (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <button
                                            onClick={onStart}
                                            className={`session-card__action ${aiRuntime === 'ready' ? 'session-card__action--primary' : 'session-card__action--disabled'}`}
                                            style={{ width: '100%', padding: '12px', fontSize: '14px', borderRadius: '10px', opacity: aiRuntime === 'ready' ? 1 : 0.6, cursor: aiRuntime === 'ready' ? 'pointer' : 'not-allowed' }}
                                            disabled={aiRuntime !== 'ready'}
                                            aria-label="Start this session"
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">play_circle</span>
                                            Start AI Analysis
                                        </button>
                                        <div style={{ display: 'flex', gap: '8px' }}>
                                            <button
                                                onClick={() => setConfirmAction('no_show')}
                                                className="session-card__action session-card__action--secondary"
                                                style={{ flex: 1, padding: '10px', fontSize: '13px', borderRadius: '8px' }}
                                            >
                                                No-Show
                                            </button>
                                            <button
                                                onClick={() => setConfirmAction('cancel')}
                                                className="session-card__action session-card__action--danger"
                                                style={{ flex: 1, padding: '10px', fontSize: '13px', borderRadius: '8px' }}
                                            >
                                                Cancel Session
                                            </button>
                                        </div>
                                    </div>
                                )}
                                {session.status === 'active' && (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <div style={{ display: 'flex', gap: '8px' }}>
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
                                        <button
                                            onClick={() => setConfirmAction('no_show')}
                                            className="session-card__action session-card__action--secondary"
                                            style={{ width: '100%', padding: '10px', fontSize: '13px', borderRadius: '8px' }}
                                        >
                                            Mark Candidate No-Show
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
                            </>
                        )}
                    </div>

                    <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '8px 0' }} />

                    {/* Panel Section */}
                    <div style={{ margin: '-24px -20px 0 -20px' }}>
                        <PanelSection sessionId={session.session_id} sessionStatus={session.status} />
                    </div>
                </div>
            </div>
        </>
    );
}
