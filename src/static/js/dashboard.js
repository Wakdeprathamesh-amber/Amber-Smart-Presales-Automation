// Dashboard functionality for Smart Presales

// Global state
const state = {
  leads: [],
  filteredLeads: [],
  selectedLeads: new Set(),  // Track selected lead UUIDs for bulk operations
  stats: {
    totalLeads: 0,
    completed: 0,
    qualified: 0,
    potential: 0,
    notQualified: 0,
    pendingCalls: 0,
    retries: 0,
    missed: 0,
    successfulConversations: 0,
    voicemail: 0
  },
  filters: {
    status: 'all',
    searchQuery: '',
    special: null // one of: 'voicemail','nonconnected','successful','potential','notqualified' | null
  },
  retryConfig: {
    max_retries: 3,
    retry_intervals: [1, 4, 24]
  },
  currentLeadUuid: null,
  batchJobId: null  // Track active batch calling job
};

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
  // Initial data load
  fetchLeads();
  
  // Fetch retry configuration
  fetchRetryConfig();
  
  // Check for active batch job and resume progress tracking
  checkAndResumeActiveBatchJob();
  
  // Set up event listeners
  setupEventListeners();
});

// Check for active batch job on page load
async function checkAndResumeActiveBatchJob() {
  try {
    const resp = await fetch('/api/batch-call/status');
    if (resp.status === 404) {
      // No active job, that's fine
      return;
    }
    if (!resp.ok) return;
    
    const job = await resp.json();
    
    // If job is still running, resume progress tracking
    if (job.status === 'running') {
      state.batchJobId = job.job_id;
      showBatchProgress();
      startBatchProgressPolling();
      showMessage('info', 'Resumed tracking active batch job');
    }
  } catch (e) {
    // Silently ignore if no active job
    console.log('No active batch job to resume');
  }
}

function setupEventListeners() {
  // Status filter change
  const statusFilter = document.getElementById('status-filter');
  if (statusFilter) {
    statusFilter.addEventListener('change', () => {
      state.filters.status = statusFilter.value;
      applyFilters();
    });
  }
  
  // Search input
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      state.filters.searchQuery = searchInput.value.toLowerCase();
      applyFilters();
    });
  }
  
  // Refresh button
  const refreshBtn = document.getElementById('refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', fetchLeads);
  }

  // Stats card quick filters
  const cardPotential = document.getElementById('card-potential');
  if (cardPotential) {
    cardPotential.addEventListener('click', () => applyQuickFilter('potential'));
  }
  const cardNotQualified = document.getElementById('card-notqualified');
  if (cardNotQualified) {
    cardNotQualified.addEventListener('click', () => applyQuickFilter('notqualified'));
  }
  const cardSuccessful = document.getElementById('card-successful');
  if (cardSuccessful) {
    cardSuccessful.addEventListener('click', () => applyQuickFilter('successful'));
  }
  const cardVoicemail = document.getElementById('card-voicemail');
  if (cardVoicemail) {
    cardVoicemail.addEventListener('click', () => applyQuickFilter('voicemail'));
  }

  // Upload CSV button
  const uploadCsvBtn = document.getElementById('upload-csv-btn');
  if (uploadCsvBtn) {
    uploadCsvBtn.addEventListener('click', () => openModal('upload-csv-modal'));
  }

  // Bulk call button
  const bulkCallBtn = document.getElementById('bulk-call-btn');
  if (bulkCallBtn) {
    bulkCallBtn.addEventListener('click', bulkCallEligible);
  }
  
  // Schedule bulk calls button
  const scheduleBulkBtn = document.getElementById('schedule-bulk-btn');
  if (scheduleBulkBtn) {
    scheduleBulkBtn.addEventListener('click', openBulkScheduleModal);
  }
  
  // Select all checkbox
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', handleSelectAllChange);
  }
  
  // Bulk schedule form
  const bulkScheduleForm = document.getElementById('bulk-schedule-form');
  if (bulkScheduleForm) {
    bulkScheduleForm.addEventListener('submit', scheduleBulkCalls);
    
    // Update summary when inputs change
    const scheduleInputs = ['schedule-date', 'schedule-time', 'parallel-calls', 'call-interval'];
    scheduleInputs.forEach(id => {
      const input = document.getElementById(id);
      if (input) {
        input.addEventListener('change', updateScheduleSummary);
      }
    });
  }
  
  // Add lead button
  const addLeadBtn = document.getElementById('add-lead-btn');
  if (addLeadBtn) {
    addLeadBtn.addEventListener('click', () => {
      openModal('add-lead-modal');
    });
  }
  
  // Retry config button
  const retryConfigBtn = document.getElementById('retry-config-btn');
  if (retryConfigBtn) {
    retryConfigBtn.addEventListener('click', () => {
      openModal('retry-config-modal');
    });
  }

  // WhatsApp settings button
  const waSettingsBtn = document.getElementById('wa-settings-btn');
  if (waSettingsBtn) {
    waSettingsBtn.addEventListener('click', async () => {
      await loadWhatsAppSettings();
      openModal('wa-settings-modal');
    });
  }

  // Email settings button
  const emailSettingsBtn = document.getElementById('email-settings-btn');
  if (emailSettingsBtn) {
    emailSettingsBtn.addEventListener('click', async () => {
      await loadEmailSettings();
      openModal('email-settings-modal');
    });
  }
  
  // Event delegation for dynamic buttons and checkboxes
  document.addEventListener('click', (e) => {
    // Lead checkbox
    if (e.target.matches('.lead-checkbox')) {
      handleCheckboxChange(e);
    }
    
    // Call button
    if (e.target.matches('.call-btn')) {
      const leadUuid = e.target.dataset.uuid;
      initiateCall(leadUuid);
    }
    
    // View details button
    if (e.target.matches('.view-btn')) {
      const leadUuid = e.target.dataset.uuid;
      viewLeadDetails(leadUuid);
    }

    // Delete button
    if (e.target.matches('.delete-btn')) {
      const leadUuid = e.target.dataset.uuid;
      deleteLead(leadUuid);
    }
    // Send email button
    if (e.target.matches('.email-btn')) {
      const leadUuid = e.target.dataset.uuid;
      sendEmail(leadUuid);
    }
    // Send WhatsApp button
    if (e.target.matches('.wa-btn')) {
      const leadUuid = e.target.dataset.uuid;
      sendWhatsApp(leadUuid);
    }
  });
  
  // Modal close buttons
  document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
    btn.addEventListener('click', () => {
      closeAllModals();
    });
  });
  
  // Add lead form submission
  const addLeadForm = document.getElementById('add-lead-form');
  if (addLeadForm) {
    addLeadForm.addEventListener('submit', (e) => {
      e.preventDefault();
      submitNewLead();
    });
  }
  
  // Retry config form submission
  const retryConfigForm = document.getElementById('retry-config-form');
  if (retryConfigForm) {
    retryConfigForm.addEventListener('submit', (e) => {
      e.preventDefault();
      submitRetryConfig();
    });
  }

  // Upload CSV form submission
  const uploadCsvForm = document.getElementById('upload-csv-form');
  if (uploadCsvForm) {
    uploadCsvForm.addEventListener('submit', (e) => {
      e.preventDefault();
      submitCsvUpload();
    });
  }
  
  // Add interval button
  const addIntervalBtn = document.getElementById('add-interval-btn');
  if (addIntervalBtn) {
    addIntervalBtn.addEventListener('click', addRetryInterval);
  }

  // WhatsApp settings form submission
  const waSettingsForm = document.getElementById('wa-settings-form');
  if (waSettingsForm) {
    waSettingsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitWhatsAppSettings();
    });
  }

  const emailSettingsForm = document.getElementById('email-settings-form');
  if (emailSettingsForm) {
    emailSettingsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitEmailSettings();
    });
  }
}

