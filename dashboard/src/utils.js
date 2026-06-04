const SYMBOLS = { INR: '₹', EUR: '€', USD: '$' };
// ISO code → display symbol (falls back to the code itself, then ₹).
export const curSymbol = (currency = 'INR') => SYMBOLS[currency] || currency || '₹';
// Accepts an ISO code ('INR'/'EUR'/'USD') or a raw symbol; defaults to INR.
export const money = (v, currency = 'INR') =>
  `${curSymbol(currency)} ${Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const statusTheme = (s) =>
  ({ Paid: 'green', Open: 'blue', Overdue: 'red', Draft: 'gray', Cancelled: 'gray', Waived: 'orange' }[s] || 'gray');

export const standingTheme = (s) =>
  ({ current: 'green', past_due: 'orange', suspended: 'red' }[s] || 'gray');

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) return resolve(true);
    const s = document.createElement('script');
    s.src = src; s.onload = () => resolve(true); s.onerror = () => reject(new Error('Could not load Razorpay Checkout'));
    document.head.appendChild(s);
  });
}

// Opens the real Razorpay Checkout modal against a server-created order.
export async function openRazorpay({ key, order_id, amount, currency, description, prefill }) {
  await loadScript('https://checkout.razorpay.com/v1/checkout.js');
  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key, order_id, amount, currency: currency || 'INR',
      name: 'Cloud Billing', description: description || 'Payment', prefill: prefill || {},
      handler: (resp) => resolve(resp),
      modal: { ondismiss: () => reject(new Error('Payment cancelled')) },
    });
    rzp.on('payment.failed', (resp) => reject(new Error(resp.error?.description || 'Payment failed')));
    rzp.open();
  });
}

// "past_due" -> "Past Due", "current" -> "Active"
export const titleCase = (s) => {
  if (!s) return '';
  if (s === 'current') return 'Active';
  return String(s).split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
};

// Payment Attempt status — customer-friendly label + badge colour.
export const attemptLabel = (s) =>
  ({ captured: 'Successful', authorised: 'Authorised', initiated: 'Pending', failed: 'Failed', refunded: 'Refunded' }[s] || titleCase(s));
export const attemptTheme = (s) =>
  ({ captured: 'green', authorised: 'blue', initiated: 'gray', failed: 'red', refunded: 'orange' }[s] || 'gray');

// Payment method type label.
export const methodLabel = (s) =>
  ({ card: 'Card', upi_autopay: 'UPI Autopay', mandate: 'Mandate' }[s] || titleCase(s));

// Invoice type label.
export const invoiceTypeLabel = (s) =>
  ({ billable: 'Billable', cost_report: 'Cost Report' }[s] || titleCase(s));
