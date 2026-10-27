/**
 * SecureVision AI — Frontend Application
 * Handles navigation, API calls, charts, uploads, alerts, and data rendering.
 * All displayed data comes from backend API responses.
 */

(function() {
    'use strict';

    const API_BASE = '';  // Same origin
    let distributionChart = null;
    let severityChart = null;

    // Current page state
    let currentPage = 'dashboard';
    let alertsPage = 1;
    let scansPage = 1;

    // ==========================================
    // INITIALIZATION
    // ==========================================
    document.addEventListener('DOMContentLoaded', () => {
        initNavigation();
        initMobileMenu();
        initUpload();
        initFilters();
        initModal();
        loadDashboard();
    });

    // ==========================================
    // NAVIGATION
    // ==========================================
    function initNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const page = item.dataset.page;
                navigateTo(page);
            });
        });
    }

    window.navigateTo = function(page) {
        currentPage = page;

        // Update nav
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        const activeNav = document.querySelector(`.nav-item[data-page="${page}"]`);
        if (activeNav) activeNav.classList.add('active');

        // Update pages
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const activePage = document.getElementById(`page-${page}`);
        if (activePage) activePage.classList.add('active');

        // Close mobile sidebar
        document.getElementById('sidebar').classList.remove('open');

        // Load page data
        switch (page) {
            case 'dashboard': loadDashboard(); break;
            case 'alerts': loadAlerts(); break;
            case 'scans': loadScans(); break;
            case 'model': loadModelDetail(); break;
            case 'research': loadResearch(); break;
        }
    };

    function initMobileMenu() {
        const btn = document.getElementById('mobile-menu-btn');
        const sidebar = document.getElementById('sidebar');
        btn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // ==========================================
    // API HELPER
    // ==========================================
    async function apiFetch(url, options = {}) {
        try {
            const response = await fetch(API_BASE + url, options);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `HTTP ${response.status}`);
            }
            return await response.json();
        } catch (err) {
            if (err.name === 'TypeError' && err.message.includes('fetch')) {
                throw new Error('Backend is not reachable. Please start the server.');
            }
            throw err;
        }
    }

    // ==========================================
    // DASHBOARD
    // ==========================================
    async function loadDashboard() {
        try {
            const data = await apiFetch('/api/v1/summary');

            // Stats
            document.getElementById('total-events').textContent = formatNumber(data.total_events_analyzed);
            document.getElementById('total-events').classList.remove('skeleton');
            document.getElementById('total-anomalies').textContent = formatNumber(data.total_anomalies);
            document.getElementById('total-anomalies').classList.remove('skeleton');
            document.getElementById('total-scans').textContent = formatNumber(data.total_scans);
            document.getElementById('total-scans').classList.remove('skeleton');
            document.getElementById('anomaly-rate').textContent = data.anomaly_rate.toFixed(1) + '%';
            document.getElementById('anomaly-rate').classList.remove('skeleton');

            // Distribution chart
            renderDistributionChart(data.total_normal, data.total_anomalies);

            // Severity chart
            renderSeverityChart(data.severity_distribution);

            // Recent scans
            renderRecentScans(data.recent_scans);

            // Model status
            updateModelBadge(data.model_status);

            // Load model status details
            loadModelStatus();

        } catch (err) {
            console.error('Dashboard load error:', err);
            document.getElementById('total-events').textContent = '—';
            document.getElementById('total-events').classList.remove('skeleton');
            document.getElementById('total-anomalies').textContent = '—';
            document.getElementById('total-anomalies').classList.remove('skeleton');
            document.getElementById('total-scans').textContent = '—';
            document.getElementById('total-scans').classList.remove('skeleton');
            document.getElementById('anomaly-rate').textContent = '—';
            document.getElementById('anomaly-rate').classList.remove('skeleton');
        }
    }

    function renderDistributionChart(normal, anomalous) {
        const canvas = document.getElementById('distributionChart');
        const emptyEl = document.getElementById('dist-empty');

        if (normal === 0 && anomalous === 0) {
            canvas.style.display = 'none';
            emptyEl.classList.remove('hidden');
            return;
        }
        canvas.style.display = 'block';
        emptyEl.classList.add('hidden');

        if (distributionChart) distributionChart.destroy();
        distributionChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Normal', 'Anomalous'],
                datasets: [{
                    data: [normal, anomalous],
                    backgroundColor: ['rgba(34, 197, 94, 0.7)', 'rgba(239, 68, 68, 0.7)'],
                    borderColor: ['rgba(34, 197, 94, 1)', 'rgba(239, 68, 68, 1)'],
                    borderWidth: 2,
                    hoverOffset: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { family: "'Inter', sans-serif" } }
                    }
                },
                cutout: '65%',
            }
        });
    }

    function renderSeverityChart(distribution) {
        const canvas = document.getElementById('severityChart');
        const emptyEl = document.getElementById('sev-empty');

        const labels = Object.keys(distribution);
        const values = Object.values(distribution);

        if (labels.length === 0) {
            canvas.style.display = 'none';
            emptyEl.classList.remove('hidden');
            return;
        }
        canvas.style.display = 'block';
        emptyEl.classList.add('hidden');

        const colorMap = {
            critical: 'rgba(239, 68, 68, 0.8)',
            high: 'rgba(249, 115, 22, 0.8)',
            medium: 'rgba(234, 179, 8, 0.8)',
            low: 'rgba(59, 130, 246, 0.8)',
            normal: 'rgba(34, 197, 94, 0.5)',
        };

        if (severityChart) severityChart.destroy();
        severityChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
                datasets: [{
                    label: 'Alerts',
                    data: values,
                    backgroundColor: labels.map(l => colorMap[l] || 'rgba(99, 102, 241, 0.6)'),
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(99, 102, 241, 0.08)' },
                        ticks: { color: '#94a3b8', stepSize: 1 }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    function renderRecentScans(scans) {
        const body = document.getElementById('recent-scans-body');
        const empty = document.getElementById('scans-empty');

        if (!scans || scans.length === 0) {
            body.innerHTML = '';
            empty.classList.remove('hidden');
            return;
        }
        empty.classList.add('hidden');

        body.innerHTML = scans.map(s => `
            <tr>
                <td><span class="badge badge-${s.status}">#${s.id}</span></td>
                <td>${escapeHtml(s.filename)}</td>
                <td><span class="badge badge-${s.status}">${s.status}</span></td>
                <td>${formatNumber(s.total_events)}</td>
                <td>${formatNumber(s.anomaly_count)}</td>
                <td>${formatDate(s.created_at)}</td>
            </tr>
        `).join('');
    }

    async function loadModelStatus() {
        try {
            const data = await apiFetch('/api/v1/model/status');
            updateModelBadge(data.status);
            document.getElementById('model-type').textContent = data.model_type || '—';
            document.getElementById('model-version-val').textContent = data.version || '—';
            document.getElementById('model-features').textContent =
                data.features ? `${data.features.length} features` : '—';
            document.getElementById('model-samples').textContent =
                data.training_samples ? formatNumber(data.training_samples) : '—';
        } catch (err) {
            updateModelBadge('error');
        }
    }

    function updateModelBadge(status) {
        const badge = document.getElementById('model-badge');
        badge.textContent = status === 'trained' ? 'Trained' : status === 'not_trained' ? 'Not Trained' : status;
        badge.className = 'badge badge-' + status;
    }

    // ==========================================
    // UPLOAD
    // ==========================================
    function initUpload() {
        const zone = document.getElementById('upload-zone');
        const input = document.getElementById('file-input');

        zone.addEventListener('click', () => input.click());

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });

        input.addEventListener('change', () => {
            if (input.files.length > 0) {
                handleFileUpload(input.files[0]);
            }
        });

        document.getElementById('upload-another-btn').addEventListener('click', resetUpload);
        document.getElementById('retry-upload-btn').addEventListener('click', resetUpload);
    }

    async function handleFileUpload(file) {
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showUploadError('Invalid File', 'Only CSV files are supported.');
            return;
        }

        // Show progress
        document.getElementById('upload-zone').classList.add('hidden');
        document.getElementById('upload-result').classList.add('hidden');
        document.getElementById('upload-error').classList.add('hidden');
        const progress = document.getElementById('upload-progress');
        progress.classList.remove('hidden');

        document.getElementById('progress-filename').textContent = file.name;
        document.getElementById('progress-status').textContent = 'Uploading...';
        document.getElementById('progress-bar').style.width = '20%';
        document.getElementById('progress-detail').textContent = 'Sending file to server...';

        try {
            const formData = new FormData();
            formData.append('file', file);

            document.getElementById('progress-bar').style.width = '40%';
            document.getElementById('progress-detail').textContent = 'Analyzing dataset...';

            const response = await fetch(API_BASE + '/api/v1/scans', {
                method: 'POST',
                body: formData,
            });

            document.getElementById('progress-bar').style.width = '80%';

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Server returned ${response.status}`);
            }

            const result = await response.json();
            document.getElementById('progress-bar').style.width = '100%';
            document.getElementById('progress-status').textContent = 'Complete!';

            setTimeout(() => {
                showUploadResult(result);
            }, 500);

        } catch (err) {
            showUploadError('Analysis Failed', err.message);
        }
    }

    function showUploadResult(result) {
        document.getElementById('upload-progress').classList.add('hidden');
        const resultDiv = document.getElementById('upload-result');
        resultDiv.classList.remove('hidden');

        document.getElementById('result-title').textContent = 'Analysis Complete';

        const statsHtml = `
            <div class="result-stat">
                <div class="result-stat-value">${formatNumber(result.total_events)}</div>
                <div class="result-stat-label">Events Analyzed</div>
            </div>
            <div class="result-stat">
                <div class="result-stat-value text-error">${formatNumber(result.anomaly_count)}</div>
                <div class="result-stat-label">Anomalies Found</div>
            </div>
            <div class="result-stat">
                <div class="result-stat-value text-success">${formatNumber(result.normal_count)}</div>
                <div class="result-stat-label">Normal Events</div>
            </div>
            <div class="result-stat">
                <div class="result-stat-value">${result.features_used ? result.features_used.length : 0}</div>
                <div class="result-stat-label">Features Used</div>
            </div>
        `;
        document.getElementById('result-stats').innerHTML = statsHtml;
    }

    function showUploadError(title, detail) {
        document.getElementById('upload-progress').classList.add('hidden');
        document.getElementById('upload-zone').classList.add('hidden');
        const errorDiv = document.getElementById('upload-error');
        errorDiv.classList.remove('hidden');
        document.getElementById('error-title').textContent = title;
        document.getElementById('error-detail').textContent = detail;
    }

    function resetUpload() {
        document.getElementById('upload-zone').classList.remove('hidden');
        document.getElementById('upload-progress').classList.add('hidden');
        document.getElementById('upload-result').classList.add('hidden');
        document.getElementById('upload-error').classList.add('hidden');
        document.getElementById('file-input').value = '';
    }

    // ==========================================
    // ALERTS
    // ==========================================
    function initFilters() {
        document.getElementById('apply-filters-btn').addEventListener('click', () => {
            alertsPage = 1;
            loadAlerts();
        });
        document.getElementById('clear-filters-btn').addEventListener('click', () => {
            document.getElementById('filter-prediction').value = '';
            document.getElementById('filter-severity').value = '';
            document.getElementById('filter-scan').value = '';
            document.getElementById('filter-search-input').value = '';
            alertsPage = 1;
            loadAlerts();
        });
        document.getElementById('export-btn').addEventListener('click', exportAlerts);
    }

    async function loadAlerts() {
        try {
            const params = new URLSearchParams();
            params.append('page', alertsPage);
            params.append('page_size', 20);

            const prediction = document.getElementById('filter-prediction').value;
            const severity = document.getElementById('filter-severity').value;
            const scanId = document.getElementById('filter-scan').value;
            const search = document.getElementById('filter-search-input').value;

            if (prediction !== '') params.append('prediction', prediction);
            if (severity) params.append('severity', severity);
            if (scanId) params.append('scan_id', scanId);
            if (search) params.append('search', search);

            const data = await apiFetch(`/api/v1/alerts?${params.toString()}`);
            renderAlerts(data);
        } catch (err) {
            console.error('Alerts load error:', err);
            document.getElementById('alerts-body').innerHTML = '';
            document.getElementById('alerts-empty').classList.remove('hidden');
        }
    }

    function renderAlerts(data) {
        const body = document.getElementById('alerts-body');
        const empty = document.getElementById('alerts-empty');
        const pagination = document.getElementById('alerts-pagination');

        if (!data.items || data.items.length === 0) {
            body.innerHTML = '';
            empty.classList.remove('hidden');
            pagination.innerHTML = '';
            return;
        }
        empty.classList.add('hidden');

        body.innerHTML = data.items.map(a => `
            <tr>
                <td>#${a.id}</td>
                <td>${a.scan_id}</td>
                <td>${a.event_index}</td>
                <td><span class="badge badge-${a.prediction === 1 ? 'anomalous' : 'normal'}">
                    ${a.prediction === 1 ? 'Anomalous' : 'Normal'}
                </span></td>
                <td><span class="badge badge-${a.severity || 'normal'}">${a.severity || 'normal'}</span></td>
                <td><code>${a.anomaly_score.toFixed(4)}</code></td>
                <td>${escapeHtml(a.source_ip || '—')}</td>
                <td>${escapeHtml(a.protocol || '—')}</td>
                <td>${escapeHtml(a.original_label || '—')}</td>
                <td><button class="btn btn-secondary btn-xs" onclick="viewAlertDetail(${a.id})">Details</button></td>
            </tr>
        `).join('');

        renderPagination(pagination, data, (page) => {
            alertsPage = page;
            loadAlerts();
        });
    }

    function exportAlerts() {
        const params = new URLSearchParams();
        const prediction = document.getElementById('filter-prediction').value;
        const severity = document.getElementById('filter-severity').value;
        const scanId = document.getElementById('filter-scan').value;

        if (prediction !== '') params.append('prediction', prediction);
        if (severity) params.append('severity', severity);
        if (scanId) params.append('scan_id', scanId);

        window.open(API_BASE + `/api/v1/alerts/export?${params.toString()}`, '_blank');
    }

    // ==========================================
    // ALERT DETAIL MODAL
    // ==========================================
    function initModal() {
        document.getElementById('modal-close-btn').addEventListener('click', closeModal);
        document.getElementById('alert-modal').addEventListener('click', (e) => {
            if (e.target.id === 'alert-modal') closeModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    }

    window.viewAlertDetail = async function(alertId) {
        try {
            const data = await apiFetch(`/api/v1/alerts/${alertId}`);
            renderAlertModal(data);
            document.getElementById('alert-modal').classList.remove('hidden');
        } catch (err) {
            console.error('Alert detail error:', err);
        }
    };

    function renderAlertModal(alert) {
        document.getElementById('modal-title').textContent = `Alert #${alert.id}`;
        const body = document.getElementById('modal-body');

        const featureValues = alert.feature_values_parsed || {};
        const explanation = alert.explanation_parsed || {};
        const steps = alert.investigation_steps_parsed || [];

        let html = '';

        // Overview
        html += `<div class="detail-section">
            <h3>Overview</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Prediction</div>
                    <div class="detail-value">
                        <span class="badge badge-${alert.prediction === 1 ? 'anomalous' : 'normal'}">
                        ${alert.prediction === 1 ? 'Anomalous' : 'Normal'}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Severity</div>
                    <div class="detail-value">
                        <span class="badge badge-${alert.severity || 'normal'}">${alert.severity || 'normal'}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Anomaly Score</div>
                    <div class="detail-value"><code>${alert.anomaly_score.toFixed(6)}</code></div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Event Index</div>
                    <div class="detail-value">${alert.event_index}</div>
                </div>
                ${alert.source_ip ? `<div class="detail-item"><div class="detail-label">Source IP</div><div class="detail-value">${escapeHtml(alert.source_ip)}</div></div>` : ''}
                ${alert.dest_ip ? `<div class="detail-item"><div class="detail-label">Dest IP</div><div class="detail-value">${escapeHtml(alert.dest_ip)}</div></div>` : ''}
                ${alert.protocol ? `<div class="detail-item"><div class="detail-label">Protocol</div><div class="detail-value">${escapeHtml(alert.protocol)}</div></div>` : ''}
                ${alert.original_label ? `<div class="detail-item"><div class="detail-label">Original Label</div><div class="detail-value">${escapeHtml(alert.original_label)}</div></div>` : ''}
            </div>
        </div>`;

        // Explanation
        if (explanation.summary) {
            html += `<div class="detail-section">
                <h3>Explanation</h3>
                <p style="margin-bottom:12px; color: var(--text-secondary); font-size:0.9rem;">${escapeHtml(explanation.summary)}</p>`;

            if (explanation.reasons && explanation.reasons.length > 0) {
                html += `<ul class="reason-list">`;
                explanation.reasons.forEach(r => {
                    html += `<li>${escapeHtml(r)}</li>`;
                });
                html += `</ul>`;
            }

            if (explanation.anomaly_score_interpretation) {
                html += `<p style="margin-top:12px; font-size:0.82rem; color:var(--text-muted);">
                    ${escapeHtml(explanation.anomaly_score_interpretation)}</p>`;
            }
            if (explanation.confidence_note) {
                html += `<p style="margin-top:8px; font-size:0.78rem; color:var(--text-muted); font-style:italic;">
                    ${escapeHtml(explanation.confidence_note)}</p>`;
            }
            html += `</div>`;
        }

        // Investigation Steps
        if (steps.length > 0) {
            html += `<div class="detail-section">
                <h3>Recommended Investigation</h3>
                <ol class="step-list">`;
            steps.forEach(s => {
                html += `<li>${escapeHtml(s)}</li>`;
            });
            html += `</ol></div>`;
        }

        // Feature Values
        const featureKeys = Object.keys(featureValues);
        if (featureKeys.length > 0) {
            html += `<div class="detail-section">
                <h3>Feature Values</h3>
                <div class="detail-grid">`;
            featureKeys.forEach(k => {
                html += `<div class="detail-item">
                    <div class="detail-label">${escapeHtml(k)}</div>
                    <div class="detail-value"><code>${typeof featureValues[k] === 'number' ? featureValues[k].toFixed(4) : featureValues[k]}</code></div>
                </div>`;
            });
            html += `</div></div>`;
        }

        body.innerHTML = html;
    }

    function closeModal() {
        document.getElementById('alert-modal').classList.add('hidden');
    }

    // ==========================================
    // SCANS
    // ==========================================
    async function loadScans() {
        try {
            const data = await apiFetch(`/api/v1/scans?page=${scansPage}&page_size=10`);
            renderScans(data);
        } catch (err) {
            console.error('Scans load error:', err);
            document.getElementById('scans-body').innerHTML = '';
            document.getElementById('scans-page-empty').classList.remove('hidden');
        }
    }

    function renderScans(data) {
        const body = document.getElementById('scans-body');
        const empty = document.getElementById('scans-page-empty');
        const pagination = document.getElementById('scans-pagination');

        if (!data.items || data.items.length === 0) {
            body.innerHTML = '';
            empty.classList.remove('hidden');
            pagination.innerHTML = '';
            return;
        }
        empty.classList.add('hidden');

        body.innerHTML = data.items.map(s => `
            <tr>
                <td>#${s.id}</td>
                <td>${escapeHtml(s.filename)}</td>
                <td><span class="badge badge-${s.status}">${s.status}</span></td>
                <td>${formatNumber(s.total_events)}</td>
                <td>${formatNumber(s.anomaly_count)}</td>
                <td>${formatNumber(s.normal_count)}</td>
                <td><code>${escapeHtml(s.model_version || '—')}</code></td>
                <td>${formatDate(s.created_at)}</td>
                <td><button class="btn btn-secondary btn-xs" onclick="viewScanAlerts(${s.id})">View Alerts</button></td>
            </tr>
        `).join('');

        renderPagination(pagination, data, (page) => {
            scansPage = page;
            loadScans();
        });
    }

    window.viewScanAlerts = function(scanId) {
        document.getElementById('filter-scan').value = scanId;
        navigateTo('alerts');
        loadAlerts();
    };

    // ==========================================
    // MODEL DETAIL
    // ==========================================
    async function loadModelDetail() {
        const container = document.getElementById('model-detail-content');
        try {
            const data = await apiFetch('/api/v1/model/status');

            let html = `
                <div class="detail-section">
                    <h3>Model Information</h3>
                    <div class="info-grid">
                        <div class="info-row">
                            <span class="info-label">Status</span>
                            <span class="info-value"><span class="badge badge-${data.status}">${data.status}</span></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Model Type</span>
                            <span class="info-value">${data.model_type || '—'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Version</span>
                            <span class="info-value"><code>${data.version || '—'}</code></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Training Samples</span>
                            <span class="info-value">${data.training_samples ? formatNumber(data.training_samples) : '—'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Contamination</span>
                            <span class="info-value">${data.contamination ?? '—'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Estimators</span>
                            <span class="info-value">${data.n_estimators ?? '—'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Training Dataset</span>
                            <span class="info-value">${data.training_dataset ? escapeHtml(data.training_dataset) : '—'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Last Trained</span>
                            <span class="info-value">${data.last_trained ? formatDate(data.last_trained) : '—'}</span>
                        </div>
                    </div>
                </div>`;

            if (data.features && data.features.length > 0) {
                html += `<div class="detail-section">
                    <h3>Features (${data.features.length})</h3>
                    <div class="feature-list">
                        ${data.features.map(f => `<span class="feature-tag">${escapeHtml(f)}</span>`).join('')}
                    </div>
                </div>`;
            }

            if (data.status === 'not_trained') {
                html += `<div class="detail-section" style="text-align:center; padding:24px;">
                    <p style="color:var(--text-secondary); margin-bottom:12px;">
                        No trained model found. Upload a CSV dataset to automatically train the model, 
                        or run <code>python scripts/train_model.py</code> from the command line.
                    </p>
                    <button class="btn btn-primary" onclick="navigateTo('upload')">Upload Dataset</button>
                </div>`;
            }

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="empty-state"><p>Failed to load model status: ${escapeHtml(err.message)}</p></div>`;
        }
    }

    // ==========================================
    // RESEARCH
    // ==========================================
    async function loadResearch() {
        const container = document.getElementById('research-content');
        try {
            const data = await apiFetch('/api/v1/research/metrics');

            if (!data.experiments || data.experiments.length === 0) {
                container.innerHTML = `<div class="empty-state">
                    <p>No evaluation experiments recorded yet.</p>
                    <p style="margin-top:8px; font-size:0.85rem; color:var(--text-muted);">
                        Run <code>python scripts/evaluate_model.py</code> to evaluate model performance.
                    </p>
                </div>`;
                return;
            }

            let html = '';
            data.experiments.forEach(exp => {
                html += `<div class="detail-section" style="border-bottom: 1px solid var(--border-color); padding-bottom: 24px; margin-bottom: 24px;">
                    <h3>${escapeHtml(exp.experiment_name)}</h3>
                    <p style="color:var(--text-secondary); font-size:0.85rem; margin-bottom:16px;">
                        Model: ${escapeHtml(exp.model_type)} | Dataset: ${escapeHtml(exp.dataset_name || '—')}
                        | Samples: ${exp.total_samples} | Date: ${exp.created_at ? formatDate(exp.created_at) : '—'}
                    </p>

                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value text-success">${exp.precision != null ? (exp.precision * 100).toFixed(1) + '%' : '—'}</div>
                            <div class="metric-label">Precision</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" style="color:var(--accent-secondary)">${exp.recall != null ? (exp.recall * 100).toFixed(1) + '%' : '—'}</div>
                            <div class="metric-label">Recall</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" style="color:var(--accent-primary)">${exp.f1 != null ? (exp.f1 * 100).toFixed(1) + '%' : '—'}</div>
                            <div class="metric-label">F1 Score</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value text-warning">${exp.false_positive_rate != null ? (exp.false_positive_rate * 100).toFixed(1) + '%' : '—'}</div>
                            <div class="metric-label">False Positive Rate</div>
                        </div>
                    </div>`;

                // Confusion matrix
                if (exp.confusion_matrix) {
                    const cm = exp.confusion_matrix;
                    html += `<h4 style="font-size:0.85rem; color:var(--text-secondary); margin:16px 0 12px;">Confusion Matrix</h4>
                    <div class="confusion-matrix">
                        <div class="cm-header"></div>
                        <div class="cm-header">Pred Normal</div>
                        <div class="cm-header">Pred Anomalous</div>
                        <div class="cm-header">True Normal</div>
                        <div class="cm-cell cm-tn">${cm.true_negatives}</div>
                        <div class="cm-cell cm-fp">${cm.false_positives}</div>
                        <div class="cm-header">True Anomalous</div>
                        <div class="cm-cell cm-fn">${cm.false_negatives}</div>
                        <div class="cm-cell cm-tp">${cm.true_positives}</div>
                    </div>`;
                }

                if (exp.notes) {
                    html += `<p style="margin-top:16px; font-size:0.82rem; color:var(--text-muted); font-style:italic;">
                        Note: ${escapeHtml(exp.notes)}</p>`;
                }

                html += `</div>`;
            });

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<div class="empty-state"><p>Failed to load research data: ${escapeHtml(err.message)}</p></div>`;
        }
    }

    // ==========================================
    // PAGINATION HELPER
    // ==========================================
    function renderPagination(container, data, onPageChange) {
        if (data.total_pages <= 1) {
            container.innerHTML = `<span class="pagination-info">${data.total} total records</span>`;
            return;
        }

        let html = '';
        html += `<button ${data.page <= 1 ? 'disabled' : ''} onclick="return false;">Prev</button>`;

        const startPage = Math.max(1, data.page - 2);
        const endPage = Math.min(data.total_pages, data.page + 2);

        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="${i === data.page ? 'active' : ''}">${i}</button>`;
        }

        html += `<button ${data.page >= data.total_pages ? 'disabled' : ''}>Next</button>`;
        html += `<span class="pagination-info">${data.total} total</span>`;

        container.innerHTML = html;

        // Add event listeners
        container.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.disabled) return;
                if (btn.textContent === 'Prev') onPageChange(data.page - 1);
                else if (btn.textContent === 'Next') onPageChange(data.page + 1);
                else onPageChange(parseInt(btn.textContent));
            });
        });
    }

    // ==========================================
    // UTILITY FUNCTIONS
    // ==========================================
    function formatNumber(n) {
        if (n == null) return '0';
        return n.toLocaleString();
    }

    function formatDate(dateStr) {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function escapeHtml(str) {
        if (str == null) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

})();
