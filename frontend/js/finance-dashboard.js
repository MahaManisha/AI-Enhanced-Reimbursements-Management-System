/**
 * Finance Administrator Dashboard Controller
 * AI-Enhanced Reimbursements Management System
 * 
 * Manages executive financial audit views:
 * - Live KPI metrics (Awaiting Decision, Approved, Rejected, Total Volume)
 * - Dynamic Chart.js visualizations (Status Distribution, Category Spend, Monthly Trends)
 * - Immediate High-Rejection-Risk alert cards
 * - Filterable claims inspection table
 * - Claim review modal with ML risk breakdown and Generative AI audit copilot
 * - Direct claim approval and rejection with mandatory justification
 * - Category management modal
 */

let statusChart = null;
let categoryChart = null;
let monthlyTrendChart = null;
let currentClaimInReview = null;

document.addEventListener("DOMContentLoaded", async () => {
    if (!Auth.requireAuth(["ADMIN"])) return;

    setupNavigation();
    await loadEmployeesFilter();
    await loadCategoriesFilter();
    await loadAdminAnalytics();
    await loadAdminClaims();
    setupEventListeners();
});

/**
 * Initializes sidebar user profile badge and sign-out handler.
 */
function setupNavigation() {
    const user = Auth.getCurrentUser();
    if (user) {
        const nameEl = document.querySelector(".user-name");
        const roleEl = document.querySelector(".user-role");
        const avatarEl = document.querySelector(".user-avatar");
        if (nameEl && user.full_name) nameEl.textContent = user.full_name;
        if (roleEl) roleEl.textContent = user.department || (user.role === "ADMIN" ? "Finance & Accounts" : "Employee");
        if (avatarEl && user.full_name) {
            const initials = user.full_name.split(" ").filter(Boolean).map(n => n[0]).join("").substring(0, 2).toUpperCase();
            if (initials) avatarEl.textContent = initials;
        }
    }
    document.getElementById("logout-btn")?.addEventListener("click", () => Auth.logout());
}

/**
 * Global manual refresh triggered by user clicking 'Refresh'.
 */
window.refreshDashboard = async function() {
    await loadAdminAnalytics();
    await loadAdminClaims();
};

/**
 * Populates employee dropdown for administrative filtering.
 */
async function loadEmployeesFilter() {
    try {
        const res = await API.get("/admin/employees");
        const select = document.getElementById("filter-employee");
        if (res.employees && select) {
            select.innerHTML = '<option value="">All Employees</option>' +
                res.employees.map(e => `<option value="${e.id}">${e.full_name} (${e.department})</option>`).join("");
        }
    } catch (err) {
        console.error("Failed to load employees for filter:", err);
    }
}

/**
 * Populates category dropdown for administrative filtering.
 */
async function loadCategoriesFilter() {
    try {
        const res = await API.get("/categories?all=true");
        const select = document.getElementById("filter-category");
        if (res.categories && select) {
            select.innerHTML = '<option value="">All Categories</option>' +
                res.categories.map(c => `<option value="${c.id}">${c.category_name}</option>`).join("");
        }
    } catch (err) {
        console.error("Failed to load categories for filter:", err);
    }
}

/**
 * Loads executive KPI statistics, charts, and high-risk claim alerts.
 */
async function loadAdminAnalytics() {
    try {
        const res = await API.get("/admin/analytics");
        if (!res.success) return;

        const summary = res.summary || {};
        document.getElementById("stat-pending").textContent = summary.pending_claims || 0;
        document.getElementById("stat-approved").textContent = summary.approved_claims || 0;
        document.getElementById("stat-rejected").textContent = summary.rejected_claims || 0;
        document.getElementById("stat-total-amount").textContent = ReimbursementUI.formatCurrency(summary.total_amount_claimed || 0);

        renderStatusChart(res.status_distribution || []);
        renderCategoryChart(res.category_distribution || []);
        renderMonthlyTrendChart(res.monthly_trends || []);
        renderHighRiskAlerts(res.high_risk_claims || []);
    } catch (err) {
        console.error("Failed to load admin analytics:", err);
    }
}

/**
 * Renders the claim status doughnut chart.
 */
