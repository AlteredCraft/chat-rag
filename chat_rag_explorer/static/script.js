/**
 * Frontend Logger Utility
 * Provides structured logging with session tracking for debugging
 */
const AppLogger = {
    sessionId: localStorage.getItem('chat-rag-session-id') || (() => {
        const id = 'sess_' + Math.random().toString(36).substring(2, 10);
        localStorage.setItem('chat-rag-session-id', id);
        return id;
    })(),

    _format(level, message, data) {
        const timestamp = new Date().toISOString();
        const prefix = `[${timestamp}] [${this.sessionId}] ${level.toUpperCase()}:`;
        return { prefix, message, data };
    },

    debug(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('debug', message, data);
        if (d) console.debug(prefix, msg, d);
        else console.debug(prefix, msg);
    },

    info(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('info', message, data);
        if (d) console.info(prefix, msg, d);
        else console.info(prefix, msg);
    },

    warn(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('warn', message, data);
        if (d) console.warn(prefix, msg, d);
        else console.warn(prefix, msg);
    },

    error(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('error', message, data);
        if (d) console.error(prefix, msg, d);
        else console.error(prefix, msg);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    AppLogger.info('Chat application initializing');

    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const submitButton = chatForm.querySelector('button');
    const settingsLink = document.querySelector('.settings-link');
    const confirmModal = document.getElementById('confirm-modal');
    const modalCancel = document.getElementById('modal-cancel');
    const modalOk = document.getElementById('modal-ok');

    // Confirm before navigating to settings (resets chat)
    if (settingsLink && confirmModal) {
        settingsLink.addEventListener('click', (e) => {
            e.preventDefault();
            confirmModal.classList.add('visible');
        });

        modalCancel.addEventListener('click', () => {
            confirmModal.classList.remove('visible');
        });

        modalOk.addEventListener('click', () => {
            window.location.href = settingsLink.href;
        });

        confirmModal.addEventListener('click', (e) => {
            if (e.target === confirmModal) {
                confirmModal.classList.remove('visible');
            }
        });
    }

    // Clear chat button
    const clearChatBtn = document.getElementById('clear-chat-btn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', () => {
            clearChat();
        });
    }

    function clearChat() {
        AppLogger.info('Clearing chat');

        // Clear UI
        chatHistory.innerHTML = '';

        // Reset conversation history (keep system message)
        conversationHistory = [
            { role: 'system', content: 'You are a helpful assistant.' }
        ];

        // Reset session metrics
        sessionMetrics = {
            prompt_tokens: 0,
            completion_tokens: 0,
            total_tokens: 0
        };

        // Update metrics display
        document.getElementById('metric-prompt-tokens').textContent = '0';
        document.getElementById('metric-completion-tokens').textContent = '0';
        document.getElementById('metric-total-tokens').textContent = '0';
        document.getElementById('total-prompt-tokens').textContent = '0';
        document.getElementById('total-completion-tokens').textContent = '0';
        document.getElementById('total-total-tokens').textContent = '0';

        messageInput.focus();
    }

    const STORAGE_KEY = 'chat-rag-selected-model';
    const DEFAULT_MODEL = 'openai/gpt-3.5-turbo';

    // Parameter controls
    const temperatureSlider = document.getElementById('temperature-slider');
    const temperatureValue = document.getElementById('temperature-value');
    const temperatureControl = document.getElementById('temperature-control');
    const temperatureHint = document.getElementById('temperature-hint');
    const topPSlider = document.getElementById('top-p-slider');
    const topPValue = document.getElementById('top-p-value');
    const topPControl = document.getElementById('top-p-control');
    const topPHint = document.getElementById('top-p-hint');

    // Track supported parameters for current model
    let supportedParams = [];

    // Get model from localStorage or use default
    function getCurrentModel() {
        const model = localStorage.getItem(STORAGE_KEY) || DEFAULT_MODEL;
        return model;
    }

    // Fetch model metadata and update parameter controls
    async function updateParameterControls() {
        const currentModel = getCurrentModel();
        AppLogger.debug('Fetching model metadata for parameter controls', { model: currentModel });

        try {
            const response = await fetch('/api/models');
            const data = await response.json();
            const models = data.data || [];
            const model = models.find(m => m.id === currentModel);

            if (model && model.supported_parameters) {
                supportedParams = model.supported_parameters;
                AppLogger.debug('Model supported parameters', { params: supportedParams });
            } else {
                supportedParams = [];
                AppLogger.debug('No supported parameters found for model');
            }

            // Update temperature control
            const tempSupported = supportedParams.includes('temperature');
            if (tempSupported) {
                temperatureControl.classList.remove('disabled');
                temperatureSlider.disabled = false;
                temperatureHint.textContent = '';
            } else {
                temperatureControl.classList.add('disabled');
                temperatureSlider.disabled = true;
                temperatureHint.textContent = 'Not supported by this model';
            }

            // Update top_p control
            const topPSupported = supportedParams.includes('top_p');
            if (topPSupported) {
                topPControl.classList.remove('disabled');
                topPSlider.disabled = false;
                topPHint.textContent = '';
            } else {
                topPControl.classList.add('disabled');
                topPSlider.disabled = true;
                topPHint.textContent = 'Not supported by this model';
            }
        } catch (error) {
            AppLogger.error('Failed to fetch model metadata', { error: error.message });
        }
    }

    // Update slider value displays
    temperatureSlider.addEventListener('input', () => {
        temperatureValue.textContent = parseFloat(temperatureSlider.value).toFixed(1);
    });

    topPSlider.addEventListener('input', () => {
        topPValue.textContent = parseFloat(topPSlider.value).toFixed(2);
    });

    // Listen for model changes from settings page
    window.addEventListener('storage', (e) => {
        if (e.key === STORAGE_KEY) {
            AppLogger.info('Model changed via storage event', { newModel: e.newValue });
            document.getElementById('metric-model').textContent = e.newValue || DEFAULT_MODEL;
            updateParameterControls();
        }
    });

    // Display current model on load
    const currentModel = getCurrentModel();
    document.getElementById('metric-model').textContent = currentModel;
    AppLogger.info('Current model loaded', { model: currentModel });

    // Initialize parameter controls
    updateParameterControls();

    // Session-wide metrics
    let sessionMetrics = {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0
    };

    // Conversation history
    let conversationHistory = [
        { role: 'system', content: 'You are a helpful assistant.' }
    ];

    // Configure marked for better chat-style breaks
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const message = messageInput.value.trim();
        if (!message) return;

        const model = getCurrentModel();
        const requestStartTime = performance.now();

        AppLogger.info('Chat request initiated', {
            model: model,
            messageLength: message.length,
            conversationTurns: conversationHistory.length
        });

        // Clear input
        messageInput.value = '';
        messageInput.disabled = true;
        submitButton.disabled = true;

        // Add user message to history
        conversationHistory.push({ role: 'user', content: message });

        // Add user message UI
        appendMessage('user', message);

        // Add empty bot message container
        const botMessageContent = appendMessage('bot', '');
        let messageBuffer = '';
        let chunkCount = 0;
        let firstChunkTime = null;

        try {
            // Build request body with optional parameters
            const requestBody = {
                messages: conversationHistory,
                model: model
            };

            // Only include parameters if they're supported by the model
            if (supportedParams.includes('temperature')) {
                requestBody.temperature = parseFloat(temperatureSlider.value);
            }
            if (supportedParams.includes('top_p')) {
                requestBody.top_p = parseFloat(topPSlider.value);
            }

            AppLogger.debug('Sending POST /api/chat', {
                contextLength: conversationHistory.length,
                model: model,
                temperature: requestBody.temperature,
                top_p: requestBody.top_p
            });

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                AppLogger.error('Chat API returned error', { status: response.status });
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            AppLogger.debug('Stream started, processing chunks');

            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                chunkCount++;

                // Track time to first chunk
                if (firstChunkTime === null && chunk.length > 0) {
                    firstChunkTime = performance.now();
                    const ttfc = firstChunkTime - requestStartTime;
                    AppLogger.debug('Time to first chunk', { ttfc_ms: ttfc.toFixed(2) });
                }

                // Check for metadata marker
                if (chunk.startsWith('__METADATA__:')) {
                    try {
                        const metadataJson = chunk.replace('__METADATA__:', '');
                        const usageData = JSON.parse(metadataJson);
                        AppLogger.info('Token usage received', usageData);
                        updateMetrics(usageData);
                    } catch (parseError) {
                        AppLogger.error('Failed to parse metadata', { error: parseError.message, chunk: chunk });
                    }
                    continue; // Don't render metadata in chat
                }

                messageBuffer += chunk;

                // Parse markdown and sanitize
                const html = marked.parse(messageBuffer);
                botMessageContent.innerHTML = DOMPurify.sanitize(html);

                // Auto-scroll to bottom
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }

            const totalTime = performance.now() - requestStartTime;
            AppLogger.info('Chat response completed', {
                chunks: chunkCount,
                responseLength: messageBuffer.length,
                totalTime_ms: totalTime.toFixed(2)
            });

            // Add bot message to history
            if (messageBuffer) {
                conversationHistory.push({ role: 'assistant', content: messageBuffer });
            }

        } catch (error) {
            const totalTime = performance.now() - requestStartTime;
            AppLogger.error('Chat request failed', {
                error: error.message,
                totalTime_ms: totalTime.toFixed(2),
                chunksReceived: chunkCount
            });
            botMessageContent.innerHTML += ` <span style="color: red;">[Error: ${error.message}]</span>`;
        } finally {
            messageInput.disabled = false;
            submitButton.disabled = false;
            messageInput.focus();
        }
    });

    function updateMetrics(data) {
        AppLogger.debug('Updating metrics display', data);

        // Update Last Interaction
        if (data.model) document.getElementById('metric-model').textContent = data.model;
        if (data.prompt_tokens) document.getElementById('metric-prompt-tokens').textContent = data.prompt_tokens;
        if (data.completion_tokens) document.getElementById('metric-completion-tokens').textContent = data.completion_tokens;
        if (data.total_tokens) document.getElementById('metric-total-tokens').textContent = data.total_tokens;

        // Update Session Totals
        if (data.prompt_tokens) sessionMetrics.prompt_tokens += data.prompt_tokens;
        if (data.completion_tokens) sessionMetrics.completion_tokens += data.completion_tokens;
        if (data.total_tokens) sessionMetrics.total_tokens += data.total_tokens;

        document.getElementById('total-prompt-tokens').textContent = sessionMetrics.prompt_tokens;
        document.getElementById('total-completion-tokens').textContent = sessionMetrics.completion_tokens;
        document.getElementById('total-total-tokens').textContent = sessionMetrics.total_tokens;

        AppLogger.info('Session metrics updated', {
            sessionTotals: { ...sessionMetrics }
        });
    }

    function appendMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';
        
        if (role === 'user') {
            contentDiv.textContent = text;
        } else {
            // For bot, if there's initial text, parse it as markdown
            const html = marked.parse(text || '');
            contentDiv.innerHTML = DOMPurify.sanitize(html);
        }
        
        messageDiv.appendChild(contentDiv);
        chatHistory.appendChild(messageDiv);
        
        // Scroll to bottom
        chatHistory.scrollTop = chatHistory.scrollHeight;

        return contentDiv; // Return content div so we can append to it
    }

    AppLogger.info('Chat application initialized successfully', {
        sessionId: AppLogger.sessionId,
        model: getCurrentModel()
    });
});
