/**
 * Dumont Cloud - VS Code Failover Status Widget
 *
 * Injetado via Nginx sub_filter no code-server
 * Mostra status GPU/CPU no canto superior direito
 * Atualiza automaticamente e notifica sobre failover
 */

(function() {
    'use strict';

    const POLL_INTERVAL = 2000; // 2 seconds
    const API_ENDPOINT = '/api/failover/status';

    // State
    let currentState = {
        mode: 'gpu',       // 'gpu' | 'cpu' | 'failover'
        gpuName: 'GPU',
        cpuName: 'CPU Standby',
        lastSync: null,
        syncCount: 0,
        healthy: true
    };

    // Create widget container
    function createWidget() {
        const container = document.createElement('div');
        container.id = 'dumont-failover-widget';
        container.innerHTML = `
            <div class="dumont-widget-inner">
                <div class="dumont-status-indicator">
                    <span class="dumont-status-dot"></span>
                    <span class="dumont-status-text">GPU</span>
                </div>
                <div class="dumont-status-details">
                    <span class="dumont-sync-count">0 syncs</span>
                </div>
            </div>
            <div class="dumont-notification" style="display: none;">
                <div class="dumont-notification-content">
                    <span class="dumont-notification-icon">⚠️</span>
                    <span class="dumont-notification-text"></span>
                </div>
            </div>
        `;
        document.body.appendChild(container);
        return container;
    }

    // Update widget UI
    function updateWidget(state) {
        const widget = document.getElementById('dumont-failover-widget');
        if (!widget) return;

        const dot = widget.querySelector('.dumont-status-dot');
        const text = widget.querySelector('.dumont-status-text');
        const details = widget.querySelector('.dumont-status-details');
        const syncCount = widget.querySelector('.dumont-sync-count');

        // Update based on mode
        switch (state.mode) {
            case 'gpu':
                dot.className = 'dumont-status-dot dumont-status-gpu';
                text.textContent = state.gpuName || 'GPU';
                widget.classList.remove('dumont-failover', 'dumont-cpu');
                widget.classList.add('dumont-gpu');
                break;

            case 'cpu':
                dot.className = 'dumont-status-dot dumont-status-cpu';
                text.textContent = state.cpuName || 'CPU Standby';
                widget.classList.remove('dumont-failover', 'dumont-gpu');
                widget.classList.add('dumont-cpu');
                break;

            case 'failover':
                dot.className = 'dumont-status-dot dumont-status-failover';
                text.textContent = 'Failover...';
                widget.classList.remove('dumont-gpu', 'dumont-cpu');
                widget.classList.add('dumont-failover');
                break;
        }

        // Update sync count
        if (state.syncCount > 0) {
            syncCount.textContent = `${state.syncCount} syncs`;
            details.style.display = 'block';
        }

        // Show/hide based on health
        if (!state.healthy) {
            dot.classList.add('dumont-status-warning');
        } else {
            dot.classList.remove('dumont-status-warning');
        }
    }

    // Show notification
    function showNotification(message, type = 'info') {
        const widget = document.getElementById('dumont-failover-widget');
        if (!widget) return;

        const notification = widget.querySelector('.dumont-notification');
        const notificationText = widget.querySelector('.dumont-notification-text');
        const notificationIcon = widget.querySelector('.dumont-notification-icon');

        // Set icon based on type
        switch (type) {
            case 'warning':
                notificationIcon.textContent = '⚠️';
                notification.className = 'dumont-notification dumont-notification-warning';
                break;
            case 'error':
                notificationIcon.textContent = '❌';
                notification.className = 'dumont-notification dumont-notification-error';
                break;
            case 'success':
                notificationIcon.textContent = '✅';
                notification.className = 'dumont-notification dumont-notification-success';
                break;
            default:
                notificationIcon.textContent = 'ℹ️';
                notification.className = 'dumont-notification dumont-notification-info';
        }

        notificationText.textContent = message;
        notification.style.display = 'block';

        // Auto-hide after 10 seconds for non-error notifications
        if (type !== 'error') {
            setTimeout(() => {
                notification.style.display = 'none';
            }, 10000);
        }
    }

    // Handle failover event
    function handleFailover(oldState, newState) {
        console.log('[Dumont] Failover detected:', oldState.mode, '->', newState.mode);

        if (oldState.mode === 'gpu' && newState.mode === 'cpu') {
            showNotification(
                `GPU falhou! Trocando para ${newState.cpuName}. Seus arquivos estão salvos.`,
                'warning'
            );

            // Play sound if available
            try {
                const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleQ4BJKbYv5wlBw+B0dGrdRcQMpHI05p1HgsmhdPSrXEfAC2N0dauaCIAMJHR1K9mIgAyjdDSsmUjADOL0NKxZSMANI3Q0bBkIwA0jdDRr2QjADSNz9GuZCMANY3P0a1jIwA1jc/RrWMjADWNz9GtYyMAN4zP0axhIwA4jM/SrF8kADqKz9KsXSQAO4rP0qxdJAA7is/SrFwkADuLz9KrXCQAO4vP0qtcJAA8jM/SqV0kAD2Mz9OoXiQAPozO06leJAA/jc7TqF4kAD+OztOnXiQAQI7O06deJABBjs7TpV4kAEKOztOlXiQAQ47O06VdJABDjs7TpF0kAESPztKkXSQARY/O0qRdJABGj87So1wkAEaPztKjWyQAR5DO0qJbJABIkM7SolskAEiQztKhWyQASZDO0qFbJABKkM7SoFskAEqQzdKgWiQAS5DN0p9aJABLkM3Sn1okAEyQzdKeWSQATZDN0p5ZJABNkM3SnVkkAE6RzdKdWSQATpHN0pxYJABPkc3SnFgkAE+RzdKcWCQAUJHN0ptXJABRkc3Sm1ckAFGRzdKaVyQAUpHN0ppWJABSkc3SmVYkAFORzdKZViQAU5LN0ZhVJABUks3RmFUkAFSSzNGXVCQAVZLM0ZdUJABVkszRllQkAFaSzNGWUyQAVpLM0JZTJABXkszQlVMkAFeSzNCVUiQAWJLM0JRSJABYkszQlFIkAFmSzNCUUSQAWZLM0JNRJAA=');
                audio.volume = 0.3;
                audio.play();
            } catch (e) {
                console.log('[Dumont] Audio notification not available');
            }
        } else if (oldState.mode === 'cpu' && newState.mode === 'gpu') {
            showNotification(
                `Nova GPU provisionada! Voltando para ${newState.gpuName}.`,
                'success'
            );
        }
    }

    // Poll status API
    async function pollStatus() {
        try {
            const response = await fetch(API_ENDPOINT);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            const newState = {
                mode: data.mode || 'gpu',
                gpuName: data.gpu_name || 'GPU',
                cpuName: data.cpu_name || 'CPU Standby',
                lastSync: data.last_sync,
                syncCount: data.sync_count || 0,
                healthy: data.healthy !== false
            };

            // Check for state change
            if (currentState.mode !== newState.mode) {
                handleFailover(currentState, newState);
            }

            currentState = newState;
            updateWidget(currentState);

        } catch (error) {
            console.warn('[Dumont] Status poll failed:', error.message);
            // Mark as potentially unhealthy after multiple failures
            currentState.healthy = false;
            updateWidget(currentState);
        }
    }

    // Initialize widget
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        console.log('[Dumont] Initializing failover status widget');

        // Create widget
        createWidget();
        updateWidget(currentState);

        // Start polling
        pollStatus();
        setInterval(pollStatus, POLL_INTERVAL);

        // Listen for visibility changes to pause/resume polling
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                pollStatus();
            }
        });

        console.log('[Dumont] Failover status widget initialized');
    }

    // Start
    init();

})();
