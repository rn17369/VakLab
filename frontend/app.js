// WebSocket connection for real-time transcripts
let ws = null;
let activeCalls = new Map();
let currentCallSid = null;
let callStartTimes = new Map();

// DOM Elements
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const activeCallsList = document.getElementById('activeCallsList');
const noCallSelected = document.getElementById('noCallSelected');
const transcriptContainer = document.getElementById('transcriptContainer');
const transcriptMessages = document.getElementById('transcriptMessages');
const callMemberName = document.getElementById('callMemberName');
const callPhone = document.getElementById('callPhone');
const callCampaign = document.getElementById('callCampaign');
const callStatus = document.getElementById('callStatus');
const callDuration = document.getElementById('callDuration');

// Connect to WebSocket
function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ui/transcripts`;
    
    console.log('Connecting to:', wsUrl);
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus('connected', 'Connected');
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);
        handleMessage(message);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('disconnected', 'Error');
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus('disconnected', 'Disconnected');
        // Attempt to reconnect after 3 seconds
        setTimeout(connect, 3000);
    };
}

// Handle incoming WebSocket messages
function handleMessage(message) {
    switch (message.type) {
        case 'init':
            // Initialize with active calls
            message.active_calls.forEach(call => {
                activeCalls.set(call.call_sid, call);
                if (call.status === 'active') {
                    callStartTimes.set(call.call_sid, new Date(call.start_time));
                }
            });
            renderActiveCallsList();
            break;
            
        case 'call_started':
            activeCalls.set(message.call_sid, message.data);
            callStartTimes.set(message.call_sid, new Date(message.data.start_time));
            renderActiveCallsList();
            // Auto-select if it's the first call
            if (activeCalls.size === 1) {
                selectCall(message.call_sid);
            }
            break;
            
        case 'transcript_message':
            const call = activeCalls.get(message.call_sid);
            if (call) {
                call.messages.push(message.message);
                if (currentCallSid === message.call_sid) {
                    addTranscriptMessage(message.message);
                }
            }
            break;
            
        case 'call_ended':
            const endedCall = activeCalls.get(message.call_sid);
            if (endedCall) {
                endedCall.status = 'ended';
                callStartTimes.delete(message.call_sid);
                renderActiveCallsList();
                if (currentCallSid === message.call_sid) {
                    updateCallHeader(endedCall);
                }
            }
            break;
            
        case 'call_status_update':
            const updatedCall = activeCalls.get(message.call_sid);
            if (updatedCall) {
                updatedCall.status = message.status;
                Object.assign(updatedCall, message.metadata);
                renderActiveCallsList();
                if (currentCallSid === message.call_sid) {
                    updateCallHeader(updatedCall);
                }
            }
            break;
    }
}

// Update connection status indicator
function updateConnectionStatus(status, text) {
    statusIndicator.className = `status-indicator ${status}`;
    statusText.textContent = text;
}

// Render the list of active calls in the sidebar
function renderActiveCallsList() {
    if (activeCalls.size === 0) {
        activeCallsList.innerHTML = '<p class="empty-state">No active calls</p>';
        return;
    }
    
    activeCallsList.innerHTML = '';
    activeCalls.forEach((call, callSid) => {
        const card = document.createElement('div');
        card.className = `call-card ${currentCallSid === callSid ? 'active' : ''}`;
        card.onclick = () => selectCall(callSid);
        
        const memberName = call.member_data?.member_first_name || 'Unknown';
        const memberLastName = call.member_data?.member_last_name || '';
        const phone = call.member_data?.phone_number || 'N/A';
        const campaign = call.member_data?.campaign_name || 'N/A';
        
        card.innerHTML = `
            <div class="call-card-name">${memberName} ${memberLastName}</div>
            <div class="call-card-meta">${phone}</div>
            <div class="call-card-meta">${campaign}</div>
            <span class="call-card-status ${call.status}">${call.status.toUpperCase()}</span>
        `;
        
        activeCallsList.appendChild(card);
    });
}

// Select a call to view its transcript
function selectCall(callSid) {
    currentCallSid = callSid;
    const call = activeCalls.get(callSid);
    
    if (!call) return;
    
    // Update UI
    noCallSelected.style.display = 'none';
    transcriptContainer.style.display = 'flex';
    
    // Update call header
    updateCallHeader(call);
    
    // Render messages
    transcriptMessages.innerHTML = '';
    call.messages.forEach(msg => addTranscriptMessage(msg));
    
    // Update sidebar selection
    renderActiveCallsList();
    
    // Start duration timer if call is active
    if (call.status === 'active') {
        startDurationTimer(callSid);
    }
}

// Update call header information
function updateCallHeader(call) {
    const memberName = call.member_data?.member_first_name || 'Unknown';
    const memberLastName = call.member_data?.member_last_name || '';
    const phone = call.member_data?.phone_number || 'N/A';
    const campaign = call.member_data?.campaign_name || 'N/A';
    
    callMemberName.textContent = `${memberName} ${memberLastName}`;
    callPhone.textContent = phone;
    callCampaign.textContent = campaign;
    callStatus.textContent = call.status.toUpperCase();
    callStatus.className = `call-status-badge ${call.status}`;
}

// Add a transcript message to the display
function addTranscriptMessage(message) {
    const messageDiv = document.createElement('div');
    const speakerClass = message.speaker.toLowerCase();
    messageDiv.className = `message ${speakerClass}`;
    
    // Emoji for avatar
    let emoji = '🤖';
    if (message.speaker === 'Customer') emoji = '👤';
    if (message.speaker === 'System') emoji = '⚙️';
    
    const timestamp = new Date(message.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    messageDiv.innerHTML = `
        <div class="message-avatar ${speakerClass}">${emoji}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-speaker">${message.speaker}</span>
                <span class="message-timestamp">${timestamp}</span>
            </div>
            <div class="message-text">${escapeHtml(message.text)}</div>
        </div>
    `;
    
    transcriptMessages.appendChild(messageDiv);
    transcriptMessages.scrollTop = transcriptMessages.scrollHeight;
}

// Start duration timer for active call
function startDurationTimer(callSid) {
    const updateDuration = () => {
        if (currentCallSid !== callSid || !callStartTimes.has(callSid)) {
            return;
        }
        
        const startTime = callStartTimes.get(callSid);
        const now = new Date();
        const durationMs = now - startTime;
        const seconds = Math.floor(durationMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const displaySeconds = seconds % 60;
        
        callDuration.textContent = `${String(minutes).padStart(2, '0')}:${String(displaySeconds).padStart(2, '0')}`;
        
        requestAnimationFrame(updateDuration);
    };
    
    requestAnimationFrame(updateDuration);
}

// Utility: Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
window.addEventListener('load', () => {
    connect();
    
    // Send periodic pings to keep connection alive
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
});
