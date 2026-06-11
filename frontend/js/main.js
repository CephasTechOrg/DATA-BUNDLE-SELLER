import { getBundles, createOrder, getOrderStatus } from "./api.js";

const loadingScreen = document.getElementById("loadingScreen");
const bundlesGrid = document.getElementById("bundlesGrid");
const bundleLoading = document.getElementById("bundleLoading");
const bundleError = document.getElementById("bundleError");
const orderModal = document.getElementById("orderModal");
const orderModalBackdrop = document.getElementById("orderModalBackdrop");
const orderModalClose = document.getElementById("orderModalClose");
const orderForm = document.getElementById("orderForm");
const orderFormError = document.getElementById("orderFormError");
const orderSubmitBtn = document.getElementById("orderSubmitBtn");
const bundleSummary = document.getElementById("bundleSummary");
const processingModal = document.getElementById("processingModal");
const statusModal = document.getElementById("statusModal");
const statusContent = document.getElementById("statusContent");
const statusModalClose = document.getElementById("statusModalClose");
const statusModalBackdrop = document.getElementById("statusModalBackdrop");

let allNetworks = [];
let selectedNetwork = "MTN";
let selectedBundle = null;

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatCapacityDisplay(capacityMb) {
    const n = Number(capacityMb);
    if (!Number.isFinite(n) || n <= 0) return `${capacityMb} MB`;
    if (n >= 1000) {
        const gb = n / 1000;
        return gb % 1 === 0 ? `${gb} GB` : `${gb.toFixed(1)} GB`;
    }
    return `${n} MB`;
}

function scrollToBundles() {
    document.getElementById("bundles").scrollIntoView({ behavior: "smooth" });
}

