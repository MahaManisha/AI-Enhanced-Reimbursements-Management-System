/**
 * Reimbursement UI Helpers & Receipt Viewer
 * AI-Enhanced Reimbursements Management System
 * 
 * Provides shared formatters, status/risk badges, audit trail renderers,
 * and an authenticated receipt document viewer for PDFs and images.
 */

const ReimbursementUI = {
    /**
     * Formats numeric amounts to standard USD currency strings ($1,234.56).
     */
    formatCurrency(amount) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD"
        }).format(amount || 0);
    },

    /**
     * Formats an ISO date string to a localized human-readable date (e.g. Nov 5, 2026).
     */
    formatDate(dateStr) {
        if (!dateStr) return "-";
        const d = new Date(dateStr);
        return d.toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric"
        });
    },

    /**
     * Generates a semantic status badge for PENDING, APPROVED, or REJECTED.
     */
    getStatusBadge(status) {
        const s = (status || "PENDING").toUpperCase();
        switch (s) {
            case "APPROVED":
                return `<span class="badge badge-approved">Approved</span>`;
            case "REJECTED":
                return `<span class="badge badge-rejected">Rejected</span>`;
            case "PENDING":
            default:
                return `<span class="badge badge-pending">Awaiting Review</span>`;
        }
    },

    /**
     * Generates an advisory risk badge reflecting Random Forest classification.
     */
    getRiskBadge(risk, confidence) {
        const r = (risk || "UNPREDICTED").toUpperCase();
        const confText = confidence ? ` (${(confidence * 100).toFixed(0)}%)` : "";

        switch (r) {
            case "LIKELY_APPROVED":
                return `<span class="badge badge-risk-low" title="Random Forest: High historical approval likelihood">Low Risk${confText}</span>`;
            case "REQUIRES_REVIEW":
                return `<span class="badge badge-risk-medium" title="Random Forest: Requires finance officer inspection">Review Recommended${confText}</span>`;
            case "HIGH_REJECTION_RISK":
                return `<span class="badge badge-risk-high" title="Random Forest: Statistical policy or receipt variance">High Risk${confText}</span>`;
            default:
                return `<span class="badge" style="background:#f1f5f9;color:#64748b;">Not Evaluated</span>`;
        }
    },

    /**
     * Renders chronological audit log items inside a container element.
     */
    renderAuditTrail(logs, containerEl) {
        if (!containerEl) return;
        if (!logs || logs.length === 0) {
            containerEl.innerHTML = `<p style="color:var(--slate-400);font-size:13px;">No audit records available.</p>`;
            return;
        }

        containerEl.innerHTML = logs.map(l => `
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <div class="timeline-time">${new Date(l.created_at).toLocaleString()}</div>
                    <div class="timeline-actor">${l.actor_name} (${l.actor_role}) &bull; <strong style="color:var(--primary);">${l.action}</strong></div>
                    <div class="timeline-desc">${l.comments || "No comments entered."}</div>
                </div>
            </div>
        `).join("");
    },

    /**
     * Securely loads and renders an uploaded receipt document:
     * 1. Opens a blank new tab immediately to prevent popup blocker suppression.
     * 2. Calls API.getBlob() passing the JWT Bearer token in headers.
     * 3. Creates a local object URL (URL.createObjectURL).
     * 4. Renders PDFs within an inline iframe and images within an aligned container.
     * 5. Automatically revokes the object URL when closed to prevent memory leaks.
     */
    async viewReceipt(claimId) {
        if (!claimId) {
            alert("No claim reference specified.");
            return;
        }

        const token = API.getToken();
        if (!token) {
            alert("Authentication token is missing. Please log in again.");
            window.location.href = "/login.html";
            return;
        }

        // Open blank tab synchronously to satisfy browser popup security policies
        const newTab = window.open("about:blank", "_blank");
        if (newTab) {
            try {
                newTab.document.title = "Loading Receipt...";
                newTab.document.body.style.margin = "0";
                newTab.document.body.style.display = "flex";
                newTab.document.body.style.alignItems = "center";
                newTab.document.body.style.justifyContent = "center";
                newTab.document.body.style.height = "100vh";
                newTab.document.body.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
                newTab.document.body.style.color = "#64748b";
                newTab.document.body.style.backgroundColor = "#f8fafc";
                newTab.document.body.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 16px; font-weight: 600; color: #1e293b; margin-bottom: 6px;">Loading Receipt Document</div>
                        <div style="font-size: 13px; color: #64748b;">Retrieving securely from server...</div>
                    </div>
                `;
            } catch (e) {
                // Ignore cross-origin context warnings
            }
        }

        try {
            const { blob, contentType } = await API.getBlob(`/reimbursements/${claimId}/bill`);
            if (!blob || blob.size === 0) {
                throw new Error("The receipt file is empty.");
            }

            const objectUrl = URL.createObjectURL(blob);

            if (newTab) {
                if (contentType === "application/pdf") {
                    newTab.document.title = `Receipt Claim #${claimId} (PDF)`;
                    newTab.document.body.style.margin = "0";
                    newTab.document.body.style.overflow = "hidden";
                    newTab.document.body.style.backgroundColor = "#525659";
                    newTab.document.body.innerHTML = `
                        <iframe src="${objectUrl}" style="border:none;width:100vw;height:100vh;position:fixed;top:0;left:0;" type="application/pdf" title="Receipt Document"></iframe>
                    `;
                } else if (contentType.startsWith("image/")) {
                    newTab.document.title = `Receipt Claim #${claimId}`;
                    newTab.document.body.style.margin = "0";
                    newTab.document.body.style.backgroundColor = "#0f172a";
                    newTab.document.body.style.display = "flex";
                    newTab.document.body.style.alignItems = "center";
                    newTab.document.body.style.justifyContent = "center";
                    newTab.document.body.style.minHeight = "100vh";
                    newTab.document.body.innerHTML = `
                        <img src="${objectUrl}" style="max-width:100%;max-height:100vh;object-fit:contain;box-shadow:0 10px 25px rgba(0,0,0,0.5);margin:auto;display:block;" alt="Receipt Claim #${claimId}">
                    `;
                } else {
                    newTab.location.replace(objectUrl);
                }

                newTab.addEventListener("unload", () => {
                    setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
                });
                setTimeout(() => {
                    URL.revokeObjectURL(objectUrl);
                }, 10 * 60 * 1000);
            } else {
                // Fallback if popup was blocked by browser
                const a = document.createElement("a");
                a.href = objectUrl;
                a.target = "_blank";
                a.rel = "noopener noreferrer";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(() => URL.revokeObjectURL(objectUrl), 60 * 1000);
            }
        } catch (err) {
            console.error("Receipt view error:", err);
            const errMsg = err.message || "Failed to load receipt file.";
            if (newTab) {
                newTab.document.title = "Receipt Error";
                newTab.document.body.style.backgroundColor = "#ffffff";
                newTab.document.body.innerHTML = `
                    <div style="text-align: center; padding: 40px 24px; max-width: 480px; margin: auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <div style="font-size: 18px; font-weight: 700; color: #dc2626; margin-bottom: 8px;">Unable to Display Receipt</div>
                        <p style="font-size: 14px; color: #475569; line-height: 1.5; margin-bottom: 20px;">${errMsg.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</p>
                        <button onclick="window.close()" style="padding: 8px 18px; background: #64748b; color: #ffffff; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;">Close Window</button>
                    </div>
                `;
            } else {
                alert("Unable to open receipt: " + errMsg);
            }
        }
    }
};

window.ReimbursementUI = ReimbursementUI;
window.viewReceipt = ReimbursementUI.viewReceipt.bind(ReimbursementUI);