function renderStatusChart(data) {
    const ctx = document.getElementById("statusChart");
    const emptyEl = document.getElementById("statusChart-empty");
    if (!ctx) return;

    if (statusChart) {
        statusChart.destroy();
        statusChart = null;
    }

    const hasData = Array.isArray(data) && data.length > 0 && data.some(d => d.count > 0);
    if (!hasData) {
        ctx.style.display = "none";
        if (emptyEl) emptyEl.style.display = "flex";
        return;
    }

    ctx.style.display = "block";
    if (emptyEl) emptyEl.style.display = "none";

    const labels = data.map(d => d.status);
    const counts = data.map(d => d.count);
    const statusColors = {
        "PENDING": "#f59e0b",
        "APPROVED": "#16a34a",
        "REJECTED": "#dc2626"
    };
    const colors = labels.map(s => statusColors[s] || "#94a3b8");

    statusChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { boxWidth: 12 } }
            },
            cutout: "60%"
        }
    });
}

/**
 * Renders expenditure by category bar chart.
 */
function renderCategoryChart(data) {
    const ctx = document.getElementById("categoryChart");
    const emptyEl = document.getElementById("categoryChart-empty");
    if (!ctx) return;

    if (categoryChart) {
        categoryChart.destroy();
        categoryChart = null;
    }

    const hasData = Array.isArray(data) && data.length > 0 && data.some(d => d.amount > 0);
    if (!hasData) {
        ctx.style.display = "none";
        if (emptyEl) emptyEl.style.display = "flex";
        return;
    }

    ctx.style.display = "block";
    if (emptyEl) emptyEl.style.display = "none";

    const labels = data.map(d => d.category);
    const amounts = data.map(d => d.amount);

    categoryChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Expenditure ($)",
                data: amounts,
                backgroundColor: "#ea580c",
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: v => "$" + v }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

/**
 * Renders monthly audit volume line chart.
 */
function renderMonthlyTrendChart(data) {
    const ctx = document.getElementById("trendChart");
    const emptyEl = document.getElementById("trendChart-empty");
    if (!ctx) return;

    if (monthlyTrendChart) {
        monthlyTrendChart.destroy();
        monthlyTrendChart = null;
    }

    const hasData = Array.isArray(data) && data.length > 0 && data.some(d => (d.claimed_amount > 0 || d.approved_amount > 0));
    if (!hasData) {
        ctx.style.display = "none";
        if (emptyEl) emptyEl.style.display = "flex";
        return;
    }

    ctx.style.display = "block";
    if (emptyEl) emptyEl.style.display = "none";

    const labels = data.map(d => d.month);
    const claimed = data.map(d => d.claimed_amount);
    const approved = data.map(d => d.approved_amount);

    monthlyTrendChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Claimed Amount ($)",
                    data: claimed,
                    borderColor: "#94a3b8",
                    backgroundColor: "rgba(148, 163, 184, 0.1)",
                    fill: true,
                    tension: 0.3
                },
                {
                    label: "Approved Amount ($)",
                    data: approved,
                    borderColor: "#ea580c",
                    backgroundColor: "rgba(234, 88, 12, 0.1)",
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: v => "$" + v }
                }
            }
        }
    });
}

/**
 * Displays prominent alert cards for claims classified as HIGH_REJECTION_RISK.
 */
