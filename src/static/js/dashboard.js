// Dashboard functionality for Smart Presales

// Global state
const state = {
  leads: [],
  filteredLeads: [],
  stats: {
    totalLeads: 0,
    completed: 0,
    qualified: 0,
    potential: 0,
    notQualified: 0,
    pendingCalls: 0,
    retries: 0,
    missed: 0
  },
  filters: {
    status: 'all',
    searchQuery: ''
  },
  retryConfig: {
    max_retries: 3,
    retry_intervals: [1, 4, 24]
  }
};

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
  // Initial data load
  fetchLeads();
  
  // Fetch retry configuration
  fetchRetryConfig();
  
  // Set up event listeners
  setupEventListeners();
});

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
  
  // Event delegation for dynamic buttons
  document.addEventListener('click', (e) => {
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
}

// API Functions
let activeRefreshTimer = null;

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
  
  try {
    const response = await fetch(`/api/leads/${leadUuid}/call`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to initiate call');
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
          ${entry.summary ? `<div class="history-summary">${entry.summary}</div>` : ''}
          ${entry.success_status ? `<div class="history-success">Result: <span class="status-badge status-${entry.success_status.toLowerCase().replace(' ', '-')}">${entry.success_status}</span></div>` : ''}
        </div>
      `;
    });
    callHistoryHtml += '</div>';
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
            <strong>Last Call:</strong> ${lead.last_call_time ? new Date(lead.last_call_time).toLocaleString() : 'N/A'}
          </div>
          <div class="detail-item">
            <strong>Next Retry:</strong> ${lead.next_retry_time ? new Date(lead.next_retry_time).toLocaleString() : 'N/A'}
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
          <strong>Structured Data:</strong>
          ${structuredDataHtml}
        </div>
      </div>
      
      <div class="detail-section">
        <h4 class="section-title">Call History</h4>
        ${callHistoryHtml}
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
      body: JSON.stringify({ status: ['pending', 'missed', 'failed'], limit: 25 })
    });
    if (!resp.ok) throw new Error('Bulk call failed');
    const data = await resp.json();
    showMessage('success', `Initiated ${data.initiated.length} calls${data.errors && data.errors.length ? `, ${data.errors.length} errors` : ''}`);
    fetchLeads();
  } catch (e) {
    console.error('Bulk call error:', e);
    showMessage('error', 'Failed to start bulk calls');
  } finally {
    showLoader(false);
  }
}

// Rendering Functions
function renderLeadsTable() {
  const tableBody = document.getElementById('leads-table-body');
  if (!tableBody) return;
  
  tableBody.innerHTML = '';
  
  if (state.filteredLeads.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center">No leads found</td>
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
    
    // Determine if call button should be shown
    const showCallButton = lead.call_status === 'pending' || 
                          (lead.call_status === 'missed' || lead.call_status === 'failed');
    const isInitiated = lead.call_status === 'initiated';
    
    row.innerHTML = `
      <td>${lead.name || 'N/A'}</td>
      <td>${lead.number || 'N/A'}</td>
      <td>${lead.email || 'N/A'}</td>
      <td><span class="status-badge status-${lead.call_status || 'pending'}">${lead.call_status || 'pending'}</span></td>
      <td>
        ${lead.success_status ? 
          `<span class="status-badge status-${lead.success_status.toLowerCase().replace(' ', '-')}">${lead.success_status}</span>
           ${lead.summary ? '<span class="analysis-indicator" title="Analysis available">📊</span>' : ''}` 
          : 'N/A'}
      </td>
      <td>${retryInfo}</td>
      <td>${lead.last_call_time ? new Date(lead.last_call_time).toLocaleString() : 'N/A'}</td>
      <td>
        <div class="btn-group">
          ${showCallButton ? `
            <button class="btn btn-primary btn-sm call-btn" data-uuid="${lead.lead_uuid}" ${isInitiated ? 'disabled' : ''}>${isInitiated ? 'Calling…' : 'Call'}</button>
          ` : ''}
          <button class="btn btn-secondary btn-sm view-btn" data-uuid="${lead.lead_uuid}">
            ${lead.summary ? '<span class="btn-icon">📋</span> View Analysis' : 'Details'}
          </button>
          <button class="btn btn-danger btn-sm delete-btn" data-uuid="${lead.lead_uuid}">Delete</button>
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
}

function applyFilters() {
  const { status, searchQuery } = state.filters;
  
  state.filteredLeads = state.leads.filter(lead => {
    // Status filter
    if (status !== 'all' && lead.call_status !== status) {
      return false;
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
}
