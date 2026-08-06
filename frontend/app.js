/* ═══════════════════════════════════════════════
   TgGifts — Vue 3 App Logic
   ═══════════════════════════════════════════════ */

const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;

// ── Telegram WebApp SDK ────────────────────────
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try { tg.setBackgroundColor('#0D0E1A'); } catch {}
  try { tg.setHeaderColor('#0D0E1A'); } catch {}
}
const ME = tg?.initDataUnsafe?.user || null;
const INIT_DATA = tg?.initData || '';

// ── API Fetcher ────────────────────────────────
const H = {
  'ngrok-skip-browser-warning': '69420',
  'X-Init-Data': INIT_DATA,
};
const api = (url, opts = {}) => fetch(url, {
  ...opts,
  headers: { ...H, ...(opts.headers || {}) },
});

// ── Image Fallback mapping per animation ───────
const IMG_MAP = {
  'pink_bear.json': 'assets/rose_bear.gif',
  'plumber_bear.json': 'assets/worker.gif',
  'football_bear.json': 'assets/football.gif',
};

// ── Lottie Cache ───────────────────────────────
const animCache = {};
async function preloadAnim(filename) {
  if (!filename) return null;
  if (animCache[filename]) return animCache[filename];
  try {
    const r = await fetch(`assets/${filename}`, { headers: { 'ngrok-skip-browser-warning': '69420' } });
    if (!r.ok) return null;
    const data = await r.json();
    animCache[filename] = data;
    return data;
  } catch (e) {
    console.error('Failed to fetch anim:', filename, e);
    return null;
  }
}

// ── Lottie SVG Component ───────────────────────
const LottieAnim = {
  props: { filename: String, fallbackImg: String },
  setup(props) {
    const el = ref(null);
    const failed = ref(false);
    let inst = null;

    const destroy = () => {
      if (inst) {
        try { inst.destroy(); } catch {}
        inst = null;
      }
    };

    const load = async () => {
      await nextTick();
      if (!props.filename) {
        failed.value = true;
        return;
      }
      failed.value = false;
      const data = await preloadAnim(props.filename);
      if (!data || !el.value) {
        failed.value = true;
        return;
      }
      destroy();
      try {
        inst = lottie.loadAnimation({
          container: el.value,
          renderer: 'svg',
          loop: true,
          autoplay: true,
          animationData: JSON.parse(JSON.stringify(data)),
          rendererSettings: {
            preserveAspectRatio: 'xMidYMid meet',
            progressiveLoad: false,
          },
        });
      } catch (e) {
        console.warn('Lottie render error:', props.filename, e);
        failed.value = true;
      }
    };

    onMounted(load);
    watch(() => props.filename, load);
    Vue.onUnmounted(destroy);
    return { el, failed };
  },
  template: `
    <div class="lottie-box-wrap" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;">
      <div v-show="!failed" ref="el" class="lottie-box"></div>
      <img v-if="failed && fallbackImg" :src="fallbackImg" class="card-img" alt="gift"/>
    </div>
  `,
};

// ── Gift Color Scheme ──────────────────────────
const GC = {
  '🎄': { c1: '#22c55e', c2: '#86efac', glow: 'rgba(34,197,94,.55)' },
  '🎁': { c1: '#7B61FF', c2: '#a07af8', glow: 'rgba(123,97,255,.55)' },
  '🧸': { c1: '#f5c842', c2: '#fb923c', glow: 'rgba(245,200,66,.55)' },
};
const gc = e => GC[e] || GC['🎁'];

// ── Confetti ───────────────────────────────────
function confetti() {
  const canvas = document.getElementById('confettiCanvas');
  if (!canvas) return;
  canvas.width = innerWidth; canvas.height = innerHeight;
  const ctx = canvas.getContext('2d');
  const cols = ['#7B61FF', '#FFD700', '#fb923c', '#22c55e', '#a07af8', '#fff'];
  const p = Array.from({ length: 100 }, () => ({
    x: Math.random() * canvas.width, y: -20,
    w: 6 + Math.random() * 6, h: 3 + Math.random() * 4,
    c: cols[~~(Math.random() * cols.length)],
    r: 0, dr: (Math.random() - .5) * .12,
    vy: 2 + Math.random() * 3, vx: (Math.random() - .5) * 2, a: 1,
  }));
  (function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = 0;
    p.forEach(q => {
      q.y += q.vy; q.x += q.vx; q.r += q.dr;
      if (q.y > canvas.height * .75) q.a -= .025;
      if (q.a <= 0) return; alive++;
      ctx.save(); ctx.globalAlpha = q.a;
      ctx.translate(q.x, q.y); ctx.rotate(q.r);
      ctx.fillStyle = q.c; ctx.fillRect(-q.w / 2, -q.h / 2, q.w, q.h);
      ctx.restore();
    });
    if (alive) requestAnimationFrame(draw);
    else ctx.clearRect(0, 0, canvas.width, canvas.height);
  })();
}