function renderHighRiskAlerts(claims) {
    const container = document.getElementById("high-risk-alerts-container");
    if (!container) return;

    if (!claims || claims.length === 0) {
        container.innerHTML = "";
        container.style.display = "none";
        return;
    }

    container.style.display = "block";
    container.innerHTML = `
        <div style="background:#ffffff;border:1px solid #fecaca;border-left:4px solid #dc2626;border-radius:var(--radius-sm);padding:16px 20px;margin-bottom:24px;">
            <div style="font-weight:700;color:#991b1b;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
                <span>High Rejection Risk Claims Requiring Immediate Audit</span>
                <span class="badge" style="background:#fee2e2;color:#991b1b;font-weight:700;">${claims.length}</span>
            </div>
            <div style="display:flex;flex-direction:column;gap:8px;">
                ${claims.map(c => `
                    <div style="display:flex;justify-content:space-between;align-items:center;background:#ffffff;padding:12px 14px;border-radius:var(--radius-sm);border:1px solid #fee2e2;flex-wrap:wrap;gap:10px;">
                        <div>
                            <strong>#${c.id} - ${c.employee_name} (${c.department || c.employee_department || ''})</strong> &bull;
                            <span style="color:#b91c1c;font-weight:700;">${ReimbursementUI.formatCurrency(c.amount)}</span> for <strong>${c.category_name}</strong>
                            ${!c.bill_available ? '<span style="color:#dc2626;font-size:12px;margin-left:8px;font-weight:600;">(No Receipt)</span>' : '<span style="color:#16a34a;font-size:12px;margin-left:8px;font-weight:600;">(Receipt Attached)</span>'}
                            <div style="font-size:12px;color:var(--slate-500);margin-top:2px;">Submitted on ${ReimbursementUI.formatDate(c.expense_date)}: ${c.description || ''}</div>
                        </div>
                        <button type="button" class="btn btn-sm btn-primary btn-review-claim" data-id="${c.id}" onclick="openReviewModal('${c.id}')">Review Now</button>
                    </div>
                `).join("")}
            </div>
        </div>
    `;
}

/**
 * Fetches filtered claims for admin review.
 */
async function loadAdminClaims() {
    const params = {
        status: document.getElementById("filter-status")?.value || "",
        category_id: document.getElementById("filter-category")?.value || "",
        employee_id: document.getElementById("filter-employee")?.value || "",
        risk: document.getElementById("filter-risk")?.value || "",
        search: document.getElementById("search-input")?.value || ""
    };

    try {
        const res = await API.get("/admin/reimbursements", params);
        if (res.success) {
            renderAdminTable(res.claims || []);
        }
    } catch (err) {
        console.error("Failed to load admin claims:", err);
    }
}

/**
 * Renders claims in the administrative review table.
 */
function renderAdminTable(claims) {
    const tbody = document.getElementById("claims-table-body");
    const emptyState = document.getElementById("empty-state");
    const emptyTitle = document.getElementById("empty-state-title");
    const emptySub = document.getElementById("empty-state-sub");
    if (!tbody) return;

    if (!claims || claims.length === 0) {
        tbody.innerHTML = "";
        if (emptyState) {
            emptyState.style.display = "block";
            const hasFilters = Boolean(
                document.getElementById("filter-status")?.value ||
                document.getElementById("filter-category")?.value ||
                document.getElementById("filter-employee")?.value ||
                document.getElementById("filter-risk")?.value ||
                (document.getElementById("search-input")?.value || "").trim()
            );

            if (hasFilters) {
                if (emptyTitle) emptyTitle.textContent = "No claims matched your search filters";
                if (emptySub) emptySub.textContent = "Adjust the filter selections above to broaden your query.";
            } else {
                if (emptyTitle) emptyTitle.textContent = "No reimbursement claims available yet.";
                if (emptySub) emptySub.textContent = "Employee reimbursement claims will appear here once submitted.";
            }
        }
        return;
    }

    if (emptyState) emptyState.style.display = "none";

    tbody.innerHTML = claims.map(c => `
        <tr>
            <td><strong>#${c.id}</strong></td>
            <td>
                <div><strong>${c.employee_name}</strong></div>
                <div style="font-size:12px;color:var(--slate-500);">${c.employee_department}</div>
            </td>
            <td>${ReimbursementUI.formatDate(c.expense_date)}</td>
            <td><strong>${c.category_name}</strong></td>
            <td>${ReimbursementUI.formatCurrency(c.amount)}</td>
            <td>
                ${c.bill_available
                    ? `<button type="button" class="btn btn-sm btn-secondary btn-view-receipt" data-id="${c.id}" onclick="viewReceipt('${c.id}')" title="View attached receipt">View</button>`
                    : `<span style="color:var(--slate-400);font-size:12px;">Missing</span>`
                }
            </td>
            <td>${ReimbursementUI.getRiskBadge(c.ml_prediction, c.ml_confidence)}</td>
            <td>${ReimbursementUI.getStatusBadge(c.claim_status)}</td>
            <td>
                <button type="button" class="btn btn-sm btn-primary btn-review-claim" data-id="${c.id}" onclick="openReviewModal('${c.id}')">Review</button>
            </td>
        </tr>
    `).join("");
}

