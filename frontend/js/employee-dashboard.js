/**
 * Employee Dashboard Controller
 * AI-Enhanced Reimbursements Management System
 * 
 * Manages the employee dashboard view:
 * - Live statistical summary cards (Total, Pending, Approved, Rejected, Amount)
 * - Category breakdown and monthly trend Chart.js visualizations
 * - Filterable reimbursement history table
 * - Modal claim submission with real-time ML & Generative AI evaluation
 * - Claim details modal with ML risk meter and AI audit insights
 */

let categoryChart = null;
let monthlyChart = null;
let allMyClaims = [];

document.addEventListener("DOMContentLoaded", async () => {
    if (!Auth.requireAuth(["EMPLOYEE"])) return;

    setupNavigation();
    await loadCategories();
    await loadAnalytics();
    await loadClaims();
    setupEventListeners();
    checkSubmissionStatus();
});

/**
 * Checks query parameters for newly submitted claim notifications.
 */
function checkSubmissionStatus() {
    const params = new URLSearchParams(window.location.search);
    const submittedId = params.get("submitted");
    if (submittedId) {
        const noticeEl = document.getElementById("dashboard-notice");
        if (noticeEl) {
            noticeEl.innerHTML = `<strong>Claim Submitted Successfully:</strong> Reimbursement claim <strong>#${submittedId}</strong> has been submitted and queued for review.`;
            noticeEl.style.display = "block";
            window.history.replaceState({}, document.title, window.location.pathname);
            setTimeout(() => {
                noticeEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }, 100);
        }
    }
}

/**
 * Populates current employee identity in the sidebar.
 */
function setupNavigation() {
    const user = Auth.getCurrentUser();
    if (user) {
        const nameEl = document.querySelector(".user-name");
        const roleEl = document.querySelector(".user-role");
        const avatarEl = document.querySelector(".user-avatar");
        if (nameEl && user.full_name) nameEl.textContent = user.full_name;
        if (roleEl) roleEl.textContent = user.department || "Employee";
        if (avatarEl && user.full_name) {
            const initials = user.full_name.split(" ").filter(Boolean).map(n => n[0]).join("").substring(0, 2).toUpperCase();
            if (initials) avatarEl.textContent = initials;
        }
    }
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => Auth.logout());
    }
}

/**
 * Loads active categories into form and filter dropdowns.
 */
async function loadCategories() {
    try {
        const res = await API.get("/categories");
        const select = document.getElementById("claim-category");
        const filterSelect = document.getElementById("filter-category");

        if (res.categories && select) {
            select.innerHTML = '<option value="">Select Category...</option>' +
                res.categories.map(c => `<option value="${c.id}">${c.category_name}</option>`).join("");
        }

        if (res.categories && filterSelect) {
            filterSelect.innerHTML = '<option value="">All Categories</option>' +
                res.categories.map(c => `<option value="${c.id}">${c.category_name}</option>`).join("");
        }
    } catch (err) {
        console.error("Failed to load categories:", err);
    }
}

/**
 * Fetches personal statistical aggregations and renders dashboard charts.
 */
async function loadAnalytics() {
    try {
        const res = await API.get("/employee/analytics");
        if (!res.success) return;

        const summary = res.summary || {};
        document.getElementById("stat-total").textContent = summary.total_claims || 0;
        document.getElementById("stat-pending").textContent = summary.pending_claims || 0;
        document.getElementById("stat-approved").textContent = summary.approved_claims || 0;
        document.getElementById("stat-rejected").textContent = summary.rejected_claims || 0;
        document.getElementById("stat-amount").textContent = ReimbursementUI.formatCurrency(summary.total_approved || 0);

        renderCategoryChart(res.category_breakdown || []);
        renderMonthlyChart(res.monthly_trends || []);
    } catch (err) {
        console.error("Failed to load employee analytics:", err);
    }
}

/**
 * Renders the expense breakdown doughnut chart.
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
    const palette = ["#ea580c", "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#06b6d4", "#64748b"];

    categoryChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: amounts,
                backgroundColor: palette.slice(0, labels.length),
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: "right", labels: { boxWidth: 12, font: { size: 12 } } },
                tooltip: {
                    callbacks: {
                        label: (c) => ` ${c.label}: $${Number(c.raw).toFixed(2)}`
                    }
                }
            },
            cutout: "65%"
        }
    });
}

/**
 * Renders the monthly expense volume bar chart.
 */