async function deleteLead(leadUuid) {
  if (!confirm('Delete this lead? This cannot be undone.')) return;
  showLoader(true);
  try {
    const resp = await fetch(`/api/leads/${leadUuid}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to delete lead');
    }
    showMessage('success', 'Lead deleted');
    
    // Remove from selection if selected
    state.selectedLeads.delete(leadUuid);
    updateSelectedCount();
    
    // Refresh list
    await fetchLeads();
  } catch (e) {
    console.error('Delete lead error:', e);
    showMessage('error', e.message || 'Failed to delete lead');
  } finally {
    showLoader(false);
  }
}

// API Functions
let activeRefreshTimer = null;
let detailsRefreshTimer = null;
let detailsRefreshDebounce = null;

async function fetchLeads() {
  showLoader(true);
  
  try {
    const response = await fetch('/api/leads');
    if (!response.ok) throw new Error('Failed to fetch leads');
    
    const data = await response.json();
    state.leads = data;
    state.filteredLeads = [...data];
    
    calculateStats();
    renderLeadsTable();
    renderStats();

    // Auto-refresh while any lead is in active state
    const hasActive = state.leads.some(l => ['initiated', 'answered'].includes(l.call_status));
    if (hasActive) {
      if (activeRefreshTimer) clearTimeout(activeRefreshTimer);
      activeRefreshTimer = setTimeout(fetchLeads, 10000);
    } else if (activeRefreshTimer) {
      clearTimeout(activeRefreshTimer);
      activeRefreshTimer = null;
    }
    
    showLoader(false);
  } catch (error) {
    console.error('Error fetching leads:', error);
    showMessage('error', 'Failed to load leads');
    showLoader(false);
  }
}

async function initiateCall(leadUuid) {
  showLoader(true);
  
  // Provide immediate UI feedback on the clicked button
  const btn = document.querySelector(`.call-btn[data-uuid="${leadUuid}"]`);
  const prevDisabled = btn ? btn.disabled : false;
  const prevHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '📞 Calling…';
  }
  showMessage('info', 'Placing call…');

  try {
    const response = await fetch(`/api/leads/${leadUuid}/call`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const msg = errorData.details || errorData.error || 'Failed to initiate call';
      throw new Error(msg);
    }
    
    const data = await response.json();
    showMessage('success', `Call initiated for lead`);
    
    // Update lead status in UI
    const leadIndex = state.leads.findIndex(lead => lead.lead_uuid === leadUuid);
    if (leadIndex !== -1) {
      state.leads[leadIndex].call_status = 'initiated';
      state.leads[leadIndex].last_call_time = data.call_time;
      renderLeadsTable();
    }
    
    showLoader(false);
  } catch (error) {
    console.error('Error initiating call:', error);
    showMessage('error', error.message || 'Failed to initiate call');
    showLoader(false);
  } finally {
    // Restore button state if it still exists in DOM (it may be re-rendered)
    const btnNow = document.querySelector(`.call-btn[data-uuid="${leadUuid}"]`);
    if (btnNow) {
      btnNow.disabled = prevDisabled;
      if (prevHtml) btnNow.innerHTML = prevHtml;
    }
  }
}

async function viewLeadDetails(leadUuid) {
  showLoader(true);
  
  try {
    const response = await fetch(`/api/leads/${leadUuid}/details`);
    
    if (!response.ok) throw new Error('Failed to fetch lead details');
    
    const lead = await response.json();
    renderLeadDetails(lead);
    openModal('lead-details-modal');
    // Track active lead and start auto-refresh timer
    state.currentLeadUuid = leadUuid;
    startDetailsAutoRefresh();
    
    showLoader(false);
  } catch (error) {
    console.error('Error fetching lead details:', error);
    showMessage('error', 'Failed to fetch lead details');
    showLoader(false);
  }
}

function renderLeadDetails(lead) {
  const detailsContainer = document.getElementById('lead-details-content');
  if (!detailsContainer) return;
  
  let structuredDataHtml = '<p>No structured data available</p>';
  if (lead.structured_data && typeof lead.structured_data === 'object') {
    structuredDataHtml = '<div class="structured-data">';
    for (const [key, value] of Object.entries(lead.structured_data)) {
      structuredDataHtml += `
        <div class="data-item">
          <strong>${key}:</strong> ${value || 'N/A'}
        </div>
      `;
    }
    structuredDataHtml += '</div>';
  }
  
  let callHistoryHtml = '<p>No call history available</p>';
  if (lead.call_history && lead.call_history.length > 0) {
    callHistoryHtml = '<div class="call-history">';
    lead.call_history.forEach(entry => {
      callHistoryHtml += `
        <div class="history-item">
          <div class="history-time">${new Date(entry.time).toLocaleString()}</div>
          <div class="history-status"><span class="status-badge status-${entry.status}">${entry.status}</span></div>
          ${entry.ended_reason ? `<div class="history-summary"><em>Reason: ${entry.ended_reason}</em></div>` : ''}
          ${entry.summary ? `<div class="history-summary">${entry.summary}</div>` : ''}
          ${entry.success_status ? `<div class="history-success">Result: <span class="status-badge status-${entry.success_status.toLowerCase().replace(' ', '-')}">${entry.success_status}</span></div>` : ''}
        </div>
      `;
    });
    callHistoryHtml += '</div>';
  }

  // Email timeline
  let emailHtml = '<p>No emails yet</p>';
  // WhatsApp timeline
  let waHtml = '<p>No WhatsApp messages yet</p>';
  if (lead.conversations && lead.conversations.length > 0) {
    const emails = lead.conversations.filter(c => c.channel === 'email');
    const was = lead.conversations.filter(c => c.channel === 'whatsapp');
    if (emails.length > 0) {
      const sortedE = [...emails].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
      emailHtml = '<div class="call-history">';
      sortedE.forEach(item => {
        emailHtml += `
          <div class="history-item">
            <div class="history-time">${new Date(item.timestamp).toLocaleString()}</div>
            <div class="history-status">✉️ email · ${item.direction}</div>
            ${item.subject ? `<div class="history-summary"><strong>${item.subject}</strong></div>` : ''}
            ${item.content ? `<div class="history-summary">${item.content}</div>` : ''}
            ${item.status ? `<div class="history-summary"><em>Status: ${item.status}</em></div>` : ''}
          </div>
        `;
      });
      emailHtml += '</div>';
    }
    if (was.length > 0) {
      const sortedW = [...was].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
      waHtml = '<div class="call-history">';
      sortedW.forEach(item => {
        waHtml += `
          <div class="history-item">
            <div class="history-time">${new Date(item.timestamp).toLocaleString()}</div>
            <div class="history-status">💬 whatsapp · ${item.direction}</div>
            ${item.subject ? `<div class="history-summary"><strong>${item.subject}</strong></div>` : ''}
            ${item.content ? `<div class="history-summary">${item.content}</div>` : ''}
            ${item.status ? `<div class="history-summary"><em>Status: ${item.status}</em></div>` : ''}
          </div>
        `;
      });
      waHtml += '</div>';
    }
  }
  
  detailsContainer.innerHTML = `
    <div class="lead-details">
      <div class="detail-section">
        <h4 class="section-title">Contact Information</h4>
        <div class="detail-grid">
          <div class="detail-item">
            <strong>Name:</strong> ${lead.name || 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Phone:</strong> ${lead.number || 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Email:</strong> ${lead.email || 'N/A'}
          </div>
          <div class="detail-item">
            <strong>WhatsApp:</strong> ${lead.whatsapp_number || lead.number || 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Partner:</strong> ${lead.partner || 'N/A'}
          </div>
        </div>
      </div>
      
      <div class="detail-section">
        <h4 class="section-title">Call Status</h4>
        <div class="detail-grid">
          <div class="detail-item">
            <strong>Status:</strong> <span class="status-badge status-${lead.call_status || 'pending'}">${lead.call_status || 'pending'}</span>
          </div>
          <div class="detail-item">
            <strong>Retry Count:</strong> ${lead.retry_count || '0'}
          </div>
          <div class="detail-item">
            <strong>Vapi Call ID:</strong> ${lead.vapi_call_id ? `<code style="font-size: 11px;">${lead.vapi_call_id}</code>` : 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Last Call:</strong> ${lead.last_call_time ? new Date(lead.last_call_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) + ' IST' : 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Next Retry:</strong> ${lead.next_retry_time ? new Date(lead.next_retry_time).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) + ' IST' : 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Call Duration:</strong> ${lead.call_duration ? `${lead.call_duration} seconds (${Math.floor(lead.call_duration / 60)}:${(lead.call_duration % 60).toString().padStart(2, '0')} min)` : 'N/A'}
          </div>
          <div class="detail-item full-width">
            <strong>Recording:</strong> ${lead.recording_url ? `<a href="${lead.recording_url}" target="_blank" class="btn btn-sm btn-secondary">🎧 Listen to Recording</a>` : 'Not available'}
          </div>
        </div>
      </div>
      
      <div class="detail-section">
        <h4 class="section-title">Lead Information</h4>
        <div class="detail-grid">
          <div class="detail-item">
            <strong>Country:</strong> ${lead.country || 'Not captured'}
          </div>
          <div class="detail-item">
            <strong>University:</strong> ${lead.university || 'Not captured'}
          </div>
          <div class="detail-item">
            <strong>Course:</strong> ${lead.course || 'Not captured'}
          </div>
          <div class="detail-item">
            <strong>Intake:</strong> ${lead.intake || 'Not captured'}
          </div>
          <div class="detail-item">
            <strong>Visa Status:</strong> ${lead.visa_status || 'Not captured'}
          </div>
          <div class="detail-item">
            <strong>Budget:</strong> ${lead.budget || 'Not captured'}
          </div>
        </div>
      </div>
      
      <div class="detail-section">
        <h4 class="section-title">Call Analysis</h4>
        <div class="detail-item full-width">
          <strong>Summary:</strong>
          <div class="summary-text">${lead.summary || 'No summary available'}</div>
        </div>
        <div class="detail-item full-width">
          <strong>Success Status:</strong>
          ${lead.success_status ? `<span class="status-badge status-${lead.success_status.toLowerCase().replace(' ', '-')}">${lead.success_status}</span>` : 'N/A'}
        </div>
        <div class="detail-item full-width">
          <strong>Analysis Received:</strong> ${lead.analysis_received_at ? new Date(lead.analysis_received_at).toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'}) + ' IST' : 'N/A'}
        </div>
        <div class="detail-item full-width">
          <strong>Structured Data (Raw):</strong>
          ${structuredDataHtml}
        </div>
        <div class="detail-item full-width">
          <strong>Transcript:</strong>
          <div class="summary-text" style="white-space: pre-wrap; max-height: 300px; overflow-y: auto;">${lead.transcript || 'Transcript not available yet'}</div>
        </div>
      </div>
      
      <div class="detail-section">
        <h4 class="section-title">Call History</h4>
        ${callHistoryHtml}
      </div>
      <div class="detail-section">
        <h4 class="section-title">Email History</h4>
        ${emailHtml}
      </div>
      <div class="detail-section">
        <h4 class="section-title">WhatsApp History</h4>
        ${waHtml}
      </div>
    </div>
  `;
}

async function fetchRetryConfig() {
  try {
    const response = await fetch('/api/retry-config');
    if (!response.ok) throw new Error('Failed to fetch retry configuration');
    
    const config = await response.json();
    state.retryConfig = config;
    
    // Update the retry config form if it exists
    updateRetryConfigForm();
  } catch (error) {
    console.error('Error fetching retry configuration:', error);
  }
}

function updateRetryConfigForm() {
  const maxRetriesInput = document.getElementById('max-retries');
  const intervalsContainer = document.getElementById('retry-intervals-container');
  
  if (!maxRetriesInput || !intervalsContainer) return;
  
  // Set max retries value
  maxRetriesInput.value = state.retryConfig.max_retries;
  
  // Clear and rebuild intervals
  intervalsContainer.innerHTML = '';
  
  state.retryConfig.retry_intervals.forEach((interval, index) => {
    const intervalRow = document.createElement('div');
    intervalRow.className = 'retry-interval-row';
    intervalRow.innerHTML = `
      <div class="form-group">
        <label class="form-label">Retry #${index + 1} (<span id="retry-unit-label">hours</span>)</label>
        <div class="interval-input-group">
          <input type="number" class="form-control interval-input" value="${interval}" min="1" required>
          ${index > 0 ? `<button type="button" class="btn btn-danger btn-sm remove-interval" data-index="${index}">×</button>` : ''}
        </div>
      </div>
    `;
    intervalsContainer.appendChild(intervalRow);
  });

  // Units selector
  let unitsRow = document.getElementById('retry-units-row');
  if (!unitsRow) {
    unitsRow = document.createElement('div');
    unitsRow.id = 'retry-units-row';
    unitsRow.className = 'form-group';
    unitsRow.innerHTML = `
      <label class="form-label">Units</label>
      <select id="retry-units" class="form-control">
        <option value="hours" selected>Hours</option>
        <option value="minutes">Minutes</option>
      </select>
    `;
    intervalsContainer.parentElement.appendChild(unitsRow);
  }
  
  // Add event listeners for remove buttons
  document.querySelectorAll('.remove-interval').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const index = parseInt(e.target.dataset.index);
      removeRetryInterval(index);
    });
  });
}

async function loadWhatsAppSettings() {
  try {
    const resp = await fetch('/api/settings/whatsapp');
    if (!resp.ok) throw new Error('Failed to load WhatsApp settings');
    const data = await resp.json();
    document.getElementById('wa-enable-followup').value = String(!!data.enable_followup);
    document.getElementById('wa-enable-fallback').value = String(!!data.enable_fallback);
    document.getElementById('wa-template-followup').value = data.template_followup || '';
    document.getElementById('wa-template-fallback').value = data.template_fallback || '';
    document.getElementById('wa-language').value = data.language || 'en';
    updateWaPreview();
    // Update preview on input changes
    ['wa-template-followup','wa-template-fallback','wa-language'].forEach(id => {
      const el = document.getElementById(id);
      if (el && !el._wa_bound) {
        el.addEventListener('input', updateWaPreview);
        el._wa_bound = true;
      }
    });
  } catch (e) {
    console.error('WA settings load error:', e);
    showMessage('error', 'Failed to load WhatsApp settings');
  }
}

function updateWaPreview() {
  const follow = (document.getElementById('wa-template-followup').value || 'followup_after_call');
  const fallback = (document.getElementById('wa-template-fallback').value || 'fallback_after_retries');
  const lang = (document.getElementById('wa-language').value || 'en');
  document.getElementById('wa-preview').textContent = `Follow-up: ${follow} | Fallback: ${fallback} | Lang: ${lang} | Params: [<lead name>]`;
}

async function submitWhatsAppSettings() {
  showLoader(true);
  try {
    const payload = {
      enable_followup: document.getElementById('wa-enable-followup').value === 'true',
      enable_fallback: document.getElementById('wa-enable-fallback').value === 'true',
      template_followup: document.getElementById('wa-template-followup').value || '',
      template_fallback: document.getElementById('wa-template-fallback').value || '',
      language: document.getElementById('wa-language').value || 'en'
    };
    const resp = await fetch('/api/settings/whatsapp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!resp.ok) throw new Error('Failed to save WhatsApp settings');
    showMessage('success', 'WhatsApp settings saved');
    closeAllModals();
  } catch (e) {
    console.error('WA settings save error:', e);
    showMessage('error', 'Failed to save WhatsApp settings');
  } finally {
    showLoader(false);
  }
}

async function loadEmailSettings() {
  try {
    const resp = await fetch('/api/settings/email');
    if (!resp.ok) throw new Error('Failed to load Email settings');
    const data = await resp.json();
    document.getElementById('email-subject').value = data.subject || '';
    document.getElementById('email-body').value = data.body || '';
    // If empty (first time), prefill with server defaults by calling reset
    if (!data.subject || !data.body) {
      await fetch('/api/settings/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reset_defaults: true })
      });
      const resp2 = await fetch('/api/settings/email');
      if (resp2.ok) {
        const d2 = await resp2.json();
        document.getElementById('email-subject').value = d2.subject || '';
        document.getElementById('email-body').value = d2.body || '';
      }
    }
  } catch (e) {
    console.error('Email settings load error:', e);
    showMessage('error', 'Failed to load Email settings');
  }
}

async function submitEmailSettings() {
  showLoader(true);
  try {
    const payload = {
      subject: document.getElementById('email-subject').value || '',
      body: document.getElementById('email-body').value || ''
    };
    const resp = await fetch('/api/settings/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!resp.ok) throw new Error('Failed to save Email settings');
    showMessage('success', 'Email settings saved');
    closeAllModals();
  } catch (e) {
    console.error('Email settings save error:', e);
    showMessage('error', 'Failed to save Email settings');
  } finally {
    showLoader(false);
  }
}

function addRetryInterval() {
  const intervalsContainer = document.getElementById('retry-intervals-container');
  if (!intervalsContainer) return;
  
  const currentCount = intervalsContainer.children.length;
  
  const intervalRow = document.createElement('div');
  intervalRow.className = 'retry-interval-row';
  intervalRow.innerHTML = `
    <div class="form-group">
      <label class="form-label">Retry #${currentCount + 1} (hours)</label>
      <div class="interval-input-group">
        <input type="number" class="form-control interval-input" value="24" min="1" required>
        <button type="button" class="btn btn-danger btn-sm remove-interval" data-index="${currentCount}">×</button>
      </div>
    </div>
  `;
  
  intervalsContainer.appendChild(intervalRow);
  
  // Add event listener for the new remove button
  const removeBtn = intervalRow.querySelector('.remove-interval');
  if (removeBtn) {
    removeBtn.addEventListener('click', (e) => {
      const index = parseInt(e.target.dataset.index);
      removeRetryInterval(index);
    });
  }
}

function removeRetryInterval(index) {
  const intervalsContainer = document.getElementById('retry-intervals-container');
  if (!intervalsContainer) return;
  
  // Remove the row
  intervalsContainer.children[index].remove();
  
  // Update the labels and data-index attributes
  const rows = intervalsContainer.children;
  for (let i = 0; i < rows.length; i++) {
    const label = rows[i].querySelector('.form-label');
    const removeBtn = rows[i].querySelector('.remove-interval');
    
    if (label) label.textContent = `Retry #${i + 1} (hours)`;
    if (removeBtn) removeBtn.dataset.index = i;
  }
}

async function submitRetryConfig() {
  const maxRetriesInput = document.getElementById('max-retries');
  const intervalInputs = document.querySelectorAll('.interval-input');
  const unitsSelect = document.getElementById('retry-units');
  
  if (!maxRetriesInput || intervalInputs.length === 0) return;
  
  const maxRetries = parseInt(maxRetriesInput.value);
  const retryIntervals = Array.from(intervalInputs).map(input => parseInt(input.value));
  const units = unitsSelect ? unitsSelect.value : 'hours';
  
  // Validate inputs
  if (isNaN(maxRetries) || maxRetries < 1) {
    showMessage('error', 'Max retries must be a positive number');
    return;
  }
  
  if (retryIntervals.some(interval => isNaN(interval) || interval < 1)) {
    showMessage('error', 'All retry intervals must be positive numbers');
    return;
  }
  
  showLoader(true);
  
  try {
    const response = await fetch('/api/retry-config', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        max_retries: maxRetries,
        retry_intervals: retryIntervals,
        units
      })
    });
    
    if (!response.ok) throw new Error('Failed to update retry configuration');
    
    const data = await response.json();
    state.retryConfig = data.config;
    
    showMessage('success', 'Retry configuration updated successfully');
    closeAllModals();
    
    showLoader(false);
  } catch (error) {
    console.error('Error updating retry configuration:', error);
    showMessage('error', 'Failed to update retry configuration');
    showLoader(false);
  }
}

async function submitNewLead() {
  const form = document.getElementById('add-lead-form');
  const formData = new FormData(form);
  
  // Get and validate phone number
  let phoneNumber = formData.get('number');
  
  // Validate phone number format
  if (!isValidPhoneNumber(phoneNumber)) {
    showMessage('error', 'Please enter a valid phone number with country code (e.g., 919876543210)');
    return;
  }
  
  // Ensure it starts with a plus sign for the API
  if (!phoneNumber.startsWith('+')) {
    phoneNumber = '+' + phoneNumber;
  }
  
  const newLead = {
    name: formData.get('name'),
    number: phoneNumber,
    email: formData.get('email'),
    partner: formData.get('partner'),
    call_status: 'pending'
  };
  
  showLoader(true);
  
  try {
    const response = await fetch('/api/leads', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(newLead)
    });
    
    if (!response.ok) throw new Error('Failed to add lead');
    
    const data = await response.json();
    showMessage('success', 'New lead added successfully');
    closeAllModals();
    fetchLeads();
  } catch (error) {
    console.error('Error adding lead:', error);
    showMessage('error', 'Failed to add lead');
    showLoader(false);
  }
}

function isValidPhoneNumber(phone) {
  // Remove any non-digit characters
  const digitsOnly = phone.replace(/\D/g, '');
  
  // Check if it's between 10-15 digits (international numbers)
  return digitsOnly.length >= 10 && digitsOnly.length <= 15;
}

async function submitCsvUpload() {
  const fileInput = document.getElementById('csv-file-input');
  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    showMessage('error', 'Please choose a CSV file');
    return;
  }
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  showLoader(true);
  try {
    const resp = await fetch('/api/leads/bulk-upload', {
      method: 'POST',
      body: formData
    });
    if (!resp.ok) throw new Error('Upload failed');
    const data = await resp.json();
    showMessage('success', `Uploaded ${data.created} leads${data.errors && data.errors.length ? `, ${data.errors.length} errors` : ''}`);
    closeAllModals();
    fetchLeads();
  } catch (e) {
    console.error('Bulk upload error:', e);
    showMessage('error', 'Failed to upload CSV');
  } finally {
    showLoader(false);
  }
}

async function bulkCallEligible() {
  showLoader(true);
  try {
    const resp = await fetch('/api/leads/bulk-call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        status: ['pending', 'missed', 'failed'],
        use_batch_worker: true,
        parallel_calls: 5,
        interval_seconds: 240
      })
    });
    if (!resp.ok) throw new Error('Bulk call failed');
    const data = await resp.json();
    
    // Handle batch mode response
    if (data.batch_mode) {
      showMessage('success', `Batch calling started! Processing ${data.total_eligible} leads in batches of ${data.parallel_calls}.`);
      // Store job ID for tracking
      state.batchJobId = data.job_id;
      // Show progress indicator
      showBatchProgress();
      // Start polling for progress
      startBatchProgressPolling();
    } else {
      // Legacy sync mode
      showMessage('success', `Initiated ${data.initiated.length} calls${data.errors && data.errors.length ? `, ${data.errors.length} errors` : ''}`);
    }
    fetchLeads();
  } catch (e) {
    console.error('Bulk call error:', e);
    showMessage('error', 'Failed to start bulk calls');
  } finally {
    showLoader(false);
  }
}

