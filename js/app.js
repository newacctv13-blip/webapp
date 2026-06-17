import { DATA } from './data.js';
import { Cart } from './cart.js';
import { UI } from './ui.js';

const ThemeManager = {
  STORAGE_KEY: 'omnom_theme',

  init() {
    this.toggle = document.getElementById('themeToggle');
    this.loadTheme();
    this.toggle.addEventListener('click', () => this.toggleTheme());
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (!localStorage.getItem(this.STORAGE_KEY)) this.setThemeByTime();
    });
  },

  getPreferredTheme() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved) return saved;
    return this.getTimeBasedTheme();
  },

  getTimeBasedTheme() {
    const hour = new Date().getHours();
    return (hour >= 6 && hour < 20) ? 'light' : 'dark';
  },

  setThemeByTime() {
    const theme = this.getTimeBasedTheme();
    this.applyTheme(theme);
  },

  applyTheme(theme) {
    const html = document.documentElement;
    const prev = html.getAttribute('data-theme');
    if (prev === theme) return;
    html.classList.add('theme-transitioning');
    html.setAttribute('data-theme', theme);
    requestAnimationFrame(() => {
      setTimeout(() => html.classList.remove('theme-transitioning'), 500);
    });
  },

  loadTheme() {
    const theme = this.getPreferredTheme();
    document.documentElement.setAttribute('data-theme', theme);
    if (this.toggle) {
      this.toggle.innerHTML = '<span class="toggle-icons"><span>☀️</span><span>🌙</span></span>';
    }
  },

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'light' ? 'dark' : 'light';
    localStorage.setItem(this.STORAGE_KEY, next);
    this.applyTheme(next);
  }
};

const ScrollReveal = {
  observer: null,

  init() {
    if ('IntersectionObserver' in window) {
      this.observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            this.observer.unobserve(entry.target);
          }
        });
      }, { rootMargin: '0px 0px -60px 0px', threshold: 0.1 });

      document.querySelectorAll('.reveal').forEach(el => this.observer.observe(el));
    } else {
      document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
    }
  },

  observe(el) {
    if (this.observer) this.observer.observe(el);
    else el.classList.add('visible');
  }
};

const TiltEffect = {
  init() {
    this.attachCards();
    const container = document.getElementById('productsContainer');
    if (container) {
      new MutationObserver(() => this.attachCards()).observe(container, { childList: true, subtree: true });
    }
  },

  attachCards() {
    document.querySelectorAll('.product-card:not([data-tilt])').forEach(card => {
      card.dataset.tilt = '1';
      let rafId = null;

      card.addEventListener('mousemove', (e) => {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
          const rect = card.getBoundingClientRect();
          const x = Math.min(Math.max((e.clientX - rect.left) / rect.width, 0), 1);
          const y = Math.min(Math.max((e.clientY - rect.top) / rect.height, 0), 1);
          card.style.setProperty('--mouse-x', x);
          card.style.setProperty('--mouse-y', y);
          card.classList.add('tilt-active');
        });
      });

      card.addEventListener('mouseleave', () => {
        if (rafId) cancelAnimationFrame(rafId);
        card.classList.remove('tilt-active');
        card.style.removeProperty('--mouse-x');
        card.style.removeProperty('--mouse-y');
      });
    });
  }
};

