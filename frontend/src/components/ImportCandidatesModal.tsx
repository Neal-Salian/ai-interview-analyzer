import { useState, useRef, useCallback } from 'react'
import client from '../api/client'
import './ImportCandidatesModal.css'

interface ImportCandidatesModalProps {
    onClose: () => void
    onImportComplete: () => void
    jobs: { id: string; title: string }[]
}

type Step = 'upload' | 'preview' | 'results'

interface ValidRow {
    row: number
    name: string
    email: string
    phone: string | null
    notes: string | null
    job_id: string | null
    job_title: string | null
}

interface InvalidRow {
    row: number
    name: string
    email: string
    phone?: string
    notes?: string
    errors: string[]
}

interface DuplicateRow {
    row: number
    name: string
    email: string
    phone?: string
    notes?: string
    reason: string
}

interface ValidationResult {
    valid: ValidRow[]
    invalid: InvalidRow[]
    duplicates: DuplicateRow[]
}

interface ImportResult {
    created: number
    skipped: number
    failed: number
    results: { email: string; name: string; status: string; reason?: string; candidate_id?: string }[]
}

export default function ImportCandidatesModal({ onClose, onImportComplete, jobs }: ImportCandidatesModalProps) {
    const [step, setStep] = useState<Step>('upload')
    const [file, setFile] = useState<File | null>(null)
    const [fallbackJobId, setFallbackJobId] = useState('')
    const [dragOver, setDragOver] = useState(false)
    const [validating, setValidating] = useState(false)
    const [importing, setImporting] = useState(false)
    const [validation, setValidation] = useState<ValidationResult | null>(null)
    const [importResult, setImportResult] = useState<ImportResult | null>(null)
    const [error, setError] = useState('')
    const [previewTab, setPreviewTab] = useState<'valid' | 'invalid' | 'duplicates'>('valid')
    const fileInputRef = useRef<HTMLInputElement>(null)

    // ── File handling ──────────────────────────────────────────────────────
    const handleFileDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setDragOver(false)
        const droppedFile = e.dataTransfer.files[0]
        if (droppedFile) validateAndSetFile(droppedFile)
    }, [])

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0]
        if (selectedFile) validateAndSetFile(selectedFile)
    }, [])

    const validateAndSetFile = (f: File) => {
        setError('')
        const name = f.name.toLowerCase()
        if (!name.endsWith('.csv') && !name.endsWith('.xlsx')) {
            setError('Only CSV and XLSX files are supported')
            return
        }
        if (f.size > 5 * 1024 * 1024) {
            setError('File size exceeds 5MB limit')
            return
        }
        setFile(f)
    }

    const removeFile = () => {
        setFile(null)
        setError('')
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    // ── CSV template download ──────────────────────────────────────────────
    const downloadTemplate = () => {
        const csv = 'Name,Email,Phone,Notes,Job\nJohn Doe,john@example.com,9999999999,Great candidate,Backend Developer\nJane Smith,jane@example.com,,,\n'
        const blob = new Blob([csv], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'candidate_import_template.csv'
        a.click()
        URL.revokeObjectURL(url)
    }

    // ── Validate ───────────────────────────────────────────────────────────
    const handleValidate = async () => {
        if (!file) return
        setValidating(true)
        setError('')

        try {
            const formData = new FormData()
            formData.append('file', file)

            const res = await client.post('/candidates/import/validate', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })

            setValidation(res.data)
            setStep('preview')

            // Auto-select first non-empty tab
            if (res.data.valid.length > 0) setPreviewTab('valid')
            else if (res.data.invalid.length > 0) setPreviewTab('invalid')
            else if (res.data.duplicates.length > 0) setPreviewTab('duplicates')
        } catch (err: any) {
            const detail = err.response?.data?.detail || 'Failed to validate file'
            setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
        } finally {
            setValidating(false)
        }
    }

    // ── Import ─────────────────────────────────────────────────────────────
    const handleImport = async () => {
        if (!validation || validation.valid.length === 0) return
        setImporting(true)
        setError('')

        try {
            const payload = {
                candidates: validation.valid.map(v => ({
                    name: v.name,
                    email: v.email,
                    phone: v.phone || undefined,
                    notes: v.notes || undefined,
                    job_id: v.job_id || undefined,
                })),
                job_id: fallbackJobId || undefined
            }

            const res = await client.post('/candidates/import', payload)
            setImportResult(res.data)
            setStep('results')
        } catch (err: any) {
            const detail = err.response?.data?.detail || 'Import failed'
            setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
        } finally {
            setImporting(false)
        }
    }

    // ── Format file size ───────────────────────────────────────────────────
    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    // ── Render ─────────────────────────────────────────────────────────────
    return (
        <div className="import-modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
            <div className="import-modal">
                {/* Header */}
                <div className="import-modal-header">
                    <h2>Import Candidates</h2>
                    <button className="import-modal-close" onClick={onClose}>
                        <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>close</span>
                    </button>
                </div>

                {/* Steps */}
                <div className="import-steps">
                    <div className={`import-step ${step === 'upload' ? 'active' : 'completed'}`}>
                        <span className="import-step-number">{step === 'upload' ? '1' : '✓'}</span>
                        <span>Upload</span>
                    </div>
                    <div className="import-step-divider" />
                    <div className={`import-step ${step === 'preview' ? 'active' : (step === 'results' ? 'completed' : '')}`}>
                        <span className="import-step-number">{step === 'results' ? '✓' : '2'}</span>
                        <span>Preview</span>
                    </div>
                    <div className="import-step-divider" />
                    <div className={`import-step ${step === 'results' ? 'active' : ''}`}>
                        <span className="import-step-number">3</span>
                        <span>Results</span>
                    </div>
                </div>

                {/* Body */}
                <div className="import-modal-body">
                    {/* ── Step 1: Upload ─────────────────────────────────── */}
                    {step === 'upload' && (
                        <>
                            <div
                                className={`import-dropzone ${dragOver ? 'drag-over' : ''}`}
                                onClick={() => fileInputRef.current?.click()}
                                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={handleFileDrop}
                            >
                                <span className="material-symbols-outlined import-dropzone-icon">upload_file</span>
                                <h3>Drop your file here, or click to browse</h3>
                                <p>Supports CSV and XLSX • Max 5MB</p>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".csv,.xlsx"
                                    style={{ display: 'none' }}
                                    onChange={handleFileSelect}
                                />
                            </div>

                            {file && (
                                <div className="import-file-selected">
                                    <span className="material-symbols-outlined" style={{ fontSize: '24px', color: 'var(--accent)' }}>description</span>
                                    <div className="file-info">
                                        <div className="file-name">{file.name}</div>
                                        <div className="file-size">{formatSize(file.size)}</div>
                                    </div>
                                    <button className="import-file-remove" onClick={removeFile}>
                                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>close</span>
                                    </button>
                                </div>
                            )}

                            <div className="import-job-selector">
                                <label>Assign all to job (optional)</label>
                                <select value={fallbackJobId} onChange={e => setFallbackJobId(e.target.value)}>
                                    <option value="">— No Job Selected —</option>
                                    {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
                                </select>
                                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                                    If your file has a "Job" column, per-row job assignments will take priority.
                                </p>
                            </div>

                            <button className="import-template-link" onClick={downloadTemplate}>
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>download</span>
                                Download CSV Template
                            </button>

                            {error && (
                                <div style={{ marginTop: '16px', padding: '10px 14px', borderRadius: 'var(--radius)', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--danger)', fontSize: '13px' }}>
                                    {error}
                                </div>
                            )}
                        </>
                    )}

                    {/* ── Step 2: Validation Preview ────────────────────── */}
                    {step === 'preview' && validation && (
                        <>
                            <div className="import-summary-cards">
                                <div className="import-summary-card valid">
                                    <span className="count">{validation.valid.length}</span>
                                    <span className="label">Valid</span>
                                </div>
                                <div className="import-summary-card duplicates">
                                    <span className="count">{validation.duplicates.length}</span>
                                    <span className="label">Duplicates</span>
                                </div>
                                <div className="import-summary-card invalid">
                                    <span className="count">{validation.invalid.length}</span>
                                    <span className="label">Invalid</span>
                                </div>
                            </div>

                            <div className="import-preview-tabs">
                                <button className={`import-preview-tab ${previewTab === 'valid' ? 'active' : ''}`} onClick={() => setPreviewTab('valid')}>
                                    ✅ Valid ({validation.valid.length})
                                </button>
                                <button className={`import-preview-tab ${previewTab === 'duplicates' ? 'active' : ''}`} onClick={() => setPreviewTab('duplicates')}>
                                    ⚠️ Duplicates ({validation.duplicates.length})
                                </button>
                                <button className={`import-preview-tab ${previewTab === 'invalid' ? 'active' : ''}`} onClick={() => setPreviewTab('invalid')}>
                                    ❌ Invalid ({validation.invalid.length})
                                </button>
                            </div>

                            {/* Valid table */}
                            {previewTab === 'valid' && (
                                validation.valid.length > 0 ? (
                                    <div className="import-preview-table-wrap">
                                        <table className="import-preview-table">
                                            <thead>
                                                <tr>
                                                    <th>Row</th>
                                                    <th>Name</th>
                                                    <th>Email</th>
                                                    <th>Phone</th>
                                                    <th>Job</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {validation.valid.map(r => (
                                                    <tr key={r.row}>
                                                        <td style={{ color: 'var(--text-secondary)' }}>{r.row}</td>
                                                        <td>{r.name}</td>
                                                        <td>{r.email}</td>
                                                        <td style={{ color: r.phone ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{r.phone || '—'}</td>
                                                        <td>
                                                            {r.job_title ? (
                                                                <span className="import-error-tag success">{r.job_title}</span>
                                                            ) : '—'}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="import-preview-empty">No valid records found</div>
                                )
                            )}

                            {/* Duplicates table */}
                            {previewTab === 'duplicates' && (
                                validation.duplicates.length > 0 ? (
                                    <div className="import-preview-table-wrap">
                                        <table className="import-preview-table">
                                            <thead>
                                                <tr>
                                                    <th>Row</th>
                                                    <th>Name</th>
                                                    <th>Email</th>
                                                    <th>Status</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {validation.duplicates.map(r => (
                                                    <tr key={r.row}>
                                                        <td style={{ color: 'var(--text-secondary)' }}>{r.row}</td>
                                                        <td>{r.name}</td>
                                                        <td>{r.email}</td>
                                                        <td><span className="import-error-tag warning">Already Exists</span></td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="import-preview-empty">No duplicates found</div>
                                )
                            )}

                            {/* Invalid table */}
                            {previewTab === 'invalid' && (
                                validation.invalid.length > 0 ? (
                                    <div className="import-preview-table-wrap">
                                        <table className="import-preview-table">
                                            <thead>
                                                <tr>
                                                    <th>Row</th>
                                                    <th>Name</th>
                                                    <th>Email</th>
                                                    <th>Errors</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {validation.invalid.map(r => (
                                                    <tr key={r.row}>
                                                        <td style={{ color: 'var(--text-secondary)' }}>{r.row}</td>
                                                        <td>{r.name || <span style={{ color: 'var(--text-secondary)' }}>—</span>}</td>
                                                        <td>{r.email || <span style={{ color: 'var(--text-secondary)' }}>—</span>}</td>
                                                        <td>
                                                            {r.errors.map((err, i) => (
                                                                <span key={i} className="import-error-tag error">{err}</span>
                                                            ))}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="import-preview-empty">No invalid records</div>
                                )
                            )}

                            {error && (
                                <div style={{ marginTop: '16px', padding: '10px 14px', borderRadius: 'var(--radius)', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--danger)', fontSize: '13px' }}>
                                    {error}
                                </div>
                            )}
                        </>
                    )}

                    {/* ── Step 3: Results ────────────────────────────────── */}
                    {step === 'results' && importResult && (
                        <div className="import-results-container">
                            <span className="material-symbols-outlined import-results-icon">check_circle</span>
                            <h3>Import Complete!</h3>
                            <p>Your candidates have been successfully imported.</p>

                            <div className="import-results-stats">
                                <div className="import-results-stat created">
                                    <span className="stat-value">{importResult.created}</span>
                                    <span className="stat-label">Created</span>
                                </div>
                                <div className="import-results-stat skipped">
                                    <span className="stat-value">{importResult.skipped}</span>
                                    <span className="stat-label">Skipped</span>
                                </div>
                                <div className="import-results-stat failed">
                                    <span className="stat-value">{importResult.failed}</span>
                                    <span className="stat-label">Failed</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="import-modal-footer">
                    {step === 'upload' && (
                        <>
                            <button className="import-btn secondary" onClick={onClose}>Cancel</button>
                            <button
                                className="import-btn primary"
                                disabled={!file || validating}
                                onClick={handleValidate}
                            >
                                {validating ? (
                                    <><span className="import-spinner" /> Validating...</>
                                ) : (
                                    <>
                                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>fact_check</span>
                                        Validate & Preview
                                    </>
                                )}
                            </button>
                        </>
                    )}

                    {step === 'preview' && (
                        <>
                            <button className="import-btn secondary" onClick={() => { setStep('upload'); setValidation(null); setError('') }}>
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>arrow_back</span>
                                Back
                            </button>
                            <button
                                className="import-btn primary"
                                disabled={!validation || validation.valid.length === 0 || importing}
                                onClick={handleImport}
                            >
                                {importing ? (
                                    <><span className="import-spinner" /> Importing...</>
                                ) : (
                                    <>
                                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>group_add</span>
                                        Import {validation?.valid.length || 0} Candidates
                                    </>
                                )}
                            </button>
                        </>
                    )}

                    {step === 'results' && (
                        <button className="import-btn primary" onClick={() => { onImportComplete(); onClose() }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>visibility</span>
                            View Candidates
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