// Batch progress tracking
let batchProgressTimer = null;

function showBatchProgress() {
  const existingProgress = document.getElementById('batch-progress-container');
  if (existingProgress) existingProgress.remove();
  
  const progressHTML = `
    <div id="batch-progress-container" class="batch-progress-banner">
      <div class="batch-progress-content">
        <div class="batch-progress-header">
          <h4>📞 Batch Calling in Progress</h4>
          <button id="batch-cancel-btn" class="btn btn-sm btn-danger">Cancel</button>
        </div>
        <div class="batch-progress-bar-container">
          <div id="batch-progress-bar" class="batch-progress-bar" style="width: 0%"></div>
        </div>
        <div class="batch-progress-stats">
          <span id="batch-progress-text">Initializing...</span>
        </div>
        <div class="batch-progress-details">
          <span id="batch-current-batch">Batch: -/-</span>
          <span id="batch-calls-made">Calls: 0/0</span>
          <span id="batch-next-batch">Next batch: calculating...</span>
        </div>
      </div>
    </div>
  `;
  
  const container = document.querySelector('.container');
  const firstChild = container.firstChild;
  container.insertBefore(createElementFromHTML(progressHTML), firstChild);
  
  // Add cancel handler
  document.getElementById('batch-cancel-btn').addEventListener('click', cancelBatchCall);
}

