import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import client from '../api/client';
import Navbar from '../components/Navbar';
import PageTransition from '../components/PageTransition';
import { useRuntimeStatus } from '../hooks/useRuntimeStatus';
import './MockMeetingPage.css';

interface MockSessionDetails {
    session_id: string;
    status: string;
    stream_key: string;
    meeting_id: string;
    rtmp_server: string;
}

export default function MockMeetingPage() {
    const { mockId } = useParams<{ mockId: string }>();
    const navigate = useNavigate();
    
    const [sessionDetails, setSessionDetails] = useState<MockSessionDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    
    const [copiedServer, setCopiedServer] = useState(false);
    const [copiedKey, setCopiedKey] = useState(false);

    useEffect(() => {
        const fetchDetails = async () => {
            try {
                const res = await client.get(`/sessions/mock/${mockId}`);
                setSessionDetails(res.data);
            } catch (err: any) {
                console.error(err);
                setError(err.response?.data?.detail || "Failed to load mock session details. Are you in development mode?");
            } finally {
                setLoading(false);
            }
        };
        if (mockId) {
            fetchDetails();
        }
    }, [mockId]);

    // Use existing runtime status hook for polling AI/RTMP engine status
    const { aiRuntime, aiRuntimeDetails } = useRuntimeStatus(
        sessionDetails?.session_id,
        !!sessionDetails && ['scheduled', 'active'].includes(sessionDetails.status)
    );

    const handleCopy = useCallback(async (text: string, type: 'server' | 'key') => {
        try {
            await navigator.clipboard.writeText(text);
            if (type === 'server') {
                setCopiedServer(true);
                setTimeout(() => setCopiedServer(false), 2000);
            } else {
                setCopiedKey(true);
                setTimeout(() => setCopiedKey(false), 2000);
            }
        } catch (e) {
            // fallback
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            if (type === 'server') {
                setCopiedServer(true);
                setTimeout(() => setCopiedServer(false), 2000);
            } else {
                setCopiedKey(true);
                setTimeout(() => setCopiedKey(false), 2000);
            }
        }
    }, []);

    const handleOpenDashboard = () => {
        if (sessionDetails?.session_id) {
            navigate(`/sessions/${sessionDetails.session_id}/live`);
        }
    };

    if (loading) {
        return (
            <div className="mock-meeting-page">
                <Navbar />
                <main className="mock-main mock-loading">
                    <span className="material-symbols-outlined spin-icon" style={{ animation: 'spin 2s linear infinite' }}>sync</span>
                    <p>Loading session details...</p>
                </main>
            </div>
        );
    }

    if (error || !sessionDetails) {
        return (
            <div className="mock-meeting-page">
                <Navbar />
                <main className="mock-main mock-error">
                    <span className="material-symbols-outlined error-icon">error</span>
                    <h2>Error Loading Session</h2>
                    <p>{error}</p>
                    <button className="session-card__action session-card__action--primary" onClick={() => navigate('/sessions')}>
                        Return to Sessions
                    </button>
                </main>
            </div>
        );
    }

    return (
        <div className="mock-meeting-page">
            <Navbar />
            <PageTransition>
                <main className="mock-main">
                    
                    <div className="dev-banner">
                        <span className="material-symbols-outlined warning-icon">warning</span>
                        <div className="dev-banner-text">
                            <strong>Development Mode</strong>
                            <p>This is a mock OBS meeting environment. In production, this button launches a real Zoom meeting.</p>
                        </div>
                    </div>

                    <div className="mock-header">
                        <h1>Development Interview Session</h1>
                        <p className="mock-subtitle">Connect your OBS stream to begin</p>
                    </div>

                    <div className="mock-content-grid">
                        <div className="mock-card instructions-card">
                            <h2 className="card-title">
                                <span className="material-symbols-outlined">cast</span>
                                OBS Setup Instructions
                            </h2>
                            <ol className="instructions-list">
                                <li>Open <strong>OBS Studio</strong> on your machine.</li>
                                <li>Click on <strong>Settings</strong> and navigate to the <strong>Stream</strong> tab.</li>
                                <li>Select <strong>Custom</strong> for the Service.</li>
                                <li>Paste the <strong>RTMP Server</strong> and <strong>Stream Key</strong> provided here.</li>
                                <li>Click <strong>Start Streaming</strong> in OBS.</li>
                                <li>Return to this page and open the <strong>Live Dashboard</strong>.</li>
                                <li>Click <strong>Start AI Analysis</strong> in the dashboard to begin ingestion.</li>
                            </ol>
                        </div>

                        <div className="mock-card connection-card">
                            <h2 className="card-title">
                                <span className="material-symbols-outlined">settings_input_antenna</span>
                                Connection Details
                            </h2>
                            
                            <div className="detail-row">
                                <label>Session ID</label>
                                <div className="code-block single-line">
                                    {sessionDetails.session_id}
                                </div>
                            </div>

                            <div className="detail-row">
                                <label>RTMP Server</label>
                                <div className="copyable-field">
                                    <div className="code-block">
                                        {sessionDetails.rtmp_server}
                                    </div>
                                    <button 
                                        className={`copy-btn ${copiedServer ? 'copied' : ''}`}
                                        onClick={() => handleCopy(sessionDetails.rtmp_server, 'server')}
                                        title="Copy RTMP Server"
                                    >
                                        <span className="material-symbols-outlined">
                                            {copiedServer ? 'check' : 'content_copy'}
                                        </span>
                                    </button>
                                </div>
                            </div>

                            <div className="detail-row">
                                <label>Stream Key</label>
                                <div className="copyable-field">
                                    <div className="code-block">
                                        {sessionDetails.stream_key}
                                    </div>
                                    <button 
                                        className={`copy-btn ${copiedKey ? 'copied' : ''}`}
                                        onClick={() => handleCopy(sessionDetails.stream_key, 'key')}
                                        title="Copy Stream Key"
                                    >
                                        <span className="material-symbols-outlined">
                                            {copiedKey ? 'check' : 'content_copy'}
                                        </span>
                                    </button>
                                </div>
                            </div>
                            
                            <div className="status-container">
                                <h3 className="status-label">Runtime Engine Status</h3>
                                <div className={`runtime-status ${aiRuntime}`}>
                                    <span className="material-symbols-outlined status-icon" style={aiRuntime === 'initializing' || aiRuntime === 'starting_rtmp' ? { animation: 'spin 2s linear infinite' } : {}}>
                                        {aiRuntime === 'ready' ? 'check_circle' : 
                                         aiRuntime === 'running' ? 'sensors' : 
                                         aiRuntime === 'failed' ? 'error' : 
                                         aiRuntime === 'not_initialized' ? 'pending' : 'sync'}
                                    </span>
                                    <span className="status-text">
                                        {aiRuntime === 'not_initialized' ? 'Waiting' : 
                                         aiRuntime === 'ready' ? 'AI Ready' : 
                                         aiRuntime === 'running' ? 'AI Analysis Active' : 
                                         aiRuntime === 'failed' ? 'Initialization Failed' : 
                                         `Preparing AI... (${aiRuntimeDetails?.progress || 0}%)`}
                                    </span>
                                </div>
                            </div>

                            <div className="actions-container">
                                <button className="session-card__action session-card__action--primary dashboard-btn" onClick={handleOpenDashboard}>
                                    <span className="material-symbols-outlined">dashboard</span>
                                    Open Live Dashboard
                                </button>
                            </div>
                        </div>
                    </div>
                </main>
            </PageTransition>
        </div>
    );
}