function showToast(message, isError = true) {
    const existing = document.querySelector(".error-toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.className = "error-toast";
    toast.setAttribute("role", "alert");
    const bg = isError ? "#ef4444" : "#0d9488";       // red for errors, teal for info
    const shadow = isError ? "rgba(239,68,68,0.3)" : "rgba(13,148,136,0.3)";
    const icon = isError ? "fa-exclamation-circle" : "fa-info-circle";
    toast.style.cssText = `position:fixed;top:20px;right:20px;background:${bg};color:#fff;padding:1rem 1.5rem;border-radius:12px;box-shadow:0 10px 25px ${shadow};z-index:10000;max-width:400px;`;
    toast.innerHTML = `<div style="display:flex;align-items:flex-start;gap:0.75rem;"><i class="fas ${icon}" style="font-size:1.2rem;"></i><div>${escapeHtml(message)}</div></div>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), isError ? 5000 : 8000);
}

function showLoadingScreen() {
    if (loadingScreen) loadingScreen.style.display = "flex";
}

function hideLoadingScreen() {
    if (loadingScreen) {
        loadingScreen.classList.add("fade-out");
        setTimeout(() => {
            loadingScreen.style.display = "none";
            loadingScreen.classList.remove("fade-out");
        }, 500);
    }
}

function setModalVisible(modal, visible) {
    if (!modal) return;
    if (visible) modal.removeAttribute("hidden");
    else modal.setAttribute("hidden", "");
}

async function loadBundles() {
    const loadingMessage = document.getElementById("loadingScreenMessage");
    const defaultMessage = "Preparing your data experience...";
    const wakingMessage = "Waking up server, please wait…";

    if (bundleLoading) bundleLoading.hidden = false;
    if (bundleError) { bundleError.hidden = true; bundleError.textContent = ""; }
    try {
        const data = await getBundles(() => {
            if (loadingMessage) loadingMessage.textContent = wakingMessage;
            if (bundleLoading) bundleLoading.textContent = wakingMessage;
        });
        if (loadingMessage) loadingMessage.textContent = defaultMessage;
        allNetworks = Array.isArray(data) ? data : [];
        renderBundlesForNetwork(selectedNetwork);
    } catch (err) {
        if (loadingMessage) loadingMessage.textContent = defaultMessage;
        const msg = err.message || "Failed to load bundles.";
        if (bundleError) { bundleError.textContent = msg; bundleError.hidden = false; }
        if (bundlesGrid) bundlesGrid.innerHTML = "";
    } finally {
        if (bundleLoading) bundleLoading.hidden = true;
    }
}

function getBundlesForNetwork(networkKey) {
    const net = allNetworks.find((n) => (n.key || n.name) === networkKey);
    return net && Array.isArray(net.bundles) ? net.bundles : [];
}

function renderBundlesForNetwork(networkKey) {
    const bundles = getBundlesForNetwork(networkKey);
    if (!bundles.length) {
        bundlesGrid.innerHTML = `
            <div class="no-bundles" style="grid-column:1/-1;text-align:center;padding:2rem;">
                <p style="color:var(--text-light);">No bundles for ${escapeHtml(networkKey)} yet. Check back later.</p>
            </div>`;
        return;
    }
    const variant =
        networkKey === "Telecel" ? "bundle-card--telecel"
        : networkKey === "AirtelTigo" ? "bundle-card--airteltigo"
        : "bundle-card--mtn";
    const cardClass = `bundle-card ${variant}`;
    bundlesGrid.innerHTML = bundles
        .map((b) => {
            const price = Number(b.price);
            const displayPrice = Number.isFinite(price) ? price.toFixed(2) : "—";
            const sizeLabel = formatCapacityDisplay(b.capacity);
            return `
        <div class="${cardClass}" role="button" tabindex="0" data-network="${escapeHtml(networkKey)}" data-capacity="${b.capacity}" data-price="${displayPrice}" data-size="${escapeHtml(sizeLabel)}" aria-label="Buy ${escapeHtml(sizeLabel)} for ₵${displayPrice}">
            <div class="bundle-card-top">
                <div class="bundle-network-pill">${escapeHtml(networkKey)}</div>
                <div class="bundle-more-icon"><i class="fas fa-angle-right"></i></div>
            </div>
            <div class="bundle-size">${sizeLabel}</div>
            <div class="bundle-name">${escapeHtml(networkKey)} Data Bundle</div>
            <div class="bundle-card-bottom">
                <div class="bundle-price">₵${displayPrice}</div>
                <div class="bundle-non-expiry">No Expiry</div>
            </div>
            <div class="bundle-card-strip"></div>
        </div>`;
        })
        .join("");

    bundlesGrid.querySelectorAll(".bundle-card").forEach((card) => {
        card.addEventListener("click", () => openOrderModal(card));
        card.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openOrderModal(card);
            }
        });
    });
}

function openOrderModal(card) {
    const network = card.getAttribute("data-network");
    const capacity = parseInt(card.getAttribute("data-capacity"), 10);
    const price = card.getAttribute("data-price");
    const sizeLabel = card.getAttribute("data-size");
    selectedBundle = { network, capacity, price, sizeLabel };
    if (bundleSummary) {
        bundleSummary.innerHTML = `
            <div><strong>Network:</strong> ${escapeHtml(network)}</div>
            <div><strong>Size:</strong> ${escapeHtml(sizeLabel)}</div>
            <div><strong>Price:</strong> ₵${escapeHtml(price)}</div>`;
    }
    if (orderFormError) { orderFormError.hidden = true; orderFormError.textContent = ""; }
    if (orderForm) orderForm.reset();
    const sameCheck = document.getElementById("sameAsRecipient");
    if (sameCheck) sameCheck.checked = false;
    setModalVisible(orderModal, true);
}

function closeOrderModal() {
    setModalVisible(orderModal, false);
    selectedBundle = null;
}

function copyRecipientToPayer() {
    const recipient = document.getElementById("recipientPhone");
    const payer = document.getElementById("payerPhone");
    const same = document.getElementById("sameAsRecipient");
    if (same && same.checked && recipient) payer.value = recipient.value;
}

async function handleOrderSubmit(e) {
    e.preventDefault();
    const bundle = selectedBundle;
    if (!bundle) return;
    const recipientPhone = (document.getElementById("recipientPhone")?.value ?? "").trim();
    const payerPhone = (document.getElementById("payerPhone")?.value ?? "").trim();
    const email = (document.getElementById("customerEmail")?.value ?? "").trim();
    if (!recipientPhone || !email) {
        if (orderFormError) { orderFormError.textContent = "Please enter phone to receive bundle and email."; orderFormError.hidden = false; }
        return;
    }
    const sameAsRecipient = document.getElementById("sameAsRecipient");
    const paymentRefPhone = sameAsRecipient?.checked ? recipientPhone : (payerPhone || null);
    if (orderFormError) orderFormError.hidden = true;
    orderSubmitBtn.disabled = true;
    orderSubmitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Please wait…';
    closeOrderModal();
    setModalVisible(processingModal, true);
    try {
        const order = await createOrder(
            bundle.network,
            bundle.capacity,
            recipientPhone,
            email,
            paymentRefPhone
        );
        setModalVisible(processingModal, false);
        if (order.payment_url) {
            try {
                if (typeof window.PaystackPop !== "undefined" && order.access_code) {
                    const popup = new window.PaystackPop();
                    popup.resumeTransaction(order.access_code, {
                        onSuccess: () => showStatusFromReference(order.reference),
                        onCancel: () => showToast("Payment cancelled."),
                    });
                } else {
                    window.location.href = order.payment_url;
                }
            } catch (popupErr) {
                window.location.href = order.payment_url;
            }
        } else {
            const msg = order.message || order.detail || "Could not start payment.";
            showToast(msg);
            setModalVisible(orderModal, true);
        }
    } catch (err) {
        setModalVisible(processingModal, false);
        // 503 = service temporarily unavailable (e.g. provider wallet low) -> calm info, not an error.
        const isInfo = err.status === 503;
        showToast(err.message || "Something went wrong. Please try again.", !isInfo);
        setModalVisible(orderModal, true);
    } finally {
        orderSubmitBtn.disabled = false;
        orderSubmitBtn.innerHTML = '<i class="fas fa-credit-card"></i><span>Proceed to Pay</span>';
    }
}

// Map raw order state to a friendly label + style. Delivery is async, so a paid
// order that is not yet final shows the delivery ETA.
function describeStatus(data) {
    const s = (data.status || "").toLowerCase();
    const pay = (data.payment_status || "").toLowerCase();
    if (s === "completed") return { label: "Delivered", cls: "ok", icon: "fa-circle-check", note: "Your bundle has been delivered. Enjoy! 🎉" };
    if (s === "failed") return { label: "Failed", cls: "err", icon: "fa-circle-xmark", note: "Something went wrong with this order. Please contact support with your reference." };
    if (s === "manual_review") return { label: "Being processed", cls: "wait", icon: "fa-clock", note: "Your order is being processed and will be delivered shortly." };
    if (s === "processing") return { label: "Delivering now", cls: "wait", icon: "fa-bolt", note: "Usually delivered within 30 minutes (up to 1 hour during busy periods)." };
    if (pay === "completed") return { label: "Payment received", cls: "wait", icon: "fa-clock", note: "Usually delivered within 30 minutes (up to 1 hour during busy periods)." };
    return { label: "Awaiting payment", cls: "wait", icon: "fa-hourglass-half", note: "We haven't confirmed payment for this order yet." };
}

function renderOrderStatus(data) {
    if (data.error) return `<p class="error-inline">${escapeHtml(data.error)}</p>`;
    const d = describeStatus(data);
    const ref = data.reference || "";
    const refBlock = ref
        ? `<div class="status-ref">
                <span>Your reference — save it to track your order</span>
                <div class="ref-row">
                    <code>${escapeHtml(ref)}</code>
                    <button type="button" class="copy-ref-btn" data-ref="${escapeHtml(ref)}"><i class="fas fa-copy"></i> Copy</button>
                </div>
           </div>`
        : "";
    return `
        <div class="status-badge status-${d.cls}"><i class="fas ${d.icon}"></i> ${d.label}</div>
        <p class="status-note">${escapeHtml(d.note)}</p>
        ${refBlock}
        <div class="status-meta">
            <div><span>Payment</span><strong>${escapeHtml(data.payment_status || "—")}</strong></div>
        </div>`;
}

function showStatusFromReference(reference) {
    setModalVisible(statusModal, true);
    const titleEl = document.getElementById("statusModalTitle");
    if (titleEl) titleEl.textContent = "Payment Successful";
    if (statusContent) statusContent.innerHTML = "<p>Confirming your order…</p>";
    getOrderStatus(reference, true)
        .then((data) => {
            if (!statusContent) return;
            statusContent.innerHTML = renderOrderStatus(data);
        })
        .catch((err) => {
            if (statusContent) statusContent.innerHTML = `<p class="error-inline">${escapeHtml(err.message || "Could not load status.")}</p>`;
        });
}

async function handleTrackSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("trackRef");
    const out = document.getElementById("trackResult");
    const ref = (input?.value ?? "").trim();
    if (!out) return;
    if (!ref) {
        out.hidden = false;
        out.innerHTML = `<p class="error-inline">Please enter your order reference.</p>`;
        return;
    }
    out.hidden = false;
    out.innerHTML = "<p>Checking…</p>";
    try {
        const data = await getOrderStatus(ref, true);
        out.innerHTML = renderOrderStatus(data);
    } catch (err) {
        out.innerHTML = `<p class="error-inline">${escapeHtml(err.message || "Could not load status.")}</p>`;
    }
}

function closeStatusModal() {
    setModalVisible(statusModal, false);
    const params = new URLSearchParams(window.location.search);
    if (params.has("reference")) window.history.replaceState({}, document.title, window.location.pathname);
}

function initNetworkTabs() {
    document.querySelectorAll(".network-tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            const network = tab.getAttribute("data-network");
            if (!network) return;
            selectedNetwork = network;
            document.querySelectorAll(".network-tab").forEach((t) => {
                t.classList.remove("active");
                t.setAttribute("aria-selected", t.getAttribute("data-network") === network ? "true" : "false");
            });
            tab.classList.add("active");
            renderBundlesForNetwork(network);
        });
    });
}

function initOrderStatusFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const reference = params.get("reference");
    if (!reference) return;
    setModalVisible(statusModal, true);
    showStatusFromReference(reference);
}

function initHeaderScroll() {
    const header = document.querySelector(".header");
    if (!header) return;
    window.addEventListener("scroll", () => {
        if (window.scrollY > 100) header.classList.add("scrolled");
        else header.classList.remove("scrolled");
    });
}

function initMobileMenu() {
    const menuBtn = document.querySelector(".mobile-menu");
    const navLinks = document.querySelector(".nav-links");
    if (!menuBtn || !navLinks) return;

    const setOpen = (open) => {
        navLinks.classList.toggle("open", open);
        menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
        const icon = menuBtn.querySelector("i");
        if (icon) icon.className = open ? "fas fa-times" : "fas fa-bars";
    };

    menuBtn.addEventListener("click", () => setOpen(!navLinks.classList.contains("open")));

    // Close as soon as a link is tapped (fixes the "click twice" issue) and after navigating.
    navLinks.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => setOpen(false));
    });

    // Close when tapping outside the menu.
    document.addEventListener("click", (e) => {
        if (navLinks.classList.contains("open") && !navLinks.contains(e.target) && !menuBtn.contains(e.target)) {
            setOpen(false);
        }
    });
}

function initFooterYear() {
    const el = document.getElementById("footerYear");
    if (el) el.textContent = new Date().getFullYear();
}

document.addEventListener("DOMContentLoaded", () => {
    showLoadingScreen();
    initNetworkTabs();
    initHeaderScroll();
    initMobileMenu();
    initFooterYear();
    loadBundles().then(hideLoadingScreen);
    initOrderStatusFromQuery();

    if (document.getElementById("heroBuyBtn")) document.getElementById("heroBuyBtn").addEventListener("click", scrollToBundles);
    if (document.getElementById("heroViewBtn")) document.getElementById("heroViewBtn").addEventListener("click", scrollToBundles);

    document.getElementById("sameAsRecipient").addEventListener("change", copyRecipientToPayer);
    document.getElementById("recipientPhone").addEventListener("input", copyRecipientToPayer);

    orderForm.addEventListener("submit", handleOrderSubmit);
    const trackForm = document.getElementById("trackForm");
    if (trackForm) trackForm.addEventListener("submit", handleTrackSubmit);

    // Copy-to-clipboard for the order reference (delegated; works in modal + tracker).
    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".copy-ref-btn");
        if (!btn) return;
        const ref = btn.getAttribute("data-ref") || "";
        const done = () => { btn.innerHTML = '<i class="fas fa-check"></i> Copied!'; setTimeout(() => { btn.innerHTML = '<i class="fas fa-copy"></i> Copy'; }, 1500); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(ref).then(done).catch(() => {});
        } else {
            const ta = document.createElement("textarea");
            ta.value = ref; document.body.appendChild(ta); ta.select();
            try { document.execCommand("copy"); done(); } catch (_) {}
            document.body.removeChild(ta);
        }
    });
    orderModalClose.addEventListener("click", closeOrderModal);
    orderModalBackdrop.addEventListener("click", closeOrderModal);
    statusModalClose.addEventListener("click", closeStatusModal);
    statusModalBackdrop.addEventListener("click", closeStatusModal);

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeOrderModal();
            setModalVisible(processingModal, false);
            closeStatusModal();
        }
    });
});