function createElementFromHTML(htmlString) {
  const div = document.createElement('div');
  div.innerHTML = htmlString.trim();
  return div.firstChild;
}

async function startBatchProgressPolling() {
  // Clear existing timer
  if (batchProgressTimer) {
    clearInterval(batchProgressTimer);
  }
  
  // Poll every 3 seconds
  batchProgressTimer = setInterval(async () => {
    try {
      const resp = await fetch('/api/batch-call/status');
      if (resp.status === 404) {
        // No active job
        stopBatchProgressPolling();
        return;
      }
      if (!resp.ok) throw new Error('Failed to fetch progress');
      
      const job = await resp.json();
      updateBatchProgress(job);
      
      // Stop polling if job completed
      if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
        stopBatchProgressPolling();
        showBatchComplete(job);
      }
    } catch (e) {
      console.error('Progress polling error:', e);
    }
  }, 3000);
}

function stopBatchProgressPolling() {
  if (batchProgressTimer) {
    clearInterval(batchProgressTimer);
    batchProgressTimer = null;
  }
}

function updateBatchProgress(job) {
  const progressBar = document.getElementById('batch-progress-bar');
  const progressText = document.getElementById('batch-progress-text');
  const currentBatch = document.getElementById('batch-current-batch');
  const callsMade = document.getElementById('batch-calls-made');
  const nextBatch = document.getElementById('batch-next-batch');
  
  if (!progressBar) return;  // Progress UI removed
  
  // Update progress bar
  progressBar.style.width = `${job.progress_percent}%`;
  
  // Update text
  progressText.textContent = `${job.calls_initiated} of ${job.total_leads} calls initiated (${job.progress_percent}%)`;
  
  // Update batch info
  currentBatch.textContent = `Batch: ${job.current_batch}/${job.total_batches}`;
  callsMade.textContent = `✅ ${job.calls_successful} successful | ❌ ${job.calls_failed} failed`;
  
  // Update next batch time
  if (job.next_batch_at) {
    const nextTime = new Date(job.next_batch_at);
    const now = new Date();
    const secondsUntil = Math.max(0, Math.floor((nextTime - now) / 1000));
    const minutes = Math.floor(secondsUntil / 60);
    const seconds = secondsUntil % 60;
    nextBatch.textContent = `Next batch: in ${minutes}m ${seconds}s`;
  } else if (job.status === 'running') {
    nextBatch.textContent = 'Next batch: processing...';
  } else {
    nextBatch.textContent = 'Next batch: -';
  }
}

