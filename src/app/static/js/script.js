function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

document.addEventListener('DOMContentLoaded', function() {
    const socket = io();

    socket.on('connect', function() {
        console.log('Connected to WebSocket');
    });

    socket.on('queue_updated', function(data) {
        console.log('Queue updated:', data.message);
        window.location.reload();
    });

    socket.on('agent_status_updated', function(data) {
        console.log('Agent status updated:', data);
        const statusBadge = document.getElementById('agent-status-badge');
        if (statusBadge) {
            statusBadge.textContent = `Status: ${data.status.charAt(0).toUpperCase() + data.status.slice(1)}`;
        }
    });

    socket.on('metrics_updated', function(data) {
        console.log('Metrics updated:', data);
        const servedTodayEl = document.getElementById('served-today');
        const avgTimeEl = document.getElementById('avg-time');
        if (servedTodayEl) {
            servedTodayEl.textContent = data.metrics.citizens_served_today;
        }
        if (avgTimeEl) {
            avgTimeEl.textContent = `${data.metrics.avg_service_time} min`;
        }
    });

    const statusSelect = document.getElementById('status-select');
    if (statusSelect) {
        statusSelect.addEventListener('change', function(e) {
            const newStatus = e.target.value;

            fetch('/agent/api/status', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({ status: newStatus })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update the status badge text
                    const statusBadge = document.getElementById('agent-status-badge');
                    if (statusBadge) {
                        const displayStatus = newStatus.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                        statusBadge.textContent = `Status: ${displayStatus}`;
                        
                        // Update badge color based on status
                        statusBadge.className = 'badge fs-6 ' + getStatusBadgeClass(newStatus);
                    }
                    
                    // Show success message
                    showStatusMessage(data.message, 'success');
                    console.log(data.message);
                } else {
                    showStatusMessage(data.message || 'Failed to update status', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showStatusMessage('Failed to update status. Please try again.', 'error');
            });
        });
    }

    const completeServiceBtn = document.getElementById('completeServiceBtn');
    if (completeServiceBtn) {
        completeServiceBtn.addEventListener('click', function() {
            const queueId = this.dataset.queueId;

            fetch('/api/queue/complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                },
                body: JSON.stringify({ queue_id: queueId })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message) });
                }
                return response.json();
            })
            .then(data => {
                console.log(data.message);
                // Page will reload via websocket event
            })
            .catch(error => {
                console.error('Error:', error);
                alert(`Failed to complete service: ${error.message}`);
            });
        });
    }

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            fetch('/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                }
            })
            .then(response => {
                if (response.ok) {
                    window.location.href = '/login';
                }
            });
        });
    }

    const callNextBtn = document.getElementById('callNextBtn');
    if (callNextBtn) {
        callNextBtn.addEventListener('click', function() {
            fetch('/agent/api/queue/next', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-TOKEN': getCsrfToken()
                }
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message) });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    showStatusMessage(`Called citizen with ticket: ${data.ticket_number}`, 'success');
                    // Refresh the page after a short delay to show the message
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    showStatusMessage(data.message || 'Failed to call next citizen', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showStatusMessage(`Error: ${error.message}`, 'error');
            });
        });
    }
});

// Helper function to get status badge color class
function getStatusBadgeClass(status) {
    switch(status) {
        case 'available':
            return 'bg-success';
        case 'busy':
            return 'bg-warning';
        case 'on_break':
            return 'bg-info';
        case 'offline':
            return 'bg-secondary';
        default:
            return 'bg-secondary';
    }
}

// Helper function to show status messages
function showStatusMessage(message, type) {
    // Create or update status message element
    let messageEl = document.getElementById('status-message');
    if (!messageEl) {
        messageEl = document.createElement('div');
        messageEl.id = 'status-message';
        messageEl.style.position = 'fixed';
        messageEl.style.top = '20px';
        messageEl.style.right = '20px';
        messageEl.style.zIndex = '9999';
        messageEl.style.padding = '12px 20px';
        messageEl.style.borderRadius = '4px';
        messageEl.style.fontWeight = 'bold';
        messageEl.style.minWidth = '250px';
        messageEl.style.textAlign = 'center';
        document.body.appendChild(messageEl);
    }
    
    // Set message and styling
    messageEl.textContent = message;
    messageEl.className = type === 'success' ? 'alert alert-success' : 'alert alert-danger';
    messageEl.style.display = 'block';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        if (messageEl) {
            messageEl.style.display = 'none';
        }
    }, 3000);
}
