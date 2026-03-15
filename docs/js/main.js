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
    toast.style.cssText = "position:fixed;top:20px;right:20px;background:#ef4444;color:#fff;padding:1rem 1.5rem;border-radius:12px;box-shadow:0 10px 25px rgba(239,68,68,0.3);z-index:10000;max-width:400px;";
    toast.innerHTML = `<div style="display:flex;align-items:flex-start;gap:0.75rem;"><i class="fas fa-exclamation-circle" style="font-size:1.2rem;"></i><div>${escapeHtml(message)}</div></div>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
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
    const cardClass = networkKey === "Telecel" ? "bundle-card bundle-card--telecel" : "bundle-card bundle-card--mtn";
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
            if (typeof window.PaystackPop !== "undefined" && order.access_code) {
                const popup = new window.PaystackPop();
                popup.resumeTransaction(order.access_code, {
                    onSuccess: () => showStatusFromReference(order.reference),
                    onCancel: () => showToast("Payment cancelled."),
                });
            } else {
                window.location.href = order.payment_url;
            }
        } else {
            showToast(order.message || order.detail || "Could not start payment.");
            setModalVisible(orderModal, true);
        }
    } catch (err) {
        setModalVisible(processingModal, false);
        showToast(err.message || "Something went wrong. Please try again.");
        setModalVisible(orderModal, true);
    } finally {
        orderSubmitBtn.disabled = false;
        orderSubmitBtn.innerHTML = '<i class="fas fa-credit-card"></i><span>Proceed to Pay</span>';
    }
}

function showStatusFromReference(reference) {
    setModalVisible(statusModal, true);
    if (statusContent) statusContent.innerHTML = "<p>Checking order…</p>";
    getOrderStatus(reference, true)
        .then((data) => {
            if (!statusContent) return;
            if (data.error) {
                statusContent.innerHTML = `<p class="error-inline">${escapeHtml(data.error)}</p>`;
                return;
            }
            statusContent.innerHTML = `
                <p><strong>Reference:</strong> ${escapeHtml(data.reference)}</p>
                <p><strong>Status:</strong> ${escapeHtml(data.status)}</p>
                <p><strong>Payment:</strong> ${escapeHtml(data.payment_status || "—")}</p>`;
        })
        .catch((err) => {
            if (statusContent) statusContent.innerHTML = `<p class="error-inline">${escapeHtml(err.message || "Could not load status.")}</p>`;
        });
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
    if (menuBtn && navLinks) {
        menuBtn.addEventListener("click", () => {
            const isOpen = navLinks.style.display === "flex";
            navLinks.style.display = isOpen ? "none" : "flex";
        });
    }
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