function showBatchComplete(job) {
  const progressContainer = document.getElementById('batch-progress-container');
  if (!progressContainer) return;
  
  // Update UI to show completion
  const progressContent = progressContainer.querySelector('.batch-progress-content');
  
  let statusIcon = '✅';
  let statusText = 'Completed';
  let statusClass = 'success';
  
  if (job.status === 'cancelled') {
    statusIcon = '⏸️';
    statusText = 'Cancelled';
    statusClass = 'warning';
  } else if (job.status === 'failed') {
    statusIcon = '❌';
    statusText = 'Failed';
    statusClass = 'error';
  }
  
  progressContent.innerHTML = `
    <div class="batch-progress-header">
      <h4>${statusIcon} Batch Calling ${statusText}</h4>
      <button class="btn btn-sm btn-secondary" onclick="document.getElementById('batch-progress-container').remove()">Close</button>
    </div>
    <div class="batch-progress-stats">
      <p><strong>Total Leads:</strong> ${job.total_leads}</p>
      <p><strong>Calls Initiated:</strong> ${job.calls_initiated}</p>
      <p><strong>Successful:</strong> ${job.calls_successful}</p>
      <p><strong>Failed:</strong> ${job.calls_failed}</p>
    </div>
  `;
  
  // Show notification
  showMessage(statusClass, `Batch calling ${statusText.toLowerCase()}: ${job.calls_successful} successful, ${job.calls_failed} failed out of ${job.total_leads} total`);
  
  // Refresh leads to show updated statuses
  fetchLeads();
  
  // Auto-close after 10 seconds
  setTimeout(() => {
    if (progressContainer && progressContainer.parentNode) {
      progressContainer.remove();
    }
  }, 10000);
}

