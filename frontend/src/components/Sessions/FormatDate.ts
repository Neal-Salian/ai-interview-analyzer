export function formatSessionDate(dateString: string | null): string {
    if (!dateString) return 'Unscheduled';

    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid Date';

    const now = new Date();
    
    // Time formatter
    const timeFormatter = new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
    
    // Date formatter
    const dateFormatter = new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });

    const isToday = 
        date.getDate() === now.getDate() &&
        date.getMonth() === now.getMonth() &&
        date.getFullYear() === now.getFullYear();

    const timeString = timeFormatter.format(date);

    if (isToday) {
        return `Today • ${timeString}`;
    }

    return `${dateFormatter.format(date)} • ${timeString}`;
}