/**
 * Sets up filtering, debounced search, and event delegation listeners.
 */
function setupEventListeners() {
    document.getElementById("filter-status")?.addEventListener("change", loadAdminClaims);
    document.getElementById("filter-category")?.addEventListener("change", loadAdminClaims);
    document.getElementById("filter-employee")?.addEventListener("change", loadAdminClaims);
    document.getElementById("filter-risk")?.addEventListener("change", loadAdminClaims);
    document.getElementById("search-input")?.addEventListener("input", debounce(loadAdminClaims, 300));

    // Event delegation on table body for dynamically generated Review and View buttons
    document.getElementById("claims-table-body")?.addEventListener("click", (e) => {
        const reviewBtn = e.target.closest(".btn-review-claim");
        if (reviewBtn && reviewBtn.dataset.id) {
            e.preventDefault();
            openReviewModal(reviewBtn.dataset.id);
            return;
        }
        const viewBtn = e.target.closest(".btn-view-receipt");
        if (viewBtn && viewBtn.dataset.id) {
            e.preventDefault();
            viewReceipt(viewBtn.dataset.id);
            return;
        }
    });

    // Event delegation on high risk alerts container
    document.getElementById("high-risk-alerts-container")?.addEventListener("click", (e) => {
        const reviewBtn = e.target.closest(".btn-review-claim");
        if (reviewBtn && reviewBtn.dataset.id) {
            e.preventDefault();
            openReviewModal(reviewBtn.dataset.id);
            return;
        }
    });
}

/**
 * Standard debounce utility to throttle real-time search queries.
 */
function debounce(func, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => func(...args), delay);
    };
}

/**
 * Opens claim review dossier modal.
 */
