/**
 * SweetMe & Omnom — Telegram Order Notification Worker
 * Cloudflare Worker: принимает данные заказа и отправляет уведомление в Telegram.
 * BOT_TOKEN и ADMIN_CHAT_ID хранятся как зашифрованные секреты Cloudflare — клиент их никогда не видит.
 */

const ALLOWED_ORIGINS = [
  'https://newacctv13-blip.github.io',
  'https://omnom-sweetme.pages.dev',
  'https://omnom-sweetme.vercel.app',
  'http://localhost:5173',
  'http://localhost:4173',
  'http://127.0.0.1:5173',
];

function corsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Access-Control-Allow-Origin': allowed,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
}

function formatOrderMessage(order) {
  const { name, phone, address, items, subtotal, delivery, total, currency } = order;
  const cur = currency || 'L';

  let lines = [];
  lines.push('🍪 <b>Новый заказ!</b>');
  lines.push('');
  lines.push(`👤 <b>Имя:</b> ${escapeHtml(name)}`);
  lines.push(`📞 <b>Телефон:</b> ${escapeHtml(phone)}`);
  lines.push(`📍 <b>Город:</b> Chișinău`);
  if (address) {
    lines.push(`🏠 <b>Адрес:</b> ${escapeHtml(address)}`);
  }
  lines.push('');
  lines.push('📦 <b>Состав заказа:</b>');

  if (Array.isArray(items)) {
    items.forEach(item => {
      const lineTotal = item.price * item.qty;
      lines.push(`  • ${escapeHtml(item.name)} × ${item.qty} = ${lineTotal} ${cur}`);
    });
  }

  lines.push('');
  lines.push(`💰 <b>Сумма:</b> ${subtotal} ${cur}`);
  lines.push(`🚚 <b>Доставка:</b> ${delivery} ${cur}`);
  lines.push(`💵 <b>К оплате:</b> <b>${total} ${cur}</b>`);
  lines.push('');
  lines.push(`🕐 ${new Date().toLocaleString('ru-RU', { timeZone: 'Europe/Chisinau' })}`);

  return lines.join('\n');
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

async function sendTelegram(env, message) {
  const url = `https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: env.ADMIN_CHAT_ID,
      text: message,
      parse_mode: 'HTML',
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Telegram API error ${res.status}: ${err}`);
  }

  return res.json();
}

async function forwardToAdmin(env, order) {
  if (!env.ADMIN_WEBHOOK_URL) return;
  try {
    await fetch(env.ADMIN_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(order),
      signal: AbortSignal.timeout(5000),
    });
    console.log('Order forwarded to admin webhook');
  } catch (err) {
    console.warn('Admin webhook unreachable:', err.message);
  }
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin') || '';
    const headers = corsHeaders(origin);

    // Preflight CORS
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers });
    }

    // Only POST /notify
    const url = new URL(request.url);
    if (request.method !== 'POST' || url.pathname !== '/notify') {
      return new Response(JSON.stringify({ error: 'Not found' }), {
        status: 404,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    // Validate secrets are configured
    if (!env.BOT_TOKEN || !env.ADMIN_CHAT_ID) {
      console.error('Missing BOT_TOKEN or ADMIN_CHAT_ID secrets');
      return new Response(JSON.stringify({ error: 'Worker not configured' }), {
        status: 500,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    // Parse body
    let order;
    try {
      order = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
        status: 400,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    // Basic validation
    if (!order.name || !order.phone || !Array.isArray(order.items) || order.items.length === 0) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), {
        status: 400,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }

    // Send notification
    try {
      const message = formatOrderMessage(order);
      await sendTelegram(env, message);
      ctx.waitUntil(forwardToAdmin(env, order));

      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    } catch (err) {
      console.error('sendTelegram failed:', err.message);
      return new Response(JSON.stringify({ ok: false, error: err.message }), {
        status: 502,
        headers: { ...headers, 'Content-Type': 'application/json' },
      });
    }
  },
};
