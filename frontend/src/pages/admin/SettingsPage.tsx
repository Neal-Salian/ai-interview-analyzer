import Navbar from '../../components/Navbar';
import PageTransition from '../../components/PageTransition';

export default function SettingsPage() {
    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />
            <PageTransition>
                <div style={{ padding: '32px 24px', maxWidth: '800px', margin: '0 auto' }}>
                    <div style={{ marginBottom: '32px' }}>
                        <h1 style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-heading)', marginBottom: '8px' }}>System Settings</h1>
                        <p style={{ color: 'var(--text-secondary)' }}>Manage application configuration and authentication settings.</p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        {/* System Settings Block */}
                        <div style={{ background: 'var(--bg-surface-high)', borderRadius: '16px', border: '1px solid var(--border)', padding: '24px' }}>
                            <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>General Configuration</h2>
                            <div style={{ display: 'grid', gap: '16px' }}>
                                <div>
                                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                        Platform Name
                                    </label>
                                    <input
                                        type="text"
                                        disabled
                                        value="AI Interview Analyser Enterprise"
                                        style={{ width: '100%', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px 12px', color: 'var(--text-primary)' }}
                                    />
                                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>Contact engineering to update the platform name.</p>
                                </div>
                            </div>
                        </div>

                        {/* Authentication Settings Block */}
                        <div style={{ background: 'var(--bg-surface-high)', borderRadius: '16px', border: '1px solid var(--border)', padding: '24px' }}>
                            <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>Authentication Settings</h2>
                            <div style={{ display: 'grid', gap: '16px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div>
                                        <div style={{ fontWeight: 500, marginBottom: '4px' }}>Require Multi-Factor Authentication</div>
                                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Enforce MFA for all recruiter and admin accounts.</div>
                                    </div>
                                    <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', padding: '4px 12px', borderRadius: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                        Coming Soon
                                    </div>
                                </div>
                                <hr style={{ border: 'none', borderTop: '1px solid var(--border)' }} />
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <div>
                                        <div style={{ fontWeight: 500, marginBottom: '4px' }}>Session Timeout</div>
                                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Automatically log users out after inactivity.</div>
                                    </div>
                                    <select disabled style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-secondary)', borderRadius: '6px', padding: '6px 12px' }}>
                                        <option>24 Hours (Default)</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </PageTransition>
        </div>
    );
}