async function cancelBatchCall() {
  if (!state.batchJobId) return;
  
  if (!confirm('Cancel batch calling? Calls already initiated will continue, but no new calls will be made.')) {
    return;
  }
  
  try {
    const resp = await fetch('/api/batch-call/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: state.batchJobId })
    });
    
    if (!resp.ok) throw new Error('Failed to cancel');
    
    showMessage('info', 'Batch calling cancelled');
    stopBatchProgressPolling();
    
  } catch (e) {
    console.error('Cancel error:', e);
    showMessage('error', 'Failed to cancel batch calling');
  }
}

async function sendEmail(leadUuid) {
  showLoader(true);
  try {
    const resp = await fetch(`/api/leads/${leadUuid}/email`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to send email');
    }
    showMessage('success', 'Email sent');
    // Optimistically mark email_sent in table
    const lead = state.leads.find(l => l.lead_uuid === leadUuid);
    if (lead) {
      lead.email_sent = 'true';
    }
    renderLeadsTable();
    // Debounced refresh of details modal if this lead is open
    maybeDebouncedRefreshDetails(leadUuid);
  } catch (e) {
    console.error('Send email error:', e);
    showMessage('error', e.message || 'Failed to send email');
  } finally {
    showLoader(false);
  }
}

async function sendWhatsApp(leadUuid) {
  showLoader(true);
  try {
    const resp = await fetch(`/api/leads/${leadUuid}/whatsapp`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || 'Failed to send WhatsApp');
    }
    showMessage('success', 'WhatsApp sent');
    const lead = state.leads.find(l => l.lead_uuid === leadUuid);
    if (lead) {
      lead.whatsapp_sent = 'true';
    }
    renderLeadsTable();
    // Debounced refresh of details modal if this lead is open
    maybeDebouncedRefreshDetails(leadUuid);
  } catch (e) {
    console.error('Send WhatsApp error:', e);
    showMessage('error', e.message || 'Failed to send WhatsApp');
  } finally {
    showLoader(false);
  }
}

function startDetailsAutoRefresh() {
  stopDetailsAutoRefresh();
  // Auto-refresh details every 15s while modal is open
  detailsRefreshTimer = setInterval(async () => {
    if (!state.currentLeadUuid) return;
    try {
      const resp = await fetch(`/api/leads/${state.currentLeadUuid}/details`);
      if (!resp.ok) return;
      const lead = await resp.json();
      renderLeadDetails(lead);
    } catch (e) {
      // Silently ignore transient errors
    }
  }, 15000);
}

function stopDetailsAutoRefresh() {
  if (detailsRefreshTimer) {
    clearInterval(detailsRefreshTimer);
    detailsRefreshTimer = null;
  }
  if (detailsRefreshDebounce) {
    clearTimeout(detailsRefreshDebounce);
    detailsRefreshDebounce = null;
  }
}

function maybeDebouncedRefreshDetails(leadUuid) {
  if (!state.currentLeadUuid || state.currentLeadUuid !== leadUuid) return;
  if (detailsRefreshDebounce) clearTimeout(detailsRefreshDebounce);
  detailsRefreshDebounce = setTimeout(async () => {
    try {
      const resp = await fetch(`/api/leads/${leadUuid}/details`);
      if (!resp.ok) return;
      const lead = await resp.json();
      renderLeadDetails(lead);
    } catch (e) {}
  }, 1200);
}

