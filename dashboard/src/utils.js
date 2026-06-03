export const money = (v, currency = '₹') =>
  `${currency} ${Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const statusTheme = (s) =>
  ({ Paid: 'green', Open: 'blue', Overdue: 'red', Draft: 'gray', Cancelled: 'gray', Waived: 'orange' }[s] || 'gray');

export const standingTheme = (s) =>
  ({ current: 'green', past_due: 'orange', suspended: 'red' }[s] || 'gray');