// ── Main App ───────────────────────────────────
createApp({
  components: { 'lottie-anim': LottieAnim },

  setup() {
    const tab = ref('home');
    const gifts = ref([]);
    const selected = ref(null);
    const recipient = ref('');
    const paying = ref(false);
    const errMsg = ref('');
    const toast = ref('');
    const isAdmin = ref(false);
    const showAdmin = ref(false);
    const aTab = ref('gifts');
    const adminGifts = ref([]);
    const adminOrders = ref([]);
    const myOrders = ref([]);
    const user = ref(ME);
    const form = reactive({ show: false, id: null, emoji: '', display_name: '', date_label: '', gift_tg_id: '', base_stars: 50, commission: 10 });

    let toastTimer = null;
    const showToast = msg => {
      toast.value = msg;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { toast.value = ''; }, 2800);
    };

    const getGiftImg = anim => IMG_MAP[anim] || null;

    // ── Style Helpers ──────────────────────────
    const sheetGlowStyle = computed(() => selected.value
      ? { filter: `drop-shadow(0 0 30px ${gc(selected.value.emoji).glow})` }
      : {}
    );
    const sheetRingStyle = (n) => {
      if (!selected.value) return {};
      const c = gc(selected.value.emoji);
      return n === 1
        ? { borderTopColor: c.c1, borderRightColor: c.c1 + '44', borderBottomColor: 'transparent', borderLeftColor: 'transparent', border: '1.5px solid' }
        : { borderBottomColor: c.c2, borderLeftColor: c.c2 + '44', borderTopColor: 'transparent', borderRightColor: 'transparent', border: '1.5px solid' };
    };

    // ── Load Gifts ─────────────────────────────
    const loadGifts = async () => {
      try {
        const data = await fetch('/api/gifts', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        gifts.value = data;
        // Preload all Lottie animations immediately
        data.forEach(g => g.animation && preloadAnim(g.animation));
      } catch (e) { console.error('loadGifts error:', e); }
    };

    // ── Load History ───────────────────────────
    const loadHistory = async () => {
      if (!ME) return;
      try {
        const d = await api('/api/my-orders').then(r => r.json());
        myOrders.value = Array.isArray(d) ? d : [];
      } catch {}
    };

    // ── Sheet Controls ─────────────────────────
    const openSheet = g => {
      selected.value = g; recipient.value = ''; errMsg.value = '';
      if (tg) { tg.BackButton.show(); tg.BackButton.onClick(closeSheet); }
    };
    const closeSheet = () => {
      selected.value = null;
      if (tg) tg.BackButton.hide();
    };

    const isNumeric = val => /^\d+$/.test((val || '').trim());

    // ── Contact Picker & Me Button ───────────
    const setRecipientMe = () => {
      if (ME && ME.username) {
        recipient.value = '@' + ME.username;
      } else if (ME && ME.id) {
        recipient.value = String(ME.id);
      } else {
        showToast('Open in Telegram to autofill');
      }
    };

    const pickContact = () => {
      if (!tg) {
        const inp = prompt('Enter Telegram Username (@username) or User ID (e.g. 6588631008):');
        if (inp) recipient.value = inp.trim();
        return;
      }

      // Priority 1: Telegram WebApp requestContact API
      if (typeof tg.requestContact === 'function') {
        try {
          tg.requestContact((ok, res) => {
            if (ok && res) {
              const c = res.responseUnsafe?.contact || res;
              const val = c.username ? `@${c.username}` : (c.user_id ? `${c.user_id}` : (c.phone_number || ''));
              if (val) {
                recipient.value = val;
                showToast(`Selected: ${val}`);
              }
            }
          });
          return;
        } catch (e) {
          console.warn('requestContact failed:', e);
        }
      }

      // Priority 2: Telegram requestUser API
      if (typeof tg.requestUser === 'function') {
        try {
          tg.requestUser({ bot_is_member: false }, (ok, u) => {
            if (ok && u) {
              const val = u.username ? `@${u.username}` : `${u.id}`;
              recipient.value = val;
              showToast(`Selected: ${val}`);
            }
          });
          return;
        } catch (e) {
          console.warn('requestUser failed:', e);
        }
      }

      // Fallback
      const inp = prompt('Enter Telegram Username (@username) or User ID (e.g. 6588631008):');
      if (inp) recipient.value = inp.trim();
    };

    // ── Pay via tg.openInvoice ─────────────────
    const pay = async () => {
      let rcpt = recipient.value.trim();
      if (!rcpt) { errMsg.value = 'Enter a recipient username or User ID'; return; }
      if (!ME) { showToast('Open in Telegram to purchase'); return; }

      // Format recipient ID: numeric ID (e.g. 6588631008) vs @username
      if (/^\d+$/.test(rcpt)) {
        rcpt = rcpt;
      } else {
        rcpt = '@' + rcpt.replace(/^@/, '');
      }

      paying.value = true; errMsg.value = '';
      try {
        const r = await api('/api/invoice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ recipient_id: rcpt, gift_id: selected.value.id }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Failed');

        if (tg?.openInvoice) {
          tg.openInvoice(data.link, status => {
            paying.value = false;
            if (status === 'paid') {
              closeSheet();
              confetti();
              showToast('✅ Gift purchased successfully!');
              loadHistory();
            } else if (status === 'cancelled') {
              errMsg.value = 'Payment cancelled';
            } else if (status === 'failed') {
              errMsg.value = 'Payment failed. Try again.';
            }
          });
        } else {
          window.open(data.link, '_blank');
          paying.value = false;
          closeSheet();
          showToast('✅ Invoice created — pay in Telegram');
        }
      } catch (e) {
        paying.value = false;
        errMsg.value = e.message;
      }
    };

    // ── Admin CRUD ─────────────────────────────
    const loadAdminGifts = async () => {
      try {
        const d = await api('/api/admin/gifts').then(r => r.json());
        adminGifts.value = d;
      } catch {}
    };
    const loadAdminOrders = async () => {
      try {
        const d = await api('/api/admin/orders').then(r => r.json());
        adminOrders.value = d;
      } catch {}
    };
    const openAddForm = () => {
      Object.assign(form, { show: true, id: null, emoji: '🧸', display_name: '', date_label: '08/06/26', gift_tg_id: '', base_stars: 50, commission: 10, animation: '' });
      showAdmin.value = true;
      aTab.value = 'gifts';
    };
    const editGift = g => {
      Object.assign(form, { show: true, id: g.id, emoji: g.emoji, display_name: g.display_name || '', date_label: g.date_label, gift_tg_id: g.gift_tg_id, base_stars: g.base_stars, commission: g.commission, animation: g.animation || '' });
    };
    const saveGift = async () => {
      const body = { emoji: form.emoji, display_name: form.display_name, date_label: form.date_label, gift_tg_id: form.gift_tg_id, base_stars: form.base_stars, commission: form.commission, animation: form.animation };
      const url = form.id ? `/api/admin/gifts/${form.id}` : '/api/admin/gifts';
      const method = form.id ? 'PATCH' : 'POST';
      const r = await api(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (r.ok) { form.show = false; loadAdminGifts(); loadGifts(); showToast('✅ Saved'); }
      else showToast('❌ Save failed');
    };
    const toggleActive = async g => {
      await api(`/api/admin/gifts/${g.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active: g.active ? 0 : 1 }) });
      loadAdminGifts(); loadGifts();
    };
    const delGift = async id => {
      if (!confirm('Delete this gift?')) return;
      await api(`/api/admin/gifts/${id}`, { method: 'DELETE' });
      showToast('🗑️ Deleted'); loadAdminGifts(); loadGifts();
    };

    // ── Boot ───────────────────────────────────
    onMounted(async () => {
      try {
        const cfg = await fetch('/api/config', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (ME && ME.id === cfg.admin_id) isAdmin.value = true;
      } catch {}

      await loadGifts();
      if (ME) loadHistory();

      if (tg) {
        tg.BackButton.onClick(() => {
          if (showAdmin.value) showAdmin.value = false;
          else if (selected.value) closeSheet();
          else if (tab.value !== 'home') tab.value = 'home';
          else tg.BackButton.hide();
        });
      }
    });

    const scrollToGifts = () => {
      const el = document.querySelector('.gifts-grid');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    };

    const openRealUserContact = () => {
      if (tg?.openTelegramLink) {
        tg.openTelegramLink('https://t.me/xusanboyman200');
      } else {
        window.open('https://t.me/xusanboyman200', '_blank');
      }
    };

    return {
      tab, gifts, selected, recipient, paying, errMsg, toast,
      isAdmin, showAdmin, aTab, adminGifts, adminOrders, myOrders, user, form,
      sheetGlowStyle, sheetRingStyle, getGiftImg, scrollToGifts, openRealUserContact, isNumeric,
      openSheet, closeSheet, pickContact, setRecipientMe, pay, loadHistory,
      loadAdminGifts, loadAdminOrders, openAddForm, editGift, saveGift, toggleActive, delGift,
    };
  },
}).mount('#app');
