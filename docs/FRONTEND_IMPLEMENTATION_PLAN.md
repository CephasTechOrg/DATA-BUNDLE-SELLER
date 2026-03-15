# Frontend Redesign – Implementation Plan

Redesign the `frontend/` folder to match the customer reference design. Users choose **MTN** or **Telecel**, then see that network’s bundles. Clean, professional UI with hero image, loading screen, and modals.

---

## Reference

- **Design source:** `customer/` (ExtraData-style: loading screen, header, hero + image, bundles grid, How It Works, modals, footer)
- **Hero image:** `frontend/images/hero.png`
- **Backend API:** `GET /bundles`, `POST /orders`, `GET /orders/{reference}` (unchanged)

---

## Implementation Steps

| # | Step | Status | Notes |
|---|------|--------|--------|
| 1 | Create `frontend/images/` and ensure `hero.png` path is correct | ✅ Done | Using `images/hero.png` in hero section |
| 2 | Add loading screen (logo pulse + progress bar) to HTML | ✅ Done | |
| 3 | Add fixed header with logo, nav links (Bundles, How It Works, Contact), mobile menu | ✅ Done | Brand: "Bundle Reseller" |
| 4 | Add hero section: title, description, CTAs, stats, hero image | ✅ Done | |
| 5 | Add bundles section with section header + **network tabs (MTN \| Telecel)** | ✅ Done | |
| 6 | Add skeleton loading placeholders for bundle grid | ✅ Done | |
| 7 | Add How It Works section (3 steps with icons) | ✅ Done | |
| 8 | Add order modal: recipient phone, email, payment ref phone, "Same as above", summary, Proceed to Pay | ✅ Done | |
| 9 | Add processing modal (spinner during payment init) | ✅ Done | |
| 10 | Add success/order-status modal (after Paystack return) | ✅ Done | |
| 11 | Add footer (brand, links, copyright) | ✅ Done | |
| 12 | Port customer CSS: variables, loading, header, hero, bundles, steps, modals, footer, responsive | ✅ Done | Customer CSS copied; network-tabs, modal [hidden], loading-inline, error-inline added |
| 13 | Implement JS: load bundles, network tabs, render bundle cards, open order modal, submit order, Paystack popup/redirect, status from query | ✅ Done | See `frontend/js/main.js` |
| 14 | Add `payment_reference_phone` to API and optional "Same as above" in form | ✅ Done | `api.js` createOrder accepts paymentRefPhone; form has checkbox |
| 15 | Final pass: accessibility, error toasts, mobile menu toggle | ✅ Done | Toasts, ESC close, mobile menu, aria on tabs/modals |

---

## Done

- All 15 steps completed. Frontend mirrors customer design: loading screen, header, hero with `images/hero.png`, network tabs (MTN | Telecel), bundle cards, How It Works, order modal (recipient phone, email, payment ref + “Same as above”), processing modal, status modal, footer. JS: load bundles, switch by tab, order flow, Paystack redirect (popup if `access_code` returned), status from `?reference=`.

---

## File Changes Summary

| File | Action |
|------|--------|
| `frontend/index.html` | Replace with full layout (loading, header, hero, bundles + tabs, how-it-works, modals, footer) |
| `frontend/style/style.css` | Replace/expand to match customer design system |
| `frontend/js/main.js` | Rewrite: network tabs, bundle grid, order modal, Paystack, status from URL |
| `frontend/js/api.js` | Add `payment_reference_phone` to `createOrder` |
| `frontend/images/hero.png` | Already added by user; only reference in HTML |
| `docs/FRONTEND_IMPLEMENTATION_PLAN.md` | This plan; update status as we go |
