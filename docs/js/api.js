// Local: use dev server. Production (Vercel/Netlify): use Render backend. Override with window.API_BASE_URL if needed.
function getBaseUrl() {
    if (typeof window !== "undefined" && window.API_BASE_URL) return window.API_BASE_URL.replace(/\/$/, "");
    if (typeof window === "undefined") return "";
    const p = window.location.protocol;
    const h = window.location.hostname;
    if (p === "file:" || !h || h === "localhost" || h === "127.0.0.1") return "http://127.0.0.1:8000";
    return "https://bundlereseller-backend.onrender.com";
}
const BASE_URL = getBaseUrl();

// Retry when backend is asleep (e.g. Render free tier). Long timeout + retries so user sees loading instead of instant error.
const FETCH_TIMEOUT_MS = 60000;  // 60s per attempt (Render can take 30–60s to wake)
const FETCH_RETRIES = 3;         // 3 attempts total
const RETRY_DELAY_MS = 3000;     // 3s between retries

function isNetworkError(err) {
    return err instanceof TypeError && (err.message === "Failed to fetch" || err.message === "Load failed");
}

async function fetchWithRetry(url, options = {}, onRetry) {
    let lastErr;
    for (let attempt = 1; attempt <= FETCH_RETRIES; attempt++) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        try {
            const res = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(id);
            return res;
        } catch (err) {
            clearTimeout(id);
            lastErr = err;
            const isRetryable = isNetworkError(err) || err.name === "AbortError";
            if (isRetryable && attempt < FETCH_RETRIES) {
                if (typeof onRetry === "function") onRetry(attempt);
                await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
            } else {
                throw err;
            }
        }
    }
    throw lastErr;
}

async function handleResponse(res) {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const raw = data.detail ?? data.message ?? res.statusText;
        const message = Array.isArray(raw)
            ? raw.map((m) => (m && m.msg) || m).join(", ")
            : typeof raw === "string"
                ? raw
                : "Request failed";
        const err = new Error(message);
        err.status = res.status;
        err.data = data;
        throw err;
    }
    return data;
}

export async function getBundles(onRetry) {
    const res = await fetchWithRetry(`${BASE_URL}/bundles`, {}, onRetry);
    return handleResponse(res);
}

export async function createOrder(network, capacity, bundlePhone, email, paymentRefPhone = null, onRetry) {
    const body = {
        network,
        capacity,
        phone_number: bundlePhone,
        email,
    };
    if (paymentRefPhone != null && String(paymentRefPhone).trim() !== "") {
        body.payment_reference_phone = paymentRefPhone.trim();
    }
    const res = await fetchWithRetry(`${BASE_URL}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    }, onRetry);
    return handleResponse(res);
}

export async function getOrderStatus(reference, refresh = false, onRetry) {
    const url = `${BASE_URL}/orders/${encodeURIComponent(reference)}${refresh ? "?refresh=true" : ""}`;
    const res = await fetchWithRetry(url, {}, onRetry);
    return handleResponse(res);
}
