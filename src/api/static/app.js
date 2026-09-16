const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const suggestionChips = document.getElementById('suggestion-chips');

chatInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

function togglePanel(element) {
    element.parentElement.classList.toggle('open');
}

function sendSuggestion(text) {
    chatInput.value = text;
    sendMessage();
}

function getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function appendUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    msgDiv.innerHTML = `
        <div class="message-content">${escapeHTML(text)}</div>
        <div class="message-timestamp">${getCurrentTime()}</div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function appendAssistantMessage(text, metadata = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant-message';
    
    let formattedText = escapeHTML(text);
    formattedText = formattedText.replace(/\[AI Generated\]/g, '<span class="ai-disclosure">AI Generated</span>');
    
    let contentHTML = `
        <div class="message-content">${formattedText}</div>
        <div class="message-timestamp">${getCurrentTime()}</div>
    `;
    
    if (metadata) {
        const template = document.getElementById('decision-panel-template').content.cloneNode(true);
        
        template.querySelector('.intent-val').textContent = metadata.intent || 'N/A';
        
        const trustBadge = template.querySelector('.trust-val');
        trustBadge.textContent = metadata.trust_decision;
        trustBadge.className = 'badge trust-val'; // reset
        if (metadata.trust_decision === 'AUTO_HANDLE') trustBadge.classList.add('state-auto');
        else if (metadata.trust_decision === 'DEEP_ANALYSIS') trustBadge.classList.add('state-deep');
        else if (metadata.trust_decision === 'HUMAN_ESCALATION') trustBadge.classList.add('state-human');
        
        template.querySelector('.capability-val').textContent = metadata.capability || 'UNKNOWN';
        template.querySelector('.safety-val').textContent = metadata.safety || 'SAFE';
        
        const providerVal = template.querySelector('.provider-val');
        if (providerVal) {
            providerVal.textContent = metadata.provider ? metadata.provider : 'N/A';
        }
        
        const evidenceList = template.querySelector('.evidence-list');
        if (metadata.evidence && metadata.evidence.length > 0) {
            metadata.evidence.forEach(ev => {
                const li = document.createElement('div');
                li.className = 'evidence-item';
                const simPercent = Math.round(parseFloat(ev.similarity) * 100);
                li.innerHTML = `
                    <div class="e-intent">${escapeHTML(ev.intent)}</div>
                    <div class="e-meta">
                        <span>${escapeHTML(ev.status)}</span>
                        <span>${simPercent}% match</span>
                    </div>
                `;
                evidenceList.appendChild(li);
            });
        } else {
            evidenceList.innerHTML = '<div style="padding: 1rem; color: var(--text-secondary);">No playbooks retrieved.</div>';
        }
        
        // Populate floating cards if they exist
        const fcIntent = document.getElementById('fc-intent');
        if (fcIntent) fcIntent.textContent = metadata.intent || 'Unknown';
        
        const fcTrust = document.getElementById('fc-trust');
        if (fcTrust) {
            fcTrust.textContent = metadata.trust_decision || 'Pending';
            fcTrust.className = 'fc-value badge ' + (metadata.trust_decision || '').toLowerCase();
        }
        
        const fcCapability = document.getElementById('fc-capability');
        if (fcCapability) fcCapability.textContent = metadata.capability || 'UNKNOWN';
        
        const fcEvidence = document.getElementById('fc-evidence');
        if (fcEvidence) fcEvidence.textContent = metadata.evidence ? `${metadata.evidence.length} playbooks` : '0 playbooks';
        
        const tempDiv = document.createElement('div');
        tempDiv.appendChild(template);
        contentHTML += tempDiv.innerHTML;
    }
    
    msgDiv.innerHTML = contentHTML;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function showTyping() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant-message typing-msg';
    msgDiv.innerHTML = `
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(msgDiv);
    scrollToBottom();
    return msgDiv;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setInputState(disabled) {
    chatInput.disabled = disabled;
    sendButton.disabled = disabled;
    if (disabled) {
        suggestionChips.style.opacity = '0.5';
        suggestionChips.style.pointerEvents = 'none';
    } else {
        suggestionChips.style.opacity = '1';
        suggestionChips.style.pointerEvents = 'auto';
        chatInput.focus();
    }
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    chatInput.value = '';
    appendUserMessage(text);
    setInputState(true);
    
    const typingElement = showTyping();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: text
            })
        });
        
        typingElement.remove();
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const data = await response.json();
        appendAssistantMessage(data.response, data.metadata);
        
        // Handle demo mode badge
        const demoBadge = document.getElementById('demo-badge');
        if (data.demo_mode) {
            demoBadge.classList.remove('hidden');
        } else {
            demoBadge.classList.add('hidden');
        }
        
    } catch (error) {
        typingElement.remove();
        appendAssistantMessage('Sorry, the server encountered an error processing your request.');
        console.error('Chat error:', error);
    } finally {
        setInputState(false);
    }
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag])
    );
}

// Premium 3D parallax effect on desktop
document.addEventListener('mousemove', (e) => {
    // Only apply if prefers-reduced-motion is not reduce and screen is large
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || window.innerWidth <= 1024) return;
    
    const wrapper = document.querySelector('.chat-section-wrapper');
    if (!wrapper) return;
    
    const x = (e.clientX / window.innerWidth - 0.5) * 2; // -1 to 1
    const y = (e.clientY / window.innerHeight - 0.5) * 2; // -1 to 1
    
    // Rotate the main chat container slightly
    const chatSection = wrapper.querySelector('.chat-section');
    if (chatSection) {
        chatSection.style.transform = `rotateX(${-y * 2}deg) rotateY(${x * 2}deg)`;
    }
    
    // Translate floating cards based on their data-depth attribute
    const floatingCards = wrapper.querySelectorAll('.floating-card');
    floatingCards.forEach(card => {
        const depth = parseFloat(card.getAttribute('data-depth')) || 0.5;
        const moveX = x * 15 * depth;
        const moveY = y * 15 * depth;
        card.style.transform = `translate3d(${moveX}px, ${moveY}px, 0)`;
    });
});

// Reset transform when mouse leaves
document.addEventListener('mouseleave', () => {
    const chatSection = document.querySelector('.chat-section');
    if (chatSection) chatSection.style.transform = 'rotateX(0) rotateY(0)';
    
    const floatingCards = document.querySelectorAll('.floating-card');
    floatingCards.forEach(card => {
        card.style.transform = 'translate3d(0,0,0)';
    });
});
