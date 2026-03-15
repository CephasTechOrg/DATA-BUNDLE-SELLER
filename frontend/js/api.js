// Use same origin when served with API (e.g. same domain); use localhost when dev or file://
function getBaseUrl() {
    if (typeof window === "undefined") return "";
    const p = window.location.protocol;
    const h = window.location.hostname;
    if (p === "file:" || !h || h === "localhost" || h === "127.0.0.1") return "http://127.0.0.1:8000";
    return ""; // production: same origin
}
const BASE_URL = getBaseUrl();

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

export async function getBundles() {
    const res = await fetch(`${BASE_URL}/bundles`);
    return handleResponse(res);
}

export async function createOrder(network, capacity, bundlePhone, email, paymentRefPhone = null) {
    const body = {
        network,
        capacity,
        phone_number: bundlePhone,
        email,
    };
    if (paymentRefPhone != null && String(paymentRefPhone).trim() !== "") {
        body.payment_reference_phone = paymentRefPhone.trim();
    }
    const res = await fetch(`${BASE_URL}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    return handleResponse(res);
}

export async function getOrderStatus(reference, refresh = false) {
    const url = `${BASE_URL}/orders/${encodeURIComponent(reference)}${refresh ? "?refresh=true" : ""}`;
    const res = await fetch(url);
    return handleResponse(res);
}