const App = {
  currentCategory: null,
  sidebarTimer: null,
  sidebarOpen: false,

  t(key) {
    const lang = DATA.lang;
    const keys = key.split('.');
    let val = DATA.translations[lang];
    for (const k of keys) {
      if (val && val[k] !== undefined) val = val[k];
      else return key;
    }
    return val;
  },

  init() {
    const savedLang = localStorage.getItem('omnom_lang');
    if (savedLang === 'ru' || savedLang === 'ro') DATA.lang = savedLang;
    ThemeManager.init();
    Cart.init();
    Cart.on('add', (id) => this.updateAddButton(id, true));
    Cart.on('remove', (id) => this.updateAddButton(id, false));
    Cart.on('changeQty', (id, qty) => this.updateQtyDisplay(id, qty));
    Cart.on('submit', () => this.renderAllProducts());
    this.renderSidebar();
    this.renderHeader();
    this.renderWhatsAppFloat();
    this.renderAllProducts();
    this.setupSidebar();
    this.setupEventListeners();
    ScrollReveal.init();
    TiltEffect.init();
    document.getElementById('cartOverlay').addEventListener('click', UI.closeCart);
    document.getElementById('cartClose').addEventListener('click', UI.closeCart);
  },

  renderSidebar() {
    const t = this.t;
    const lang = DATA.lang;
    const cats = DATA.categories || [];
    const catT = (DATA.translations[lang] || {}).categories || {};

    const nav = document.getElementById('sidebarNav');
    const subtitle = document.getElementById('sidebarSubtitle');
    if (subtitle) subtitle.textContent = t('subtitle');

    let html = `<li class="active" data-cat="all"><span class="cat-icon">📋</span> ${catT.all || 'All'}</li>`;

    cats.forEach(cat => {
      html += `<li data-cat="${cat.id}"><span class="cat-icon">${cat.icon || '📦'}</span> ${catT[cat.id] || cat.id}</li>`;
    });

    nav.innerHTML = html;
  },

  renderHeader() {
    const t = this.t;
    const s = DATA.settings || {};
    document.getElementById('header').innerHTML = `
      <div class="hero">
        <div class="hero-logo">
          <a href="index.html"><img src="images/logo.svg" alt="Omnom & SweetMe" class="hero-logo-img" /></a>
        </div>
        <div class="hero-content">
          <div class="hero-top">
            <div class="hero-info">
              <h1 class="hero-title">Omnom & SweetMe</h1>
              <p class="hero-subtitle">${t('subtitle')}</p>
            </div>
            <div class="hero-actions">
              <a class="hero-visit-btn" href="visit.html">${t('whereToFind')}</a>
              <button class="cart-toggle-header" onclick="UI.openCart()">
                🛒 ${t('cart')} <span class="cart-badge" id="cartBadgeHeader">0</span>
              </button>
            </div>
          </div>
          <div class="hero-description" id="heroDesc">
            <span class="hero-desc-short">${t('description').slice(0, Math.ceil(t('description').length / 2))}</span><span class="hero-desc-ellipsis">...</span>
            <span class="hero-desc-full">${t('description')}</span>
            <button class="hero-desc-toggle" onclick="App.toggleHeroDesc()">читать далее</button>
          </div>
          <div class="hero-meta">
            <span class="hero-meta-item"><span class="icon">🕐</span> ${t('workMode')}</span>
            <span class="hero-meta-item"><span class="icon">📍</span> <a href="${s.mapsUrl || '#'}" target="_blank">${s.city || 'Chișinău'}</a></span>
            <span class="hero-meta-item"><span class="icon">📞</span> <a href="tel:${s.phone || '+37376732386'}">${t('phone')}</a></span>
            <span class="hero-meta-item"><span class="icon">📸</span> <a href="${s.instagramUrl || '#'}" target="_blank">${t('instagram')}</a></span>
            <span class="hero-meta-item"><span class="icon">📍</span> <a href="visit.html">${t('whereToFind')}</a></span>
            <span class="hero-meta-item"><span class="icon">✈️</span> <a class="whatsapp-link" href="https://t.me/${s.telegramUsername || ''}" target="_blank">Telegram</a></span>
          </div>
        </div>
      </div>`;
  },

  renderWhatsAppFloat() {
    const s = DATA.settings || {};
    const tgUser = s.telegramUsername || '';
    if (document.getElementById('whatsappFloat')) return;
    const btn = document.createElement('a');
    btn.id = 'whatsappFloat';
    btn.className = 'whatsapp-float';
    btn.href = tgUser ? `https://t.me/${tgUser}` : `https://wa.me/${s.whatsappNumber || '37376732386'}`;
    btn.target = '_blank';
    btn.innerHTML = '✈️';
    btn.setAttribute('aria-label', 'Telegram');
    document.body.appendChild(btn);
  },

  renderAllProducts() {
    const container = document.getElementById('productsContainer');
    const lang = DATA.lang;
    const products = this.currentCategory
      ? DATA.products.filter(p => p.category === this.currentCategory)
      : DATA.products;

    const renderCardsWithCenterSpread = (items, max = 5) => {
      const display = items.slice(0, max);
      const n = display.length;
      const center = (n - 1) / 2;
      return display.map((p, i) => {
        const dist = Math.abs(i - center);
        const cardDelay = dist * 0.06;
        const imgDelay = 0.06 + dist * 0.06;
        return this.renderProductCard(p, cardDelay, imgDelay);
      }).join('');
    };

    let html = '';

    const catT = (DATA.translations[lang] || {}).categories || {};
    const unit = (DATA.translations[lang] || {}).item || 'шт';

    if (this.currentCategory) {
      const cat = (DATA.categories || []).find(c => c.id === this.currentCategory);
      html += `<div class="section reveal"><div class="products-grid">
        <div class="category-header">
          <span class="cat-icon">${cat ? cat.icon : '📋'}</span>
          <span class="cat-name">${catT[this.currentCategory] || ''}</span>
          <span class="cat-count">${products.length} ${unit}</span>
        </div>`;
      html += renderCardsWithCenterSpread(products, products.length);
      html += `</div></div>`;
    } else {
      (DATA.categories || []).forEach(cat => {
        const catProducts = DATA.products.filter(p => p.category === cat.id);
        if (catProducts.length === 0) return;
      html += `<div class="section reveal" id="section-${cat.id}"><div class="products-grid">
        <div class="category-header" data-cat="${cat.id}">
          <span class="cat-icon">${cat.icon || '📦'}</span>
          <span class="cat-name">${catT[cat.id] || cat.id}</span>
          <span class="cat-count">${catProducts.length} ${unit}</span>
        </div>`;
        html += renderCardsWithCenterSpread(catProducts, catProducts.length);
        html += `</div></div>`;
      });
    }

    container.innerHTML = html;

    if (typeof ScrollReveal !== 'undefined' && ScrollReveal.observer) {
      container.querySelectorAll('.reveal:not(.visible)').forEach(el => ScrollReveal.observe(el));
    }
  },

  renderProductCard(product, cardDelay = 0, imgDelay = 0.06) {
    const lang = DATA.lang;
    const t = this.t;
    const inCart = Cart.getQty(product.id) > 0;
    const qty = Cart.getQty(product.id);

    return `
      <div class="product-card" data-id="${product.id}" style="--card-delay:${cardDelay}s;--img-delay:${imgDelay}s">
        <img src="${product.image}" alt="${product.name[lang]}" loading="lazy" data-product-id="${product.id}" />
        <div class="product-body">
          <div class="product-name">${product.name[lang]}</div>
          <div class="product-desc">${product.desc[lang]}</div>
          <div class="product-footer">
            <div class="product-price">
              ${product.price} <small>${DATA.settings.currency || 'L'}</small>
              <span class="product-unit">/ ${t('item')}</span>
            </div>
            <div class="qty-controls ${inCart ? 'visible' : ''}" id="qty-${product.id}">
              <button class="qty-btn" onclick="Cart.changeQty(${product.id}, -1); App.updateQtyDisplay(${product.id}, Cart.getQty(${product.id}))">−</button>
              <span class="qty-value" id="qtyVal-${product.id}">${qty}</span>
              <button class="qty-btn" onclick="Cart.changeQty(${product.id}, 1); App.updateQtyDisplay(${product.id}, Cart.getQty(${product.id}))">+</button>
            </div>
            <button class="btn-cart ${inCart ? 'added' : ''}" id="btnCart-${product.id}" onclick="Cart.add(${product.id})">
              ${inCart ? '✓' : t('addToCart')}
            </button>
          </div>
        </div>
      </div>`;
  },

  toggleHeroDesc() {
    const el = document.getElementById('heroDesc');
    if (!el) return;
    const expanded = el.classList.toggle('expanded');
    el.querySelector('.hero-desc-toggle').textContent = expanded ? 'скрыть' : 'читать далее';
  },

  openModal(productId) {
    const product = DATA.products.find(p => p.id === productId);
    if (!product) return;
    const lang = DATA.lang;
    const t = this.t;
    const modal = document.getElementById('productModal');
    document.getElementById('modalImg').src = product.image;
    document.getElementById('modalImg').alt = product.name[lang];
    document.getElementById('modalName').textContent = product.name[lang];
    document.getElementById('modalDesc').textContent = product.desc[lang];
    document.getElementById('modalPrice').innerHTML = `${product.price} <small>${DATA.settings.currency || 'L'}</small>`;
    const btn = document.getElementById('modalAddBtn');
    const inCart = Cart.getQty(product.id) > 0;
    btn.textContent = inCart ? '✓' : t('addToCart');
    btn.className = 'btn-cart' + (inCart ? ' added' : '');
    btn.onclick = () => { Cart.add(product.id); btn.textContent = '✓'; btn.classList.add('added'); };
    modal.classList.add('visible');
    document.body.style.overflow = 'hidden';
  },

  closeModal() {
    document.getElementById('productModal').classList.remove('visible');
    document.body.style.overflow = '';
  },

  updateAddButton(productId, inCart) {
    const btn = document.getElementById(`btnCart-${productId}`);
    const qtyEl = document.getElementById(`qty-${productId}`);
    const lang = DATA.lang;
    if (btn) {
      btn.textContent = inCart ? '✓' : DATA.translations[lang].addToCart;
      btn.classList.toggle('added', inCart);
    }
    if (qtyEl) {
      qtyEl.classList.toggle('visible', inCart);
    }
  },

  updateQtyDisplay(productId, qty) {
    const val = document.getElementById(`qtyVal-${productId}`);
    if (val) val.textContent = qty;
    if (qty === 0) {
      this.updateAddButton(productId, false);
    }
  },

  setLang(lang) {
    DATA.lang = lang;
    localStorage.setItem('omnom_lang', lang);
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b.textContent === lang.toUpperCase()));
    this.renderSidebar();
    this.renderHeader();
    this.renderAllProducts();
    Cart.render();
  },

  setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const trigger = document.getElementById('sidebarTrigger');
    const overlay = document.getElementById('overlay');
    const isMobile = () => window.innerWidth <= 768;

    const openSidebar = () => {
      if (isMobile()) return;
      clearTimeout(this.sidebarTimer);
      sidebar.classList.add('open');
      overlay.classList.add('visible');
      this.sidebarOpen = true;
    };

    const closeSidebar = () => {
      if (isMobile()) return;
      clearTimeout(this.sidebarTimer);
      this.sidebarTimer = setTimeout(() => {
        sidebar.classList.remove('open');
        overlay.classList.remove('visible');
        this.sidebarOpen = false;
      }, 300);
    };

    if (trigger) {
      trigger.addEventListener('mouseenter', openSidebar);
    }

    sidebar.addEventListener('mouseenter', () => {
      if (isMobile()) return;
      clearTimeout(this.sidebarTimer);
    });

    sidebar.addEventListener('mouseleave', closeSidebar);

    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('visible');
      this.sidebarOpen = false;
    });
  },

  setupEventListeners() {
    const sidebar = document.getElementById('sidebar');
    const nav = document.getElementById('sidebarNav');
    const mobileBtn = document.getElementById('mobileMenuBtn');
    const overlay = document.getElementById('overlay');
    const isMobile = () => window.innerWidth <= 768;

    if (nav) {
      nav.addEventListener('click', (e) => {
        const li = e.target.closest('li[data-cat]');
        if (!li) return;
        const cat = li.dataset.cat;

        nav.querySelectorAll('li').forEach(l => l.classList.remove('active'));
        li.classList.add('active');

        this.currentCategory = cat === 'all' ? null : cat;
        this.renderAllProducts();
        document.querySelectorAll('.reveal:not(.visible)').forEach(el => ScrollReveal.observe(el));

        if (isMobile()) {
          sidebar.classList.remove('open');
          overlay.classList.remove('visible');
        }
      });
    }

    if (mobileBtn) {
      mobileBtn.addEventListener('click', () => {
        const isOpen = sidebar.classList.toggle('open');
        overlay.classList.toggle('visible', isOpen);
      });
    }

    const filterToCategory = (cat) => {
      this.currentCategory = cat === 'all' ? null : cat;
      this.renderAllProducts();
      document.querySelectorAll('.reveal:not(.visible)').forEach(el => ScrollReveal.observe(el));
      if (nav) {
        nav.querySelectorAll('li').forEach(l => l.classList.toggle('active', l.dataset.cat === cat));
      }
    };

    document.addEventListener('click', (e) => {
      const catHeader = e.target.closest('.category-header[data-cat]');
      if (catHeader) {
        filterToCategory(catHeader.dataset.cat);
        return;
      }
      const img = e.target.closest('.product-card img[data-product-id]');
      if (img) {
        this.openModal(Number(img.dataset.productId));
        return;
      }
    });

    const modal = document.getElementById('productModal');
    if (modal) {
      document.getElementById('modalClose').addEventListener('click', () => this.closeModal());
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.closeModal();
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.closeModal();
      });
    }

    window.addEventListener('resize', () => {
      if (!isMobile()) {
        sidebar.classList.remove('open');
        overlay.classList.remove('visible');
        mobileBtn.style.display = 'none';
      } else {
        mobileBtn.style.display = 'block';
      }
    });
  }
};

window.App = App;
window.UI = UI;

document.addEventListener('DOMContentLoaded', () => App.init());
