# Pricing & Bundle Flow – Confirmation

## 1. Money flow (your understanding is correct)

| Step | What happens |
|------|-------------------------------|
| **Customer sees** | Your selling price, e.g. **6 GHS** (1 GB bundle on your frontend). |
| **Customer pays** | 6 GHS via Paystack → money goes to **your Paystack account**. |
| **Your system** | After Paystack confirms payment (webhook), your backend calls GHDataConnect. |
| **GHDataConnect** | They deliver the bundle to the customer’s phone and deduct from **your GHDataConnect wallet** at **their** price, e.g. **~4.1 GHS** for 1000 MB (1 GB) on MTN. |
| **Result** | You receive 6 GHS (Paystack), you pay ~4.1 GHS (GHDataConnect wallet). Your **profit** = 6 − 4.1 = **~1.9 GHS** (plus any markup you add). |

So: **customer pays you (Paystack) → you pay GHDataConnect from your prepaid balance with them.** The price the customer sees is your selling price; the amount GHDataConnect deducts is their price. Your system only talks to GHDataConnect **after** Paystack has confirmed the customer paid.

---

## 2. How GHDataConnect knows the bundle size

From the documentation:

- **Request:** `POST /v1/createIshareBundleOrder`  
  Body includes **`capacity`** = bundle size **in megabytes (MB)**.

So GHDataConnect knows the size purely from the **`capacity`** value we send:

- **1000** → 1000 MB = 1 GB  
- **2000** → 2 GB  
- **500** → 500 MB  
- etc.

Our backend already does this: when the customer buys a bundle, we send that same `capacity` (in MB) in the request to GHDataConnect. So:

- We **do** send the actual size we are buying (e.g. 1000 MB for 1 GB).
- They **do** know the size from our request.
- They deduct from your wallet according to **their** pricing for that size/network.

---

## 3. The “4.1” in the docs

In the docs they give an example like **1000 MB at 4.1** (e.g. 4.1 GHS). So:

- **1000 MB (1 GB)** → their price **4.1** (GHS) for that bundle.
- Our code uses that as **cost per 1000 MB** and scales:  
  `(capacity / 1000) * 4.1`  
  So 1000 MB → 4.1, 2000 MB → 8.2, etc. That matches the idea “4.1 for 1000 MB”.

So:

- **4.1** = their **price** (in GHS) for 1000 MB (1 GB), not a separate “size code”.
- **Size** is communicated only by **`capacity` in MB** (e.g. 1000, 2000).

---

## 4. Which bundle sizes does GHDataConnect accept? — UPDATED

The backend now uses the **exact MTN bundle list from the GHDataConnect portal**:

- **1 GB** (1000 MB) – ₵3.90  
- **2 GB** (2000 MB) – ₵7.90  
- **3 GB** – ₵11.80 | **4 GB** – ₵15.90 | **5 GB** – ₵19.90 | **6 GB** – ₵23.70  
- **8 GB** – ₵31.80 | **10 GB** – ₵38.90 | **15 GB** – ₵57.20 | **20 GB** – ₵76.20  
- **25 GB** – ₵96.20 | **30 GB** – ₵116.50 | **40 GB** – ₵153.00 | **50 GB** – ₵193.00  

So:

- We only **offer and send** these capacities (in MB) so GHDataConnect always accepts.
- **Cost** = their price (e.g. 3.90 for 1 GB). **Selling price** = cost + markup (e.g. ₵1), so the customer pays more and you keep the difference.
- To add **AIRTEL** (or other networks), add the same structure in `app/utils/pricing.py` from their portal.

---

## 5. Short answers to your questions

| Question | Answer |
|----------|--------|
| Do we show our price (e.g. 6 GHS) and they charge their price (e.g. 4 GHS)? | **Yes.** Customer pays you (Paystack); GHDataConnect deducts their amount from your GHDataConnect wallet. |
| Does our system update GHDataConnect only after the customer has paid? | **Yes.** We call GHDataConnect only after Paystack webhook confirms payment. |
| Do we send the actual bundle size we’re buying? | **Yes.** We send **`capacity` in MB** (e.g. 1000 for 1 GB). |
| How does GHDataConnect know the size? | From the **`capacity`** (MB) we send in **createIshareBundleOrder**. |
| Is “4.1” the price for 1000 MB (1 GB)? | **Yes.** In the docs, 4.1 is their price (GHS) for 1000 MB. We use it as cost per 1000 MB. |
| How do we know which sizes they accept? | From their **getAllNetworks** (or official docs). We can integrate **getAllNetworks** so we only offer and send sizes they support. |

If you want, the next step is to add a call to **getAllNetworks** and use that response to drive which bundles we show and which `capacity` values we send.
