/**
 * Billing & POS Pure Calculation Utilities.
 * Extracted pure logic for unit testing and reusability across counter, checkout, and receipts.
 */

/**
 * Calculates item line total after discount.
 * @param {number} mrpOrPrice
 * @param {number} quantity
 * @param {number} [discountPercent=0]
 * @returns {number}
 */
export function calculateLineTotal(mrpOrPrice, quantity, discountPercent = 0) {
    const price = Number(mrpOrPrice) || 0;
    const qty = Math.max(1, parseInt(quantity, 10) || 1);
    const disc = Math.max(0, Math.min(100, Number(discountPercent) || 0));
    
    const gross = price * qty;
    const discountAmount = gross * (disc / 100);
    return Math.round((gross - discountAmount) * 100) / 100;
}

/**
 * Computes complete cart totals including discounts and net payable.
 * @param {Array<{ quantity?: number, mrp?: number, unit_price?: number, discount_percent?: number }>} items
 * @param {number} [additionalDiscountAmount=0]
 * @returns {{ totalQuantity: number, grossTotal: number, itemDiscountTotal: number, netPayable: number }}
 */
export function computeCartSummary(items = [], additionalDiscountAmount = 0) {
    let totalQuantity = 0;
    let grossTotal = 0;
    let itemDiscountTotal = 0;

    for (const item of items) {
        const qty = item.quantity || 1;
        const price = Number(item.mrp || item.unit_price || 0);
        const disc = Number(item.discount_percent || 0);

        totalQuantity += qty;
        const gross = price * qty;
        const discAmt = gross * (disc / 100);

        grossTotal += gross;
        itemDiscountTotal += discAmt;
    }

    const netPayable = Math.max(0, grossTotal - itemDiscountTotal - (Number(additionalDiscountAmount) || 0));

    return {
        totalQuantity,
        grossTotal: Math.round(grossTotal * 100) / 100,
        itemDiscountTotal: Math.round(itemDiscountTotal * 100) / 100,
        netPayable: Math.round(netPayable * 100) / 100,
    };
}

/**
 * Formats a numeric currency value in Indian Rupee standard format (INR).
 * @param {number} amount
 * @returns {string}
 */
export function formatCurrencyINR(amount) {
    const val = Number(amount) || 0;
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2,
    }).format(val);
}
