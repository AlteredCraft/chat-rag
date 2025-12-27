/**
 * Frontend Logger Utility (shared with script.js pattern)
 * Provides structured logging with session tracking for debugging
 */
const SettingsLogger = {
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
    SettingsLogger.info('Settings page initializing');

    // Tab navigation
    const TAB_STORAGE_KEY = 'chat-rag-settings-tab';
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    function switchTab(tabId) {
        tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === tabId);
        });
        localStorage.setItem(TAB_STORAGE_KEY, tabId);
        SettingsLogger.debug('Tab switched', { tab: tabId });
    }

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Restore last active tab
    const savedTab = localStorage.getItem(TAB_STORAGE_KEY);
    if (savedTab && document.querySelector(`[data-tab="${savedTab}"]`)) {
        switchTab(savedTab);
    }

    const modelSelect = document.getElementById('model-select');
    const loadingIndicator = document.getElementById('loading-indicator');
    const modelDetails = document.getElementById('model-details');
    const freeOnlyFilter = document.getElementById('free-only-filter');

    const STORAGE_KEY = 'chat-rag-selected-model';
    const FILTER_STORAGE_KEY = 'chat-rag-free-filter';
    const DEFAULT_MODEL = 'openai/gpt-3.5-turbo';

    // Prompt selection elements and constants
    const PROMPT_STORAGE_KEY = 'chat-rag-selected-prompt';
    const DEFAULT_PROMPT = 'default_system_prompt';
    const promptSelect = document.getElementById('prompt-select');
    const promptLoadingIndicator = document.getElementById('prompt-loading-indicator');
    const promptDetails = document.getElementById('prompt-details');

    function isFreeModel(model) {
        const pricing = model.pricing || {};
        const promptPrice = parseFloat(pricing.prompt) || 0;
        const completionPrice = parseFloat(pricing.completion) || 0;
        return promptPrice === 0 && completionPrice === 0;
    }

    let modelsData = [];
    let promptsData = [];

    // Restore filter state and load models
    freeOnlyFilter.checked = localStorage.getItem(FILTER_STORAGE_KEY) === 'true';
    loadModels();
    loadPrompts();

    async function loadModels() {
        SettingsLogger.info('Loading models from API');
        const startTime = performance.now();
        loadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/models');
            if (!response.ok) {
                SettingsLogger.error('Models API returned error', { status: response.status });
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            modelsData = data.data || [];

            const elapsed = performance.now() - startTime;
            SettingsLogger.info('Models loaded successfully', {
                count: modelsData.length,
                loadTime_ms: elapsed.toFixed(2)
            });

            populateModelSelect(modelsData);
            restoreSelectedModel();

        } catch (error) {
            const elapsed = performance.now() - startTime;
            SettingsLogger.error('Failed to load models', {
                error: error.message,
                loadTime_ms: elapsed.toFixed(2)
            });
            modelSelect.innerHTML = '<option value="">Failed to load models</option>';
        } finally {
            loadingIndicator.classList.remove('active');
            modelSelect.disabled = false;
        }
    }

    function populateModelSelect(models) {
        SettingsLogger.debug('Populating model select dropdown');
        modelSelect.innerHTML = '';

        // Apply free filter if enabled
        const showFreeOnly = freeOnlyFilter.checked;
        const filteredModels = showFreeOnly ? models.filter(isFreeModel) : models;

        if (filteredModels.length === 0) {
            modelSelect.innerHTML = '<option value="">No models match filter</option>';
            return;
        }

        // Group models by provider
        const grouped = {};
        filteredModels.forEach(model => {
            const provider = model.id.split('/')[0] || 'Other';
            if (!grouped[provider]) {
                grouped[provider] = [];
            }
            grouped[provider].push(model);
        });

        // Sort providers alphabetically
        const sortedProviders = Object.keys(grouped).sort();

        sortedProviders.forEach(provider => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = formatProviderName(provider);

            grouped[provider].forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name || model.id;
                option.dataset.contextLength = model.context_length || 0;
                option.dataset.pricing = JSON.stringify(model.pricing || {});
                optgroup.appendChild(option);
            });

            modelSelect.appendChild(optgroup);
        });

        SettingsLogger.debug('Model select populated', {
            providers: sortedProviders.length,
            totalModels: filteredModels.length,
            filtered: showFreeOnly
        });
    }

    function formatProviderName(provider) {
        // Capitalize and clean up provider names
        const nameMap = {
            'openai': 'OpenAI',
            'anthropic': 'Anthropic',
            'google': 'Google',
            'meta-llama': 'Meta Llama',
            'mistralai': 'Mistral AI',
            'cohere': 'Cohere',
            'deepseek': 'DeepSeek',
            'qwen': 'Qwen'
        };
        return nameMap[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
    }

    function restoreSelectedModel() {
        const savedModel = localStorage.getItem(STORAGE_KEY);
        SettingsLogger.debug('Restoring selected model', { savedModel: savedModel || '(none)' });

        if (savedModel && modelSelect.querySelector(`option[value="${savedModel}"]`)) {
            modelSelect.value = savedModel;
            SettingsLogger.info('Restored previously saved model', { model: savedModel });
        } else {
            // Try to select default model
            if (modelSelect.querySelector(`option[value="${DEFAULT_MODEL}"]`)) {
                modelSelect.value = DEFAULT_MODEL;
                SettingsLogger.info('Using default model (no saved selection)', { model: DEFAULT_MODEL });
            } else {
                SettingsLogger.warn('Default model not available in model list', { defaultModel: DEFAULT_MODEL });
            }
        }
        updateModelDetails();
    }

    function updateModelDetails() {
        const selectedOption = modelSelect.options[modelSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            modelDetails.classList.remove('visible');
            return;
        }

        const model = modelsData.find(m => m.id === selectedOption.value);
        if (!model) {
            modelDetails.classList.remove('visible');
            return;
        }

        const contextLength = model.context_length || 'N/A';
        const pricing = model.pricing || {};
        const promptPrice = pricing.prompt ? `$${(parseFloat(pricing.prompt) * 1000000).toFixed(2)}/M tokens` : 'N/A';
        const completionPrice = pricing.completion ? `$${(parseFloat(pricing.completion) * 1000000).toFixed(2)}/M tokens` : 'N/A';

        const description = model.description || '';
        const architecture = model.architecture || {};
        const inputModalities = architecture.input_modalities || [];
        const outputModalities = architecture.output_modalities || [];
        const supportedParams = model.supported_parameters || [];

        modelDetails.innerHTML = `
            ${description ? `<div class="detail-row description"><span class="detail-value">${description}</span></div>` : ''}
            <div class="detail-row">
                <span class="detail-label">Model ID:</span>
                <span class="detail-value">${model.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Context Length:</span>
                <span class="detail-value">${contextLength.toLocaleString()} tokens</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Prompt Pricing:</span>
                <span class="detail-value">${promptPrice}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Completion Pricing:</span>
                <span class="detail-value">${completionPrice}</span>
            </div>
            ${inputModalities.length ? `<div class="detail-row"><span class="detail-label">Modality-in:</span><div class="tags">${inputModalities.map(m => `<span class="tag">${m}</span>`).join('')}</div></div>` : ''}
            ${outputModalities.length ? `<div class="detail-row"><span class="detail-label">Modality-out:</span><div class="tags">${outputModalities.map(m => `<span class="tag">${m}</span>`).join('')}</div></div>` : ''}
            ${supportedParams.length ? `<div class="detail-row"><span class="detail-label">Parameters:</span><div class="tags">${supportedParams.map(p => `<span class="tag">${p}</span>`).join('')}</div></div>` : ''}
        `;
        modelDetails.classList.add('visible');
    }

    modelSelect.addEventListener('change', () => {
        const selectedModel = modelSelect.value;
        const previousModel = localStorage.getItem(STORAGE_KEY);

        if (selectedModel) {
            localStorage.setItem(STORAGE_KEY, selectedModel);
            SettingsLogger.info('Model selection changed', {
                previousModel: previousModel || '(none)',
                newModel: selectedModel
            });
            updateModelDetails();
        }
    });

    freeOnlyFilter.addEventListener('change', () => {
        localStorage.setItem(FILTER_STORAGE_KEY, freeOnlyFilter.checked);
        SettingsLogger.info('Free filter toggled', { enabled: freeOnlyFilter.checked });
        populateModelSelect(modelsData);
        restoreSelectedModel();
    });

    // ===== Prompt Selection Functions =====

    async function loadPrompts() {
        SettingsLogger.info('Loading prompts from API');
        const startTime = performance.now();
        promptLoadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/prompts');
            if (!response.ok) {
                SettingsLogger.error('Prompts API returned error', { status: response.status });
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            promptsData = data.data || [];

            const elapsed = performance.now() - startTime;
            SettingsLogger.info('Prompts loaded successfully', {
                count: promptsData.length,
                loadTime_ms: elapsed.toFixed(2)
            });

            populatePromptSelect(promptsData);
            restoreSelectedPrompt();

        } catch (error) {
            const elapsed = performance.now() - startTime;
            SettingsLogger.error('Failed to load prompts', {
                error: error.message,
                loadTime_ms: elapsed.toFixed(2)
            });
            promptSelect.innerHTML = '<option value="">Failed to load prompts</option>';
        } finally {
            promptLoadingIndicator.classList.remove('active');
            promptSelect.disabled = false;
        }
    }

    function populatePromptSelect(prompts) {
        SettingsLogger.debug('Populating prompt select dropdown');
        promptSelect.innerHTML = '';

        if (prompts.length === 0) {
            promptSelect.innerHTML = '<option value="">No prompts available</option>';
            return;
        }

        prompts.forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt.id;
            option.textContent = prompt.title || prompt.id;
            promptSelect.appendChild(option);
        });

        SettingsLogger.debug('Prompt select populated', { totalPrompts: prompts.length });
    }

    function restoreSelectedPrompt() {
        const savedPrompt = localStorage.getItem(PROMPT_STORAGE_KEY);
        SettingsLogger.debug('Restoring selected prompt', { savedPrompt: savedPrompt || '(none)' });

        if (savedPrompt && promptSelect.querySelector(`option[value="${savedPrompt}"]`)) {
            promptSelect.value = savedPrompt;
            SettingsLogger.info('Restored previously saved prompt', { prompt: savedPrompt });
        } else if (promptSelect.querySelector(`option[value="${DEFAULT_PROMPT}"]`)) {
            promptSelect.value = DEFAULT_PROMPT;
            localStorage.setItem(PROMPT_STORAGE_KEY, DEFAULT_PROMPT);
            SettingsLogger.info('Using default prompt (no saved selection)', { prompt: DEFAULT_PROMPT });
        }
        updatePromptDetails();
    }

    function updatePromptDetails() {
        const selectedPrompt = promptsData.find(p => p.id === promptSelect.value);
        if (!selectedPrompt) {
            promptDetails.classList.remove('visible');
            return;
        }

        promptDetails.innerHTML = `
            ${selectedPrompt.description ? `<div class="detail-row description"><span class="detail-value">${selectedPrompt.description}</span></div>` : ''}
            <div class="detail-row">
                <span class="detail-label">Prompt ID:</span>
                <span class="detail-value">${selectedPrompt.id}</span>
            </div>
        `;
        promptDetails.classList.add('visible');
    }

    promptSelect.addEventListener('change', () => {
        const selectedPrompt = promptSelect.value;
        const previousPrompt = localStorage.getItem(PROMPT_STORAGE_KEY);

        if (selectedPrompt) {
            localStorage.setItem(PROMPT_STORAGE_KEY, selectedPrompt);
            SettingsLogger.info('Prompt selection changed', {
                previousPrompt: previousPrompt || '(none)',
                newPrompt: selectedPrompt
            });
            updatePromptDetails();
        }
    });

    SettingsLogger.info('Settings page initialized successfully');
});