function renderMonthlyChart(data) {
    const ctx = document.getElementById("monthlyChart");
    const emptyEl = document.getElementById("monthlyChart-empty");
    if (!ctx) return;

    if (monthlyChart) {
        monthlyChart.destroy();
        monthlyChart = null;
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

    monthlyChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Claimed Amount",
                    data: claimed,
                    backgroundColor: "#94a3b8",
                    borderRadius: 4
                },
                {
                    label: "Approved Amount",
                    data: approved,
                    backgroundColor: "#ea580c",
                    borderRadius: 4
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
            },
            plugins: {
                legend: { position: "top", labels: { boxWidth: 12 } }
            }
        }
    });
}

/**
 * Loads employee claims from backend.
 */
async function loadClaims() {
    try {
        const res = await API.get("/reimbursements/my");
        if (res.success) {
            allMyClaims = res.claims || [];
            applyFilters();
        }
    } catch (err) {
        console.error("Failed to load claims:", err);
    }
}

/**
 * Filters the in-memory claims list by status, category, and search text.
 */
function applyFilters() {
    const status = document.getElementById("filter-status")?.value || "";
    const category = document.getElementById("filter-category")?.value || "";
    const search = (document.getElementById("search-input")?.value || "").toLowerCase().trim();

    const filtered = allMyClaims.filter(c => {
        if (status && c.claim_status !== status) return false;
        if (category && String(c.category_id) !== String(category)) return false;
        if (search) {
            const matchDesc = (c.description || "").toLowerCase().includes(search);
            const matchCat = (c.category_name || "").toLowerCase().includes(search);
            if (!matchDesc && !matchCat) return false;
        }
        return true;
    });

    renderClaimsTable(filtered);
}

/**
 * Populates the reimbursement history table.
 */
function renderClaimsTable(claims) {
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
                (document.getElementById("search-input")?.value || "").trim()
            );

            if (hasFilters) {
                if (emptyTitle) emptyTitle.textContent = "No claims matched your search filters";
                if (emptySub) emptySub.textContent = "Adjust the filter selections above to broaden your query.";
            } else {
                if (emptyTitle) emptyTitle.textContent = "No reimbursement requests submitted yet.";
                if (emptySub) emptySub.textContent = "Submit a new reimbursement claim to get started.";
            }
        }
        return;
    }

    if (emptyState) emptyState.style.display = "none";

    tbody.innerHTML = claims.map(c => `
        <tr>
            <td><strong>#${c.id}</strong></td>
            <td>${ReimbursementUI.formatDate(c.expense_date)}</td>
            <td><strong>${c.category_name}</strong></td>
            <td>${ReimbursementUI.formatCurrency(c.amount)}</td>
            <td>
                ${c.bill_available
                    ? `<button type="button" class="btn btn-sm btn-secondary" onclick="viewReceipt('${c.id}')" title="View attached receipt">View</button>`
                    : `<span style="color:var(--slate-400);font-size:12px;">No Receipt</span>`
                }
            </td>
            <td>${ReimbursementUI.getRiskBadge(c.ml_prediction, c.ml_confidence)}</td>
            <td>${ReimbursementUI.getStatusBadge(c.claim_status)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewClaimDetails('${c.id}')">Details</button>
            </td>
        </tr>
    `).join("");
}

/**
 * Configures filter and form event listeners.
 */
function setupEventListeners() {
    document.getElementById("filter-status")?.addEventListener("change", applyFilters);
    document.getElementById("filter-category")?.addEventListener("change", applyFilters);
    document.getElementById("search-input")?.addEventListener("input", applyFilters);

    const submitForm = document.getElementById("claim-submit-form");
    if (submitForm) {
        submitForm.addEventListener("submit", handleClaimSubmit);
    }
}

/**
 * Handles claim form submission from modal dialog.
 */