// Rendering Functions
function renderLeadsTable() {
  const tableBody = document.getElementById('leads-table-body');
  if (!tableBody) return;
  
  tableBody.innerHTML = '';
  
  if (state.filteredLeads.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="10" class="text-center">No leads found</td>
      </tr>
    `;
    return;
  }
  
  state.filteredLeads.forEach(lead => {
    const row = document.createElement('tr');
    
    // Format next retry time if available
    let retryInfo = lead.retry_count || '0';
    if (lead.next_retry_time && (lead.call_status === 'missed' || lead.call_status === 'failed')) {
      const retryDate = new Date(lead.next_retry_time);
      const formattedTime = retryDate.toLocaleString();
      retryInfo += `<br><span class="text-sm">Next: ${formattedTime}</span>`;
    }
    
    // Always allow manual call retry regardless of status (disable only while initiated)
    const showCallButton = true;
    const isInitiated = lead.call_status === 'initiated';
    const isSelected = state.selectedLeads.has(lead.lead_uuid);

    const connectionBadge = (() => {
      if (isSuccessfulConversation(lead)) {
        return '<span class="status-badge status-connected">Connected</span>';
      }
      if (isVoicemail(lead)) {
        return '<span class="status-badge status-voicemail">Voicemail</span>';
      }
      if (lead.call_status === 'failed') {
        return '<span class="status-badge status-failed">Failed</span>';
      }
      if (isNonConnected(lead)) {
        return '<span class="status-badge status-no-answer">No Answer</span>';
      }
      return '<span class="status-badge status-pending">Pending</span>';
    })();
    
    row.innerHTML = `
      <td><input type="checkbox" class="lead-checkbox" data-uuid="${lead.lead_uuid}" ${isSelected ? 'checked' : ''}></td>
      <td>${lead.name || 'N/A'}</td>
      <td>${lead.number || 'N/A'}</td>
      <td>${lead.email || 'N/A'}</td>
      <td>${connectionBadge}</td>
      <td><span class="status-badge status-${lead.call_status || 'pending'}">${lead.call_status || 'pending'}</span></td>
      <td>
        ${lead.success_status ? 
          `<span class=\"status-badge status-${lead.success_status.toLowerCase().replace(' ', '-') }\">${lead.success_status}</span>
           ${lead.summary ? '<span class=\"analysis-indicator\" title=\"Analysis available\">📊</span>' : ''}` 
          : 'N/A'}
      </td>
      <td>${retryInfo}</td>
      <td>${lead.last_call_time ? new Date(lead.last_call_time).toLocaleString() : 'N/A'}</td>
      <td>
        <div class="btn-group">
          ${showCallButton ? `
            <button class="btn btn-primary btn-sm call-btn btn-icon-only btn-tooltip" data-title="Call" data-uuid="${lead.lead_uuid}" ${isInitiated ? 'disabled' : ''}>📞</button>
          ` : ''}
          ${(lead.email ? `<button class=\"btn btn-secondary btn-sm email-btn btn-icon-only btn-tooltip\" data-title=\"Send Email\" data-uuid=\"${lead.lead_uuid}\">✉️</button>` : '')}
          ${(lead.whatsapp_number || lead.number ? `<button class=\"btn btn-secondary btn-sm wa-btn btn-icon-only btn-tooltip\" data-title=\"Send WhatsApp\" data-uuid=\"${lead.lead_uuid}\">💬</button>` : '')}
          <button class="btn btn-secondary btn-sm view-btn btn-icon-only btn-tooltip" data-title="Details" data-uuid="${lead.lead_uuid}">👁️</button>
          <button class="btn btn-danger btn-sm delete-btn btn-icon-only btn-tooltip" data-title="Delete" data-uuid="${lead.lead_uuid}">🗑️</button>
          ${lead.email_sent === 'true' || lead.email_sent === true ? '<span class="badge small">Email Sent</span>' : ''}
          ${lead.whatsapp_sent === 'true' || lead.whatsapp_sent === true ? '<span class="badge small">WhatsApp Sent</span>' : ''}
        </div>
      </td>
    `;
    
    tableBody.appendChild(row);
  });
}

function renderStats() {
  document.getElementById('total-leads-count').textContent = state.stats.totalLeads;
  document.getElementById('completed-calls-count').textContent = state.stats.completed;
  document.getElementById('pending-calls-count').textContent = state.stats.pendingCalls;
  document.getElementById('missed-calls-count').textContent = state.stats.missed;
  document.getElementById('qualified-leads-count').textContent = state.stats.qualified;
  const pc = document.getElementById('potential-calls-count'); if (pc) pc.textContent = state.stats.potential;
  const nq = document.getElementById('not-qualified-count'); if (nq) nq.textContent = state.stats.notQualified;
  const sc = document.getElementById('successful-conv-count'); if (sc) sc.textContent = state.stats.successfulConversations;
  const vm = document.getElementById('voicemail-count'); if (vm) vm.textContent = state.stats.voicemail;
}

function calculateStats() {
  state.stats.totalLeads = state.leads.length;
  state.stats.completed = state.leads.filter(lead => lead.call_status === 'completed').length;
  state.stats.pendingCalls = state.leads.filter(lead => lead.call_status === 'pending').length;
  state.stats.qualified = state.leads.filter(lead => lead.success_status === 'Qualified').length;
  state.stats.potential = state.leads.filter(lead => lead.success_status === 'Potential').length;
  state.stats.notQualified = state.leads.filter(lead => lead.success_status === 'Not Qualified').length;
  state.stats.retries = state.leads.reduce((sum, lead) => sum + (parseInt(lead.retry_count) || 0), 0);
  state.stats.missed = state.leads.filter(lead => lead.call_status === 'missed').length;
  state.stats.successfulConversations = state.leads.filter(isSuccessfulConversation).length;
  state.stats.voicemail = state.leads.filter(isVoicemail).length;
}

function applyFilters() {
  const { status, searchQuery } = state.filters;
  
  state.filteredLeads = state.leads.filter(lead => {
    // Status filter
    if (status !== 'all' && lead.call_status !== status) {
      return false;
    }
    
    // Special quick filter
    if (state.filters.special) {
      if (state.filters.special === 'voicemail' && !isVoicemail(lead)) return false;
      if (state.filters.special === 'successful' && !isSuccessfulConversation(lead)) return false;
      if (state.filters.special === 'nonconnected' && !isNonConnected(lead)) return false;
      if (state.filters.special === 'potential' && lead.success_status !== 'Potential') return false;
      if (state.filters.special === 'notqualified' && lead.success_status !== 'Not Qualified') return false;
    }

    // Search query
    if (searchQuery && !(
      (lead.name && lead.name.toLowerCase().includes(searchQuery)) ||
      (lead.number && lead.number.toLowerCase().includes(searchQuery)) ||
      (lead.email && lead.email.toLowerCase().includes(searchQuery))
    )) {
      return false;
    }
    
    return true;
  });
  
  renderLeadsTable();
}

// Detection helpers
function isNonConnected(lead) {
  const dur = parseInt(lead.call_duration || 0);
  const hasTranscript = !!(lead.transcript && String(lead.transcript).trim().length);
  return lead.call_status === 'missed' || dur === 0 || !hasTranscript;
}

function isVoicemail(lead) {
  const reason = (lead.last_ended_reason || '').toString().toLowerCase();
  return reason.includes('voicemail') || reason.includes('voice mail') || reason.includes('answering machine');
}

function isSuccessfulConversation(lead) {
  const dur = parseInt(lead.call_duration || 0);
  const hasTranscript = !!(lead.transcript && String(lead.transcript).trim().length);
  return (lead.call_status === 'completed' && dur > 0) || hasTranscript;
}

function applyQuickFilter(type) {
  // Reset status dropdown to 'all' and set special filter
  const statusFilter = document.getElementById('status-filter');
  if (statusFilter) statusFilter.value = 'all';
  state.filters.status = 'all';
  state.filters.special = type; // one of: voicemail/successful/nonconnected/potential/notqualified
  applyFilters();
  // Optional: flash feedback
  showMessage('info', `Applied filter: ${type}`);
}

// UI Utilities
function showLoader(isLoading) {
  const loader = document.getElementById('global-loader');
  if (loader) {
    loader.style.display = isLoading ? 'inline-block' : 'none';
  }
}

function showMessage(type, message) {
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type}`;
  alertDiv.textContent = message;
  
  const container = document.querySelector('.container');
  container.insertBefore(alertDiv, container.firstChild);
  
  setTimeout(() => {
    alertDiv.remove();
  }, 5000);
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
  }
}