window.openReviewModal = async function(claimId) {
    if (!claimId) {
        console.error("openReviewModal called without a valid claim ID.");
        return;
    }

    const modal = document.getElementById("review-modal");
    if (!modal) {
        console.error("Review modal element '#review-modal' not found in DOM.");
        return;
    }

    modal.classList.add("show");
    document.getElementById("review-loading").style.display = "block";
    document.getElementById("review-content").style.display = "none";

    try {
        const res = await API.get(`/admin/reimbursements/${claimId}`);
        if (!res.success) throw new Error(res.error || "Failed to retrieve claim details");

        const c = res.claim;
        currentClaimInReview = c;

        document.getElementById("rev-id").textContent = `#${c.id}`;
        const dossierBtn = document.getElementById("rev-full-dossier-btn");
        if (dossierBtn) {
            dossierBtn.href = `/reimbursement-details.html?id=${c.id}`;
        }

        document.getElementById("rev-employee").textContent = c.employee_name || "-";
        const deptEl = document.getElementById("rev-department");
        if (deptEl) {
            deptEl.textContent = c.employee_department || "-";
        }
        document.getElementById("rev-category").textContent = c.category_name || "-";
        document.getElementById("rev-amount").textContent = ReimbursementUI.formatCurrency(c.amount);
        document.getElementById("rev-date").textContent = ReimbursementUI.formatDate(c.expense_date);
        document.getElementById("rev-status").innerHTML = ReimbursementUI.getStatusBadge(c.claim_status || c.status);
        document.getElementById("rev-desc").textContent = c.description || "No description provided.";

        // Receipt attachment box with working authenticated viewer
        const receiptBox = document.getElementById("rev-receipt-box");
        if (c.bill_available) {
            receiptBox.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:space-between;background:#f8fafc;padding:12px 14px;border-radius:6px;border:1px solid #e2e8f0;">
                    <div>
                        <strong>Receipt Document:</strong> <span>${c.bill_original_name || c.receipt_filename || "Attached Bill"}</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-primary btn-view-receipt" data-id="${c.id}" onclick="viewReceipt('${c.id}')">View Receipt</button>
                </div>
            `;
        } else {
            receiptBox.innerHTML = `
                <div style="background:#fef2f2;border:1px solid #fecaca;padding:12px 14px;border-radius:6px;color:#b91c1c;font-size:13px;">
                    No receipt was attached by the employee for this claim.
                </div>
            `;
        }

        // ML Risk card with confidence and probability distribution breakdown
        const confPct = c.ml_confidence ? (c.ml_confidence * 100).toFixed(1) : "0";
        let probHtml = "";
        let probs = c.ml_probabilities;
        if (typeof probs === "string") {
            try { probs = JSON.parse(probs); } catch(e) {}
        }
        if (probs && typeof probs === "object") {
            probHtml = `
                <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid #e2e8f0;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--slate-700); margin-bottom: 8px;">Random Forest Class Probability Distribution:</div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px;">
                        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 8px 10px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; font-weight: 600; color: #166534;">Likely Approved</div>
                            <div style="font-size: 15px; font-weight: 700; color: #15803d;">${((probs.LIKELY_APPROVED || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div style="background: #fffbeb; border: 1px solid #fde68a; padding: 8px 10px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; font-weight: 600; color: #92400e;">Requires Review</div>
                            <div style="font-size: 15px; font-weight: 700; color: #b45309;">${((probs.REQUIRES_REVIEW || 0) * 100).toFixed(1)}%</div>
                        </div>
                        <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 8px 10px; border-radius: 6px; text-align: center;">
                            <div style="font-size: 11px; font-weight: 600; color: #991b1b;">High Rejection Risk</div>
                            <div style="font-size: 15px; font-weight: 700; color: #b91c1c;">${((probs.HIGH_REJECTION_RISK || 0) * 100).toFixed(1)}%</div>
                        </div>
                    </div>
                </div>
            `;
        }

        document.getElementById("rev-ml-box").innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div><strong>ML Predicted Risk:</strong> ${ReimbursementUI.getRiskBadge(c.ml_prediction, c.ml_confidence)}</div>
                <div style="font-size:13px;color:var(--slate-600);">Model Confidence: <strong>${confPct}%</strong></div>
            </div>
            <div class="ml-meter">
                <div class="ml-meter-fill" style="width:${confPct}%; background:${c.ml_prediction === 'LIKELY_APPROVED' ? '#16a34a' : c.ml_prediction === 'REQUIRES_REVIEW' ? '#d97706' : '#dc2626'};"></div>
            </div>
            ${probHtml}
            <div style="font-size:11px;color:var(--slate-500);margin-top:8px;">
                Predictive risk classification is an advisory model recommendation; final authorization is required from finance personnel.
            </div>
        `;

        // Generative AI insights
        document.getElementById("rev-ai-summary").textContent = c.ai_summary || c.summary || "AI Summary not generated.";
        document.getElementById("rev-ai-obs").textContent = c.ai_observations || c.genai_observations || "No observations noted.";
        document.getElementById("rev-ai-missing").textContent = c.ai_missing_info || c.missing_documents || "None.";
        document.getElementById("rev-ai-actions").textContent = c.ai_suggested_actions || c.suggested_actions || "Inspect per company guidelines.";

        // Action Buttons state
        const actionsContainer = document.getElementById("review-actions-buttons");
        const statusVal = c.claim_status || c.status;
        if (statusVal === "APPROVED") {
            actionsContainer.innerHTML = `<span class="badge badge-approved" style="font-size:14px;padding:8px 14px;">Already Approved</span>`;
        } else if (statusVal === "REJECTED") {
            actionsContainer.innerHTML = `<span class="badge badge-rejected" style="font-size:14px;padding:8px 14px;">Already Rejected</span>`;
        } else {
            actionsContainer.innerHTML = `
                <button type="button" class="btn btn-danger" onclick="promptRejectModal('${c.id}')">Reject Claim</button>
                <button type="button" class="btn btn-success" onclick="approveClaimDirect('${c.id}')">Approve Claim</button>
            `;
        }

        // Audit Trail
        ReimbursementUI.renderAuditTrail(res.audit_logs, document.getElementById("rev-audit-logs"));

        document.getElementById("review-loading").style.display = "none";
        document.getElementById("review-content").style.display = "block";
    } catch (err) {
        alert("Failed to load claim details: " + err.message);
        modal.classList.remove("show");
    }
};

/**
 * Handles administrator approval action.
 */
window.approveClaimDirect = async function(claimId) {
    const comments = prompt("Enter optional approval comments / disbursement notes:", "Approved per financial policy guidelines.");
    if (comments === null) return;

    try {
        const res = await API.post(`/admin/reimbursements/${claimId}/approve`, { comments });
        if (!res.success) throw new Error(res.error);

        alert(`Claim #${claimId} approved successfully.`);
        closeModal("review-modal");
        await loadAdminAnalytics();
        await loadAdminClaims();
    } catch (err) {
        alert("Approval failed: " + err.message);
    }
};

/**
 * Opens rejection reason input modal.
 */
window.promptRejectModal = function(claimId) {
    document.getElementById("reject-claim-id").value = claimId;
    document.getElementById("reject-reason-input").value = "";
    document.getElementById("reject-comments-input").value = "";
    document.getElementById("reject-alert").style.display = "none";
    document.getElementById("reject-modal").classList.add("show");
};

/**
 * Submits documented rejection decision to backend.
 */
window.submitRejection = async function() {
    const claimId = document.getElementById("reject-claim-id").value;
    const reason = (document.getElementById("reject-reason-input").value || "").trim();
    const comments = (document.getElementById("reject-comments-input").value || "").trim();
    const alertBox = document.getElementById("reject-alert");

    if (!reason || reason.length < 5) {
        alertBox.textContent = "A clear rejection reason is mandatory (minimum 5 characters).";
        alertBox.style.display = "block";
        return;
    }

    try {
        const res = await API.post(`/admin/reimbursements/${claimId}/reject`, {
            rejection_reason: reason,
            comments: comments || reason
        });

        if (!res.success) throw new Error(res.error);

        alert(`Claim #${claimId} has been rejected.`);
        closeModal("reject-modal");
        closeModal("review-modal");
        await loadAdminAnalytics();
        await loadAdminClaims();
    } catch (err) {
        alertBox.textContent = err.message || "Failed to reject claim.";
        alertBox.style.display = "block";
    }
};

/**
 * Opens category management modal.
 */
window.openCategoriesModal = async function() {
    const modal = document.getElementById("categories-modal");
    if (!modal) return;
    modal.classList.add("show");
    await renderCategoriesManagerList();
};

/**
 * Renders categories management list inside modal.
 */
async function renderCategoriesManagerList() {
    try {
        const res = await API.get("/categories?all=true");
        const listContainer = document.getElementById("categories-list");
        if (!listContainer || !res.categories) return;

        listContainer.innerHTML = res.categories.map(c => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:12px;border-bottom:1px solid #e2e8f0;">
                <div>
                    <strong>${c.category_name}</strong>
                    <div style="font-size:12px;color:var(--slate-500);">${c.description || "No description"}</div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <span class="badge ${c.active ? 'badge-approved' : 'badge-rejected'}">${c.active ? 'Active' : 'Inactive'}</span>
                    <button class="btn btn-sm btn-secondary" onclick="toggleCategoryActive('${c.id}', ${!c.active})">
                        ${c.active ? 'Disable' : 'Enable'}
                    </button>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Failed to load categories list:", err);
    }
}

/**
 * Toggles an expense category's active state.
 */
window.toggleCategoryActive = async function(catId, active) {
    try {
        await API.put(`/admin/categories/${catId}`, { active });
        await renderCategoriesManagerList();
        await loadCategoriesFilter();
    } catch (err) {
        alert("Failed to update category: " + err.message);
    }
};

/**
 * Submits a new expense category from modal.
 */
window.submitNewCategory = async function() {
    const nameInput = document.getElementById("new-cat-name");
    const descInput = document.getElementById("new-cat-desc");
    const name = nameInput.value.trim();
    const description = descInput.value.trim();

    if (!name) {
        alert("Please enter a category name.");
        return;
    }

    try {
        await API.post("/admin/categories", { category_name: name, description });
        nameInput.value = "";
        descInput.value = "";
        await renderCategoriesManagerList();
        await loadCategoriesFilter();
    } catch (err) {
        alert("Failed to create category: " + err.message);
    }
};

/**
 * Closes modal by ID.
 */
window.closeModal = function(id) {
    document.getElementById(id)?.classList.remove("show");
};