async function handleClaimSubmit(e) {
    e.preventDefault();
    const alertBox = document.getElementById("submit-alert");
    const submitBtn = document.getElementById("btn-submit-claim");

    alertBox.style.display = "none";

    const catVal = parseInt(document.getElementById("claim-category").value, 10);
    const amountVal = parseFloat(document.getElementById("claim-amount").value);
    const dateVal = (document.getElementById("claim-date").value || "").trim();
    const descVal = (document.getElementById("claim-desc").value || "").trim();
    const fileInput = document.getElementById("claim-receipt");

    if (!catVal || isNaN(catVal)) {
        alertBox.textContent = "Please select an expense category.";
        alertBox.style.display = "block";
        return;
    }
    if (isNaN(amountVal) || amountVal <= 0) {
        alertBox.textContent = "Expense amount must be greater than 0.";
        alertBox.style.display = "block";
        return;
    }
    if (amountVal > 1000000) {
        alertBox.textContent = "Expense amount exceeds permissible limit ($1,000,000).";
        alertBox.style.display = "block";
        return;
    }
    const today = new Date().toISOString().split("T")[0];
    if (!dateVal || dateVal > today) {
        alertBox.textContent = "Expense date cannot be empty or in the future.";
        alertBox.style.display = "block";
        return;
    }
    if (descVal.length < 5) {
        alertBox.textContent = "Please provide an expense description (minimum 5 characters).";
        alertBox.style.display = "block";
        return;
    }

    let receiptFile = null;
    if (fileInput && fileInput.files && fileInput.files[0]) {
        receiptFile = fileInput.files[0];
        const ext = receiptFile.name.split(".").pop().toLowerCase();
        if (!["pdf", "png", "jpg", "jpeg"].includes(ext)) {
            alertBox.textContent = `Unsupported file format (${ext}). Allowed: PDF, PNG, JPG, JPEG.`;
            alertBox.style.display = "block";
            return;
        }
        if (receiptFile.size > 10 * 1024 * 1024) {
            alertBox.textContent = "Receipt file size exceeds 10MB limit.";
            alertBox.style.display = "block";
            return;
        }
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Analyzing & Submitting...";

    try {
        const payload = {
            category_id: catVal,
            amount: amountVal,
            expense_date: dateVal,
            description: descVal
        };

        const res = await API.post("/reimbursements", payload);
        if (!res.success) throw new Error(res.error || "Submission failed");

        const newClaimId = res.claim.id;

        if (receiptFile) {
            submitBtn.textContent = "Uploading Receipt...";
            await API.upload(`/reimbursements/${newClaimId}/upload`, receiptFile);
        }

        // Close modal and refresh dashboard
        closeModal("submit-modal");
        document.getElementById("claim-submit-form")?.reset();
        await loadAnalytics();
        await loadClaims();

        // Open claim details modal immediately so user inspects ML & AI results
        viewClaimDetails(newClaimId);
    } catch (err) {
        alertBox.textContent = err.message || "Failed to submit reimbursement claim.";
        alertBox.style.display = "block";
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit Claim";
    }
}

/**
 * Loads and renders the claim details modal view.
 */
window.viewClaimDetails = async function(claimId) {
    const modal = document.getElementById("details-modal");
    if (!modal) return;

    modal.classList.add("show");
    document.getElementById("details-loading").style.display = "block";
    document.getElementById("details-content").style.display = "none";

    try {
        const res = await API.get(`/reimbursements/${claimId}`);
        if (!res.success) throw new Error(res.error);

        const c = res.claim;
        document.getElementById("detail-id").textContent = `#${c.id}`;
        document.getElementById("detail-category").textContent = c.category_name;
        document.getElementById("detail-amount").textContent = ReimbursementUI.formatCurrency(c.amount);
        document.getElementById("detail-date").textContent = ReimbursementUI.formatDate(c.expense_date);
        document.getElementById("detail-status").innerHTML = ReimbursementUI.getStatusBadge(c.claim_status);
        document.getElementById("detail-desc").textContent = c.description;

        // Receipt document attachment box
        const receiptContainer = document.getElementById("detail-receipt-box");
        if (c.bill_available) {
            receiptContainer.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:space-between;background:#f8fafc;padding:12px 16px;border-radius:8px;border:1px solid #e2e8f0;">
                    <div><strong>${c.bill_original_name || "receipt"}</strong></div>
                    <button type="button" class="btn btn-sm btn-primary" onclick="viewReceipt('${c.id}')">View / Download</button>
                </div>
            `;
        } else {
            receiptContainer.innerHTML = `
                <div style="background:#fffbeb;padding:12px 16px;border-radius:8px;border:1px solid #fde68a;display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#b45309;font-size:13px;">No receipt attached. Attach one to decrease rejection risk.</span>
                    <input type="file" id="attach-later-input" style="display:none;" onchange="uploadReceiptToExisting('${c.id}', this)">
                    <button class="btn btn-sm btn-secondary" onclick="document.getElementById('attach-later-input').click()">Upload Receipt</button>
                </div>
            `;
        }

        // Random Forest Risk Assessment meter
        const mlContainer = document.getElementById("detail-ml-box");
        const confPercent = c.ml_confidence ? (c.ml_confidence * 100).toFixed(1) : "0";
        mlContainer.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <div>
                    <strong>Predicted Risk:</strong> ${ReimbursementUI.getRiskBadge(c.ml_prediction, c.ml_confidence)}
                </div>
                <div style="font-size:13px;color:var(--slate-500);">Confidence: <strong>${confPercent}%</strong></div>
            </div>
            <div class="ml-meter">
                <div class="ml-meter-fill" style="width:${confPercent}%; background:${c.ml_prediction === 'LIKELY_APPROVED' ? '#16a34a' : c.ml_prediction === 'REQUIRES_REVIEW' ? '#d97706' : '#dc2626'};"></div>
            </div>
            <p style="font-size:11px;color:var(--slate-400);margin-top:6px;">
                Advisory assessment produced by Random Forest Classifier trained on policy limits, receipt presence, and historical statistics.
            </p>
        `;

        // Generative AI Audit Insights
        document.getElementById("detail-ai-summary").textContent = c.ai_summary || "AI Summary not yet generated.";
        document.getElementById("detail-ai-obs").textContent = c.ai_observations || "No observations noted.";
        document.getElementById("detail-ai-missing").textContent = c.ai_missing_info || "None identified.";
        document.getElementById("detail-ai-actions").textContent = c.ai_suggested_actions || "Follow standard departmental review.";

        // Reviewer comments or rejection reason
        const reviewBox = document.getElementById("detail-reviewer-box");
        if (c.claim_status === "REJECTED" && c.rejection_reason) {
            reviewBox.style.display = "block";
            reviewBox.innerHTML = `
                <div class="alert alert-danger" style="margin-top:16px;">
                    <strong>Finance Rejection Reason:</strong> ${c.rejection_reason}
                </div>
            `;
        } else if (c.claim_status === "APPROVED" && c.reviewer_comments) {
            reviewBox.style.display = "block";
            reviewBox.innerHTML = `
                <div class="alert alert-success" style="margin-top:16px;">
                    <strong>Finance Review Comment:</strong> ${c.reviewer_comments}
                </div>
            `;
        } else {
            reviewBox.style.display = "none";
        }

        // Chronological audit trail
        ReimbursementUI.renderAuditTrail(res.audit_logs, document.getElementById("detail-audit-logs"));

        document.getElementById("details-loading").style.display = "none";
        document.getElementById("details-content").style.display = "block";
    } catch (err) {
        alert("Failed to load claim details: " + err.message);
        modal.classList.remove("show");
    }
};

/**
 * Uploads a receipt to an existing pending claim that lacked one.
 */
window.uploadReceiptToExisting = async function(claimId, inputEl) {
    if (!inputEl.files || !inputEl.files[0]) return;
    try {
        await API.upload(`/reimbursements/${claimId}/upload`, inputEl.files[0]);
        await loadClaims();
        await loadAnalytics();
        viewClaimDetails(claimId);
    } catch (err) {
        alert("Failed to upload receipt: " + err.message);
    }
};

/**
 * Opens modal by ID.
 */
window.openSubmitModal = function() {
    const modal = document.getElementById("submit-modal");
    if (modal) modal.classList.add("show");
};

/**
 * Closes modal by ID.
 */
window.closeModal = function(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("show");
};