function closeAllModals() {
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.classList.remove('active');
  });
  
  // Reset forms
  document.querySelectorAll('form').forEach(form => form.reset());

  // Stop details auto refresh and clear active lead
  stopDetailsAutoRefresh();
  state.currentLeadUuid = null;
}


// ========================================
// BULK CALL SCHEDULING
// ========================================

function updateSelectedCount() {
  const count = state.selectedLeads.size;
  document.getElementById('selected-count').textContent = count;
  document.getElementById('modal-selected-count').textContent = count;
  
  // Show/hide schedule button based on selection
  const scheduleBtn = document.getElementById('schedule-bulk-btn');
  if (scheduleBtn) {
    scheduleBtn.style.display = count > 0 ? 'inline-block' : 'none';
  }
}

function handleCheckboxChange(event) {
  const checkbox = event.target;
  const uuid = checkbox.dataset.uuid;
  
  if (checkbox.checked) {
    state.selectedLeads.add(uuid);
  } else {
    state.selectedLeads.delete(uuid);
  }
  
  updateSelectedCount();
  updateSelectAllCheckbox();
}

function handleSelectAllChange(event) {
  const selectAll = event.target.checked;
  
  if (selectAll) {
    // Select all filtered leads
    state.filteredLeads.forEach(lead => {
      state.selectedLeads.add(lead.lead_uuid);
    });
  } else {
    // Deselect all
    state.selectedLeads.clear();
  }
  
  updateSelectedCount();
  renderLeadsTable();
}

function updateSelectAllCheckbox() {
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  if (!selectAllCheckbox) return;
  
  const allSelected = state.filteredLeads.length > 0 && 
                      state.filteredLeads.every(lead => state.selectedLeads.has(lead.lead_uuid));
  
  selectAllCheckbox.checked = allSelected;
}

function openBulkScheduleModal() {
  if (state.selectedLeads.size === 0) {
    showMessage('error', 'Please select at least one lead');
    return;
  }
  
  // Set default date and time (tomorrow at 10 AM)
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(10, 0, 0, 0);
  
  const dateInput = document.getElementById('schedule-date');
  const timeInput = document.getElementById('schedule-time');
  
  if (dateInput) {
    dateInput.value = tomorrow.toISOString().split('T')[0];
    dateInput.min = new Date().toISOString().split('T')[0]; // Can't schedule in past
  }
  
  if (timeInput) {
    timeInput.value = '10:00';
  }
  
  updateScheduleSummary();
  
  const modal = document.getElementById('bulk-schedule-modal');
  if (modal) {
    modal.classList.add('active');
  }
}

function updateScheduleSummary() {
  const dateInput = document.getElementById('schedule-date');
  const timeInput = document.getElementById('schedule-time');
  const parallelInput = document.getElementById('parallel-calls');
  const intervalInput = document.getElementById('call-interval');
  const summaryDiv = document.getElementById('schedule-summary-content');
  
  if (!dateInput || !timeInput || !parallelInput || !intervalInput || !summaryDiv) return;
  
  const selectedCount = state.selectedLeads.size;
  const parallelCalls = parseInt(parallelInput.value);
  const callInterval = parseInt(intervalInput.value);
  
  if (!dateInput.value || !timeInput.value) {
    summaryDiv.innerHTML = 'Select date and time to see estimated completion';
    return;
  }
  
  // Calculate batches
  const batchCount = Math.ceil(selectedCount / parallelCalls);
  const totalTime = (batchCount - 1) * callInterval + 180; // +3 min avg call duration
  const totalMinutes = Math.ceil(totalTime / 60);
  
  // Parse as IST timezone
  const dateTimeString = `${dateInput.value}T${timeInput.value}:00+05:30`;
  const startDateTime = new Date(dateTimeString);
  const startFormatted = startDateTime.toLocaleString('en-IN', { 
    dateStyle: 'medium', 
    timeStyle: 'short',
    timeZone: 'Asia/Kolkata'
  });
  
  // Calculate end time
  const endDateTime = new Date(startDateTime.getTime() + totalTime * 1000);
  const endFormatted = endDateTime.toLocaleString('en-IN', { 
    timeStyle: 'short',
    timeZone: 'Asia/Kolkata'
  });
  
  summaryDiv.innerHTML = `
    <div style="line-height: 1.6;">
      <div>📞 <strong>${selectedCount} leads</strong> in <strong>${batchCount} batches</strong></div>
      <div>⚡ <strong>${parallelCalls} calls</strong> per batch</div>
      <div>⏱️ <strong>${callInterval}s</strong> between batches</div>
      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd;">
        <div>🕐 Start: <strong>${startFormatted} IST</strong></div>
        <div>🏁 Est. Complete: <strong>${endFormatted} IST</strong> (~${totalMinutes} min)</div>
      </div>
    </div>
  `;
}

async function scheduleBulkCalls(event) {
  event.preventDefault();
  
  const dateInput = document.getElementById('schedule-date');
  const timeInput = document.getElementById('schedule-time');
  const parallelInput = document.getElementById('parallel-calls');
  const intervalInput = document.getElementById('call-interval');
  
  if (!dateInput || !timeInput) {
    showMessage('error', 'Please select date and time');
    return;
  }
  
  // Parse date and time as IST (Asia/Kolkata timezone)
  // Format: "2025-10-14T10:00:00+05:30"
  const dateTimeString = `${dateInput.value}T${timeInput.value}:00+05:30`;
  const startDateTime = new Date(dateTimeString);
  const now = new Date();
  
  if (startDateTime <= now) {
    showMessage('error', 'Start time must be in the future');
    return;
  }
  
  const lead_uuids = Array.from(state.selectedLeads);
  const parallel_calls = parseInt(parallelInput.value);
  const call_interval = parseInt(intervalInput.value);
  
  // Send as ISO string with IST timezone
  const startTimeIST = dateTimeString;
  
  showLoader(true);
  
  try {
    const response = await fetch('/api/schedule-bulk-calls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lead_uuids,
        start_time: startTimeIST,
        parallel_calls,
        call_interval
      })
    });
    
    const result = await response.json();
    
    if (!response.ok) {
      throw new Error(result.error || 'Failed to schedule calls');
    }
    
    showMessage('success', `✅ Scheduled ${result.scheduled_count} calls in ${result.batch_count} batches!`);
    
    // Clear selection
    state.selectedLeads.clear();
    updateSelectedCount();
    
    // Close modal
    closeAllModals();
    
    // Refresh leads
    await fetchLeads();
    
  } catch (error) {
    console.error('Error scheduling bulk calls:', error);
    showMessage('error', error.message || 'Failed to schedule bulk calls');
  } finally {
    showLoader(false);
  }
}
