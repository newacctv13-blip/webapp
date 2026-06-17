import { DATA } from './data.js';
import { UI } from './ui.js';

export const Cart = {
  items: [],
  _cbs: {},

  on(event, fn) {
    this._cbs[event] = fn;
  },

  _emit(event, ...args) {
    if (this._cbs[event]) this._cbs[event](...args);
  },

  init() {
    try {
      const saved = localStorage.getItem('omnom_cart');
      if (saved) this.items = JSON.parse(saved);
    } catch {}
    this.render();
  },

  get deliveryFee() {
    return (DATA.settings && DATA.settings.deliveryFee) || 60;
  },

  get waNumber() {
    return (DATA.settings && DATA.settings.whatsappNumber) || '37376732386';
  },

  get tgUsername() {
    return (DATA.settings && DATA.settings.telegramUsername) || '';
  },

  get currency() {
    return (DATA.settings && DATA.settings.currency) || 'L';
  },

  save() {
    localStorage.setItem('omnom_cart', JSON.stringify(this.items));
  },

  add(productId) {
    const item = this.items.find(i => i.productId === productId);
    if (item) {
      item.qty += 1;
    } else {
      this.items.push({ productId, qty: 1 });
    }
    this.save();
    this.render();
    this._emit('add', productId);
    UI.openCart();
  },

  remove(productId) {
    this.items = this.items.filter(i => i.productId !== productId);
    this.save();
    this.render();
    this._emit('remove', productId);
  },

  changeQty(productId, delta) {
    const item = this.items.find(i => i.productId === productId);
    if (!item) return;
    item.qty += delta;
    if (item.qty <= 0) {
      this.remove(productId);
      return;
    }
    this.save();
    this.render();
    this._emit('changeQty', productId, item.qty);
  },

  getQty(productId) {
    const item = this.items.find(i => i.productId === productId);
    return item ? item.qty : 0;
  },

  getTotal() {
    const products = DATA.products || [];
    return this.items.reduce((sum, item) => {
      const product = products.find(p => p.id === item.productId);
      return sum + (product ? product.price * item.qty : 0);
    }, 0);
  },

  getCount() {
    return this.items.reduce((sum, item) => sum + item.qty, 0);
  },

  clear() {
    this.items = [];
    this.save();
    this.render();
  },

  render() {
    const lang = DATA.lang;
    const t = DATA.translations[lang] || {};
    const products = DATA.products || [];
    const cartItemsEl = document.getElementById('cartItems');
    const cartSummaryEl = document.getElementById('cartSummary');
    const cartBadge = document.getElementById('cartBadge');
    const cartBadgeHeader = document.getElementById('cartBadgeHeader');
    const count = this.getCount();
    const cur = this.currency;

    if (cartBadge) cartBadge.textContent = count;
    if (cartBadgeHeader) cartBadgeHeader.textContent = count;

    if (count === 0) {
      cartItemsEl.innerHTML = `<div class="cart-empty">${t.emptyCart || ''}</div>`;
      cartSummaryEl.innerHTML = '';
      return;
    }

    let html = '';
    this.items.forEach(item => {
      const product = products.find(p => p.id === item.productId);
      if (!product) return;
      const name = product.name[lang] || '';
      const total = product.price * item.qty;
      html += `
        <div class="cart-item">
          <div class="cart-item-info">
            <div class="cart-item-name">${name}</div>
            <div class="cart-item-price">${product.price} ${cur} × ${item.qty} ${t.item || ''}</div>
          </div>
          <div class="cart-item-qty">
            <button class="qty-btn" onclick="Cart.changeQty(${item.productId}, -1)">−</button>
            <span class="qty-value">${item.qty}</span>
            <button class="qty-btn" onclick="Cart.changeQty(${item.productId}, 1)">+</button>
          </div>
          <div class="cart-item-total">${total} ${cur}</div>
          <button class="cart-item-remove" onclick="Cart.remove(${item.productId})" title="${t.remove || ''}">✕</button>
        </div>`;
    });
    cartItemsEl.innerHTML = html;

    const subtotal = this.getTotal();
    const delivery = subtotal > 0 ? this.deliveryFee : 0;
    cartSummaryEl.innerHTML = `
      <div class="cart-summary">
        <div class="cart-summary-row">
          <span>${t.total || ''}</span>
          <span>${subtotal} ${cur}</span>
        </div>
        <div class="cart-summary-row">
          <span>${t.delivery || ''}</span>
          <span>${delivery} ${cur}</span>
        </div>
        <div class="cart-summary-row total">
          <span>${t.toPay || ''}</span>
          <span>${subtotal + delivery} ${cur}</span>
        </div>
      </div>
      <div class="cart-form">
        <input type="text" id="orderName" placeholder="${t.namePlaceholder || ''}" onfocus="this.style.borderColor=''" />
        <input type="tel" id="orderPhone" placeholder="${t.phonePlaceholder || ''}" onfocus="this.style.borderColor=''" />
      </div>
      <button class="btn-order" onclick="Cart.submitOrder()">✈️ ${t.order || ''}</button>`;
  },

  submitOrder() {
    const lang = DATA.lang;
    const t = DATA.translations[lang] || {};
    const products = DATA.products || [];
    const name = document.getElementById('orderName')?.value.trim() || '';
    const phone = document.getElementById('orderPhone')?.value.trim() || '';
    const subtotal = this.getTotal();
    const delivery = this.deliveryFee;
    const total = subtotal + delivery;
    const cur = this.currency;

    if (!name) {
      document.getElementById('orderName').style.borderColor = '#E53935';
      document.getElementById('orderName').focus();
      return;
    }
    if (!phone) {
      document.getElementById('orderPhone').style.borderColor = '#E53935';
      document.getElementById('orderPhone').focus();
      return;
    }

    const items = this.items.map(item => {
      const product = products.find(p => p.id === item.productId);
      return product ? { name: product.name[lang], price: product.price, qty: item.qty } : null;
    }).filter(Boolean);

    const orderData = { name, phone, items, subtotal, delivery, total, currency: cur };

    let msg = `🍪 ${t.orderReady || ''}\n\n`;
    msg += `👤 ${name}\n📞 ${phone}\n📍 Chișinău\n\n`;

    this.items.forEach(item => {
      const product = products.find(p => p.id === item.productId);
      if (!product) return;
      const pname = product.name[lang];
      msg += `• ${pname} × ${item.qty} = ${product.price * item.qty} ${cur}\n`;
    });

    msg += `\n${t.total || ''}: ${subtotal} ${cur}\n${t.delivery || ''}: ${delivery} ${cur}\n`;
    msg += `💵 ${t.toPay || ''}: ${total} ${cur}`;

    const s = DATA.settings || {};
    const workerUrl = s.orderWorkerUrl;

    if (workerUrl) {
      this._sendViaWorker(workerUrl, orderData, msg);
    } else {
      this._sendViaFallback(msg);
    }
  },

  _sendViaWorker(workerUrl, orderData, fallbackMsg) {
    fetch(workerUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData),
    })
      .then(res => {
        if (!res.ok) throw new Error('Worker error');
        this.clear();
        UI.closeCart();
        this._emit('submit');
      })
      .catch(() => {
        this._sendViaFallback(fallbackMsg);
      });
  },

  _sendViaFallback(msg) {
    const s = DATA.settings || {};
    const url = s.telegramUsername
      ? `https://t.me/${s.telegramUsername}?text=${encodeURIComponent(msg)}`
      : `https://wa.me/${this.waNumber}?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank');
    this.clear();
    UI.closeCart();
    this._emit('submit');
  }
};

window.Cart = Cart;
