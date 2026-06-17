interface EmptyStateProps {
    hasActiveFilter: boolean;
    hasSearchQuery: boolean;
    onClearFilters: () => void;
    onCreateSession: () => void;
}

export function EmptyState({ hasActiveFilter, hasSearchQuery, onClearFilters, onCreateSession }: EmptyStateProps) {
    const icon = hasSearchQuery ? 'search_off' : 'event_busy';
    
    let title = 'No sessions yet';
    let description = 'Create your first interview session to get started.';

    if (hasSearchQuery) {
        title = 'No matching sessions';
        description = 'No sessions match your search. Try adjusting your search terms.';
    } else if (hasActiveFilter) {
        title = 'No sessions match your filters';
        description = 'Try adjusting your filters or create a new session.';
    }

    return (
        <div className="empty-state" role="status" aria-label={title}>
            <div className="empty-state__icon-wrap">
                <span className="material-symbols-outlined empty-state__icon" aria-hidden="true">
                    {icon}
                </span>
            </div>
            <h3 className="empty-state__title">{title}</h3>
            <p className="empty-state__desc">{description}</p>
            <div className="empty-state__actions">
                {(hasActiveFilter || hasSearchQuery) && (
                    <button
                        className="empty-state__btn empty-state__btn--secondary"
                        onClick={onClearFilters}
                        aria-label="Clear all filters and search"
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }} aria-hidden="true">filter_alt_off</span>
                        Clear Filters
                    </button>
                )}
                <button
                    className="empty-state__btn empty-state__btn--primary"
                    onClick={onCreateSession}
                    aria-label="Create a new session"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }} aria-hidden="true">add</span>
                    Create Session
                </button>
            </div>
        </div>
    );
}
