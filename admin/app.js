(function () {
    "use strict";

    const isLocal = window.location.protocol === "file:" ||
        !window.location.hostname ||
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";
    const API_BASE = isLocal ? "http://127.0.0.1:8000" : "";

    const PAGE_SIZE = 20;
    let currentSkip = 0;
    let lastOrdersTotal = 0;

    const loginScreen = document.getElementById("loginScreen");
    const dashboardScreen = document.getElementById("dashboardScreen");
    const loginForm = document.getElementById("loginForm");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const loginError = document.getElementById("loginError");
    const loginBtn = document.getElementById("loginBtn");
    const logoutBtn = document.getElementById("logoutBtn");
    const statsGrid = document.getElementById("statsGrid");
    const ordersBody = document.getElementById("ordersBody");
    const ordersLoading = document.getElementById("ordersLoading");
    const ordersError = document.getElementById("ordersError");
    const exportCsvBtn = document.getElementById("exportCsvBtn");
    const refreshBtn = document.getElementById("refreshBtn");
    const applyFiltersBtn = document.getElementById("applyFiltersBtn");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const paginationInfo = document.getElementById("paginationInfo");
    const bundlesBody = document.getElementById("bundlesBody");
    const bundlesLoading = document.getElementById("bundlesLoading");
    const bundlesError = document.getElementById("bundlesError");
    const bundleModal = document.getElementById("bundleModal");
    const bundleForm = document.getElementById("bundleForm");
    const bundleIdInput = document.getElementById("bundleId");
    const bundleNetworkSelect = document.getElementById("bundleNetwork");
    const bundleCapacityInput = document.getElementById("bundleCapacity");
    const bundleCostInput = document.getElementById("bundleCost");
    const bundleSellingInput = document.getElementById("bundleSelling");
    const bundleActiveCheckbox = document.getElementById("bundleActive");
    const bundleFormError = document.getElementById("bundleFormError");
    const bundleModalTitle = document.getElementById("bundleModalTitle");

    const TOKEN_KEY = "adminToken";

    function getAuthHeader() {
        const token = sessionStorage.getItem(TOKEN_KEY);
        return token ? "Bearer " + token : null;
    }

    function setAuthToken(token) {
        sessionStorage.setItem(TOKEN_KEY, token);
    }

    function clearAuth() {
        sessionStorage.removeItem(TOKEN_KEY);
    }

    function showLogin() {
        if (dashboardScreen) dashboardScreen.hidden = true;
        if (loginScreen) loginScreen.hidden = false;
        if (loginError) loginError.hidden = true;
    }

    function showDashboard() {
        if (loginScreen) loginScreen.hidden = true;
        if (dashboardScreen) dashboardScreen.hidden = false;
    }

    async function api(path, options = {}) {
        const auth = getAuthHeader();
        if (!auth) {
            return { ok: false, status: 401 };
        }
        const res = await fetch(API_BASE + path, {
            ...options,
            headers: {
                Authorization: auth,
                "Content-Type": "application/json",
                ...options.headers,
            },
        });
        if (res.status === 401) {
            clearAuth();
            showLogin();
            return { ok: false, status: 401 };
        }
        const data = await res.json().catch(() => ({}));
        return { ok: res.ok, status: res.status, data };
    }

    function formatDate(iso) {
        if (!iso) return "—";
        try {
            const d = new Date(iso);
            return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
        } catch {
            return iso;
        }
    }

    function formatCapacity(mb) {
        if (mb == null) return "—";
        if (mb >= 1000) return (mb / 1000) + " GB";
        return mb + " MB";
    }

    function badgeClass(status) {
        if (status === "completed") return "badge-completed";
        if (status === "failed") return "badge-failed";
        return "badge-pending";
    }

    async function loadStats() {
        const from = document.getElementById("filterFrom").value || undefined;
        const to = document.getElementById("filterTo").value || undefined;
        let path = "/admin/stats";
        if (from || to) {
            const params = new URLSearchParams();
            if (from) params.set("from_date", from);
            if (to) params.set("to_date", to);
            path += "?" + params.toString();
        }
        const { ok, data } = await api(path);
        if (!ok || !data) return;
        document.getElementById("statTotalOrders").textContent = data.total_orders ?? "—";
        document.getElementById("statRevenue").textContent = data.total_revenue_ghs != null ? "₵" + data.total_revenue_ghs : "—";
        document.getElementById("statCompleted").textContent = data.completed_orders ?? "—";
        document.getElementById("statFailed").textContent = data.failed_orders ?? "—";
        document.getElementById("statPending").textContent = data.pending_orders ?? "—";
    }

    async function loadOrders() {
        ordersLoading.hidden = false;
        ordersError.hidden = true;
        const from = document.getElementById("filterFrom").value || undefined;
        const to = document.getElementById("filterTo").value || undefined;
        const status = document.getElementById("filterStatus").value || undefined;
        const payment = document.getElementById("filterPayment").value || undefined;
        const params = new URLSearchParams();
        params.set("skip", String(currentSkip));
        params.set("limit", String(PAGE_SIZE));
        if (from) params.set("from_date", from);
        if (to) params.set("to_date", to);
        if (status) params.set("status", status);
        if (payment) params.set("payment_status", payment);

        const { ok, data, status: resStatus } = await api("/admin/orders?" + params.toString());
        ordersLoading.hidden = true;
        if (resStatus === 401) return;
        if (!ok || !data) {
            ordersError.textContent = "Failed to load orders.";
            ordersError.hidden = false;
            return;
        }

        lastOrdersTotal = data.total ?? 0;
        const items = data.items ?? [];
        ordersBody.innerHTML = items
            .map(
                (o) =>
                    `<tr>
        <td data-label="Reference"><code>${escapeHtml(o.reference || "—")}</code></td>
        <td data-label="Network">${escapeHtml(o.network || "—")}</td>
        <td data-label="Size">${formatCapacity(o.capacity)}</td>
        <td data-label="Price">${o.price != null ? "₵" + Number(o.price).toFixed(2) : "—"}</td>
        <td data-label="Status"><span class="badge ${badgeClass(o.status)}">${escapeHtml(o.status || "—")}</span></td>
        <td data-label="Payment"><span class="badge ${badgeClass(o.payment_status)}">${escapeHtml(o.payment_status || "—")}</span></td>
        <td data-label="Date">${formatDate(o.created_at)}</td>
      </tr>`
            )
            .join("");

        const fromRow = currentSkip + 1;
        const toRow = Math.min(currentSkip + items.length, lastOrdersTotal);
        paginationInfo.textContent =
            lastOrdersTotal === 0
                ? "No orders"
                : `Showing ${fromRow}–${toRow} of ${lastOrdersTotal}`;
        prevBtn.disabled = currentSkip === 0;
        nextBtn.disabled = currentSkip + items.length >= lastOrdersTotal;
    }

    function escapeHtml(s) {
        const div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }

    function exportCsv() {
        const from = document.getElementById("filterFrom").value || undefined;
        const to = document.getElementById("filterTo").value || undefined;
        const status = document.getElementById("filterStatus").value || undefined;
        const payment = document.getElementById("filterPayment").value || undefined;
        const params = new URLSearchParams();
        params.set("limit", "5000");
        if (from) params.set("from_date", from);
        if (to) params.set("to_date", to);
        if (status) params.set("status", status);
        if (payment) params.set("payment_status", payment);

        api("/admin/orders?" + params.toString()).then(({ ok, data }) => {
            if (!ok || !data || !data.items) return;
            const rows = data.items;
            const headers = ["reference", "network", "capacity", "price", "status", "payment_status", "created_at", "phone_number"];
            const line = (arr) => arr.map((c) => (c == null ? "" : '"' + String(c).replace(/"/g, '""') + '"')).join(",");
            const csv = [line(headers)].concat(rows.map((o) => line([o.reference, o.network, o.capacity, o.price, o.status, o.payment_status, o.created_at, o.phone_number]))).join("\r\n");
            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "orders-" + new Date().toISOString().slice(0, 10) + ".csv";
            a.click();
            URL.revokeObjectURL(a.href);
        });
    }

    function applyFilters() {
        currentSkip = 0;
        loadOrders();
        loadStats();
    }

    // ----- Tabs -----
    function initTabs() {
        const tabs = document.querySelectorAll(".tab");
        const panels = document.querySelectorAll(".tab-panel");
        tabs.forEach((tab) => {
            tab.addEventListener("click", () => {
                const target = tab.getAttribute("data-tab");
                tabs.forEach((t) => {
                    t.classList.toggle("active", t.getAttribute("data-tab") === target);
                    t.setAttribute("aria-selected", t.getAttribute("data-tab") === target ? "true" : "false");
                });
                panels.forEach((p) => {
                    const isOrders = p.id === "panelOrders";
                    p.hidden = (target === "orders" && !isOrders) || (target === "bundles" && isOrders);
                });
                if (target === "bundles") loadBundles();
            });
        });
    }

    // ----- Bundles -----
    async function loadBundles() {
        bundlesLoading.hidden = false;
        bundlesError.hidden = true;
        const { ok, data, status: resStatus } = await api("/admin/bundles?include_inactive=true");
        bundlesLoading.hidden = true;
        if (resStatus === 401) return;
        if (!ok || !data) {
            bundlesError.textContent = "Failed to load bundles.";
            bundlesError.hidden = false;
            return;
        }
        const items = data.items || [];
        bundlesBody.innerHTML = items
            .map(
                (b) =>
                    `<tr>
                        <td data-label="Network">${escapeHtml(b.network)}</td>
                        <td data-label="Size">${formatCapacity(b.capacity_mb)}</td>
                        <td data-label="Cost">₵${Number(b.cost_price_ghs).toFixed(2)}</td>
                        <td data-label="Selling">₵${Number(b.selling_price_ghs).toFixed(2)}</td>
                        <td data-label="Active">${b.is_active ? "Yes" : "No"}</td>
                        <td data-label="Actions">
                            <button type="button" class="btn btn-small btn-edit" data-id="${b.id}" data-network="${escapeHtml(b.network)}" data-capacity="${b.capacity_mb}" data-cost="${b.cost_price_ghs}" data-selling="${b.selling_price_ghs}" data-active="${b.is_active}">Edit</button>
                            <button type="button" class="btn btn-small btn-danger" data-id="${b.id}">Delete</button>
                        </td>
                    </tr>`
            )
            .join("");

        bundlesBody.querySelectorAll(".btn-edit").forEach((btn) => {
            btn.addEventListener("click", () => {
                openBundleModal({
                    id: Number(btn.getAttribute("data-id")),
                    network: btn.getAttribute("data-network"),
                    capacity_mb: Number(btn.getAttribute("data-capacity")),
                    cost_price_ghs: parseFloat(btn.getAttribute("data-cost")),
                    selling_price_ghs: parseFloat(btn.getAttribute("data-selling")),
                    is_active: btn.getAttribute("data-active") === "true",
                });
            });
        });
        bundlesBody.querySelectorAll(".btn-danger").forEach((btn) => {
            btn.addEventListener("click", () => deleteBundle(Number(btn.getAttribute("data-id"))));
        });
    }

    function openBundleModal(bundle) {
        if (!bundleModal) return;
        if (bundleFormError) bundleFormError.hidden = true;
        if (bundle) {
            if (bundleModalTitle) bundleModalTitle.textContent = "Edit bundle";
            if (bundleIdInput) bundleIdInput.value = bundle.id;
            if (bundleNetworkSelect) { bundleNetworkSelect.value = bundle.network; bundleNetworkSelect.disabled = true; }
            if (bundleCapacityInput) { bundleCapacityInput.value = bundle.capacity_mb; bundleCapacityInput.disabled = true; }
            if (bundleCostInput) bundleCostInput.value = bundle.cost_price_ghs;
            if (bundleSellingInput) bundleSellingInput.value = bundle.selling_price_ghs;
            if (bundleActiveCheckbox) bundleActiveCheckbox.checked = bundle.is_active;
        } else {
            if (bundleModalTitle) bundleModalTitle.textContent = "Add bundle";
            if (bundleIdInput) bundleIdInput.value = "";
            if (bundleForm) bundleForm.reset();
            if (bundleActiveCheckbox) bundleActiveCheckbox.checked = true;
            if (bundleNetworkSelect) bundleNetworkSelect.disabled = false;
            if (bundleCapacityInput) bundleCapacityInput.disabled = false;
        }
        if (typeof bundleModal.showModal === "function") bundleModal.showModal();
        else bundleModal.setAttribute("open", "");
    }

    function closeBundleModal() {
        if (!bundleModal) return;
        if (typeof bundleModal.close === "function") bundleModal.close();
        else bundleModal.removeAttribute("open");
    }

    async function saveBundle(payload) {
        const id = bundleIdInput.value.trim();
        const { ok, data, status: resStatus } = id
            ? await api("/admin/bundles/" + id, { method: "PUT", body: JSON.stringify(payload) })
            : await api("/admin/bundles", { method: "POST", body: JSON.stringify(payload) });
        if (resStatus === 401) return;
        if (!ok) return data;
        return null;
    }

    async function deleteBundle(id) {
        if (!confirm("Delete this bundle? Customers will no longer see it.")) return;
        const { ok, status: resStatus } = await api("/admin/bundles/" + id, { method: "DELETE" });
        if (resStatus === 401) return;
        if (ok) loadBundles();
    }

    if (bundleForm) bundleForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (bundleFormError) bundleFormError.hidden = true;
        const id = bundleIdInput ? bundleIdInput.value.trim() : "";
        let payload;
        if (id) {
            payload = {
                cost_price_ghs: parseFloat(bundleCostInput.value),
                selling_price_ghs: parseFloat(bundleSellingInput.value),
                is_active: bundleActiveCheckbox.checked,
            };
        } else {
            payload = {
                network: bundleNetworkSelect.value.trim(),
                capacity_mb: parseInt(bundleCapacityInput.value, 10),
                cost_price_ghs: parseFloat(bundleCostInput.value),
                selling_price_ghs: parseFloat(bundleSellingInput.value),
                is_active: bundleActiveCheckbox.checked,
            };
        }
        const err = await saveBundle(payload);
        if (err) {
            bundleFormError.textContent = err.detail || "Save failed.";
            bundleFormError.hidden = false;
            return;
        }
        closeBundleModal();
        loadBundles();
    });

    document.getElementById("bundleModalCancel").addEventListener("click", closeBundleModal);
    bundleModal.addEventListener("cancel", closeBundleModal);

    document.getElementById("addBundleBtn").addEventListener("click", () => openBundleModal(null));
    document.getElementById("refreshBundlesBtn").addEventListener("click", loadBundles);

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = usernameInput.value.trim();
        const password = passwordInput.value;
        if (!username || !password) return;
        loginError.hidden = true;
        loginBtn.disabled = true;
        try {
            const res = await fetch(API_BASE + "/admin/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            const data = await res.json().catch(() => ({}));
            if (res.status === 401) {
                loginError.textContent = data.detail || "Invalid username or password.";
                loginError.hidden = false;
                return;
            }
            if (!res.ok || !data.token) {
                loginError.textContent = data.detail || "Could not connect. Check the API URL and try again.";
                loginError.hidden = false;
                return;
            }
            setAuthToken(data.token);
            showDashboard();
            loadStats();
            loadOrders();
        } finally {
            loginBtn.disabled = false;
        }
    });

    logoutBtn.addEventListener("click", () => {
        clearAuth();
        showLogin();
    });

    refreshBtn.addEventListener("click", () => {
        loadStats();
        loadOrders();
    });

    exportCsvBtn.addEventListener("click", exportCsv);
    applyFiltersBtn.addEventListener("click", applyFilters);
    prevBtn.addEventListener("click", () => {
        currentSkip = Math.max(0, currentSkip - PAGE_SIZE);
        loadOrders();
    });
    nextBtn.addEventListener("click", () => {
        currentSkip += PAGE_SIZE;
        loadOrders();
    });

    if (loginScreen && dashboardScreen) {
        if (getAuthHeader()) {
            showDashboard();
            if (typeof initTabs === "function") initTabs();
            loadStats();
            loadOrders();
        } else {
            showLogin();
        }
    }
})();
