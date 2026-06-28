import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import client from '../api/client';
import { useLocation } from 'react-router-dom';

interface ZoomStatus {
    connected: boolean;
    zoom_email?: string;
    connected_at?: string;
}

export default function SettingsPage() {
    const [zoomStatus, setZoomStatus] = useState<ZoomStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const location = useLocation();

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await client.get('/zoom/oauth/status');
                setZoomStatus(res.data);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to fetch Zoom connection status.');
            } finally {
                setLoading(false);
            }
        };
        fetchStatus();
    }, [location.search]);

    const handleConnectZoom = async () => {
        try {
            const res = await client.get('/zoom/oauth/url');
            window.location.href = res.data.url;
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to get Zoom authorization URL.');
        }
    };

    const handleDisconnectZoom = async () => {
        if (!window.confirm('Are you sure you want to disconnect your Zoom account?')) return;
        
        try {
            await client.delete('/zoom/oauth/disconnect');
            setZoomStatus({ connected: false });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to disconnect Zoom.');
        }
    };

    return (
        <div className="layout">
            <Navbar />
            <div className="layout-body">
                <Sidebar />
                <main className="main-content">
                    <div className="page-header">
                        <h1>Settings</h1>
                        <p className="page-subtitle">Manage your personal settings and integrations.</p>
                    </div>

                    {error && (
                        <div style={{ backgroundColor: '#ffebee', color: '#c62828', padding: '12px 16px', borderRadius: '8px', marginBottom: '24px' }}>
                            {error}
                        </div>
                    )}
                    
                    {new URLSearchParams(location.search).get('zoom_connected') === 'true' && (
                        <div style={{ backgroundColor: '#e8f5e9', color: '#2e7d32', padding: '12px 16px', borderRadius: '8px', marginBottom: '24px' }}>
                            Successfully connected to Zoom!
                        </div>
                    )}

                    <section style={{ backgroundColor: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', marginBottom: '24px' }}>
                        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', color: '#1a1a1a' }}>Zoom Integration</h2>
                        <p style={{ color: '#666', marginBottom: '24px', fontSize: '14px', lineHeight: 1.5 }}>
                            Connect your Zoom account to schedule and manage AI-analyzed interviews directly from the platform.
                        </p>

                        {loading ? (
                            <div>Loading...</div>
                        ) : zoomStatus?.connected ? (
                            <div style={{ border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontWeight: 600, color: '#1a1a1a' }}>Connected to Zoom</div>
                                    <div style={{ fontSize: '14px', color: '#666', marginTop: '4px' }}>{zoomStatus.zoom_email}</div>
                                </div>
                                <button 
                                    onClick={handleDisconnectZoom}
                                    style={{ padding: '8px 16px', backgroundColor: '#fff', border: '1px solid #ff4d4f', color: '#ff4d4f', borderRadius: '6px', fontWeight: 600, cursor: 'pointer' }}
                                >
                                    Disconnect
                                </button>
                            </div>
                        ) : (
                            <button 
                                onClick={handleConnectZoom}
                                style={{ padding: '10px 20px', backgroundColor: '#2d8cff', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>videocam</span>
                                Connect Zoom
                            </button>
                        )}
                    </section>
                </main>
            </div>
        </div>
    );
}
