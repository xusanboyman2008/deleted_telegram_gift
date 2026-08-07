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

// ── Image & Animated GIF Fallback mapping ───────
const IMG_MAP = {};

// ── Fallback mapping (tries .json, if fails or incompatible uses .png) ──
const FALLBACK_PNG_MAP = {
  'pink_bear.json': 'assets/rose_bear.png',
  'worker_bear.json': 'assets/worker_bear.png',
  'football_bear.json': 'assets/football_bear.png',
  'bunny_bear.json': 'assets/bunny_basket.png',
  'joker_bear.json': 'assets/balloon_bear.png',
  'santa_bear.json': 'assets/santa_teddy.png',
  'gnome_bear.json': 'assets/gnome_bear.png',
  'hear.json': 'assets/iloveu_bear.png',
  'green_tree.json': 'assets/green_tree.png',
  'hug_bear.json': 'assets/hug_bear.png',
  'hugging_bear.json': 'assets/hug_bear.png',
};
const getFallbackPng = anim => FALLBACK_PNG_MAP[anim] || null;

// ── Lottie Dash Fix (TGS uses "n", lottie-web expects "nm") ──
function fixLottieDashes(obj) {
  if (!obj || typeof obj !== 'object') return;
  if (Array.isArray(obj)) { obj.forEach(fixLottieDashes); return; }
  if ((obj.ty === 'st' || obj.ty === 'gs') && Array.isArray(obj.d)) {
    obj.d.forEach(d => { if (d.n !== undefined && d.nm === undefined) d.nm = d.n; });
  }
  for (const k in obj) if (obj.hasOwnProperty(k)) fixLottieDashes(obj[k]);
}

// ── Detect complex files that need canvas renderer ──
// Files with many gradient strokes/fills or mattes break SVG renderer
const CANVAS_RENDERER_FILES = new Set([
  'pink_bear.json',
  'football_bear.json',
  'worker_bear.json',
]);
function getRenderer(filename) {
  return CANVAS_RENDERER_FILES.has(filename) ? 'canvas' : 'svg';
}

// ── Lottie Cache ───────────────────────────────
const animCache = {};
async function preloadAnim(filename) {
  if (!filename) return null;
  if (animCache[filename]) return animCache[filename];
  try {
    const r = await fetch(`assets/${filename}`, { headers: { 'ngrok-skip-browser-warning': '69420' } });
    if (!r.ok) return null;
    const data = await r.json();
    fixLottieDashes(data);
    animCache[filename] = data;
    return data;
  } catch (e) {
    console.error('Failed to fetch anim:', filename, e);
    return null;
  }
}

// ── Lottie Component with Automatic PNG Fallback ──
const LottieAnim = {
  props: { filename: String, fallbackImg: String },
  setup(props) {
    const el = ref(null);
    const failed = ref(false);
    let inst = null;
    let isPlaying = false;
    let failTimer = null;

    const destroy = () => {
      if (failTimer) { clearTimeout(failTimer); failTimer = null; }
      if (inst) {
        try { inst.destroy(); } catch {}
        inst = null;
      }
    };

    const playAnim = () => {
      if (inst) {
        try {
          isPlaying = true;
          inst.goToAndPlay(0, true);
        } catch {}
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
      const renderer = getRenderer(props.filename);
      try {
        inst = lottie.loadAnimation({
          container: el.value,
          renderer: renderer,
          loop: false,
          autoplay: true,
          animationData: JSON.parse(JSON.stringify(data)),
          rendererSettings: renderer === 'canvas'
            ? { clearCanvas: true, progressiveLoad: true }
            : {},
        });
        isPlaying = true;
        let rendered = false;
        inst.addEventListener('enterFrame', () => {
          rendered = true;
        });
        inst.addEventListener('complete', () => {
          isPlaying = false;
        });
        inst.addEventListener('error', () => {
          console.warn('Lottie load error event for:', props.filename);
          failed.value = true;
        });
        inst.addEventListener('data_failed', () => {
          console.warn('Lottie data_failed for:', props.filename);
          failed.value = true;
        });
        inst.addEventListener('DOMLoaded', () => {
          rendered = true;
        });
        // Safety timeout: if no frame rendered within 3s, fall back to PNG
        failTimer = setTimeout(() => {
          if (!rendered && !failed.value) {
            console.warn('Lottie render timeout for:', props.filename, '— falling back to PNG');
            failed.value = true;
            destroy();
          }
        }, 3000);
      } catch (e) {
        console.warn('Lottie render error:', props.filename, e);
        failed.value = true;
      }
    };

    onMounted(load);
    watch(() => props.filename, load);
    Vue.onUnmounted(destroy);
    return { el, failed, playAnim };
  },
  template: `
    <div
      class="lottie-box-wrap"
      style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;"
      @mouseenter="playAnim"
      @touchstart.passive="playAnim"
    >
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
    const giftMsg = ref('');
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
      selected.value = g; recipient.value = ''; giftMsg.value = ''; errMsg.value = '';
      if (tg) { tg.BackButton.show(); tg.BackButton.onClick(closeSheet); }
    };
    const closeSheet = () => {
      selected.value = null;
      if (tg) tg.BackButton.hide();
    };

    const isNumeric = val => /^\d+$/.test((val || '').trim());

    // ── Live Recipient Verification & Userbot State ──────────
    const checkingUser = ref(false);
    const verifiedUser = ref(null);
    const userCheckError = ref(null);
    const userbotAccounts = ref([]);
    const selectedSender = ref('bot');
    const selectedUserbot = ref(1);
    let recipientTimer = null;

    const loadUserbotAccounts = async () => {
      try {
        const res = await fetch('/api/userbot-accounts', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        userbotAccounts.value = Array.isArray(res) ? res : [];
        if (userbotAccounts.value.length > 0) {
          selectedUserbot.value = userbotAccounts.value[0].id;
        }
      } catch (e) {
        console.warn('Failed to load userbot accounts:', e);
      }
    };

    const checkRecipientNow = async () => {
      const val = recipient.value.trim();
      if (!val) {
        verifiedUser.value = null;
        userCheckError.value = null;
        checkingUser.value = false;
        return;
      }
      checkingUser.value = true;
      userCheckError.value = null;
      try {
        const res = await fetch(`/api/check-user?query=${encodeURIComponent(val)}`, { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        checkingUser.value = false;
        if (res && res.exists) {
          verifiedUser.value = res;
          userCheckError.value = null;
        } else {
          verifiedUser.value = null;
          userCheckError.value = (res && res.error) || 'User does not exist on Telegram';
        }
      } catch (e) {
        checkingUser.value = false;
        verifiedUser.value = null;
        userCheckError.value = 'User verification error';
      }
    };

    const onRecipientInput = () => {
      verifiedUser.value = null;
      userCheckError.value = null;
      clearTimeout(recipientTimer);
      if (!recipient.value.trim()) {
        checkingUser.value = false;
        return;
      }
      checkingUser.value = true;
      recipientTimer = setTimeout(checkRecipientNow, 600);
    };

    const clearRecipient = () => {
      recipient.value = '';
      verifiedUser.value = null;
      userCheckError.value = null;
      checkingUser.value = false;
      clearTimeout(recipientTimer);
    };

    // ── Contact Picker & Me Button ───────────
    const setRecipientMe = () => {
      if (ME && ME.username) {
        recipient.value = '@' + ME.username;
      } else if (ME && ME.id) {
        recipient.value = String(ME.id);
      } else {
        showToast('Open in Telegram to autofill');
      }
      checkRecipientNow();
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
          body: JSON.stringify({
            recipient_id: rcpt,
            gift_id: selected.value.id,
            gift_text: giftMsg.value.trim() || null,
            sender_type: selectedSender.value,
            userbot_id: selectedSender.value === 'userbot' ? selectedUserbot.value : null
          }),
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

    // ── Admin Userbot CRUD ──────────────────────
    const adminUserbots = ref([]);
    const ubForm = reactive({
      show: false,
      id: null,
      first_name: '',
      last_name: '',
      username: '',
      bio: '',
      photo: '',
      phone: '',
      session_string: '',
      active: true,
    });

    const loadAdminUserbots = async () => {
      try {
        const d = await api('/api/admin/userbots').then(r => r.json());
        adminUserbots.value = Array.isArray(d) ? d : [];
      } catch (e) {
        console.error('loadAdminUserbots error:', e);
      }
    };

    const openAddUserbot = () => {
      Object.assign(ubForm, {
        show: true,
        id: null,
        first_name: '',
        last_name: '',
        username: '',
        bio: '',
        photo: '',
        phone: '',
        session_string: '',
        active: true,
      });
    };

    const editUserbot = ub => {
      Object.assign(ubForm, {
        show: true,
        id: ub.id,
        first_name: ub.first_name || '',
        last_name: ub.last_name || '',
        username: ub.username || '',
        bio: ub.bio || ub.description || '',
        photo: ub.photo || '',
        phone: ub.phone || '',
        session_string: ub.session_string || '',
        active: ub.active !== false,
      });
    };

    const saveUserbot = async () => {
      const body = {
        first_name: ubForm.first_name,
        last_name: ubForm.last_name,
        username: ubForm.username,
        bio: ubForm.bio,
        photo: ubForm.photo,
        phone: ubForm.phone,
        session_string: ubForm.session_string,
        active: ubForm.active,
      };
      const url = ubForm.id ? `/api/admin/userbots/${ubForm.id}` : '/api/admin/userbots';
      const method = ubForm.id ? 'PATCH' : 'POST';
      const r = await api(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (r.ok) {
        ubForm.show = false;
        loadAdminUserbots();
        loadUserbotAccounts();
        showToast('✅ Userbot saved & profile synced live!');
      } else {
        showToast('❌ Userbot Save Failed');
      }
    };

    // ── Admin Userbot Direct Messaging ─────────────
    const ubMsgForm = reactive({
      show: false,
      account_id: null,
      account_name: '',
      recipient: '',
      message: '',
      sending: false,
    });

    const openUserbotMsg = (ub) => {
      ubMsgForm.account_id = ub.id;
      ubMsgForm.account_name = ub.first_name ? `${ub.first_name} (@${ub.username || 'no_user'})` : `Account #${ub.id}`;
      ubMsgForm.recipient = '';
      ubMsgForm.message = '';
      ubMsgForm.sending = false;
      ubMsgForm.show = true;
    };

    const sendUserbotMsg = async () => {
      const rec = ubMsgForm.recipient.trim();
      const msg = ubMsgForm.message.trim();
      if (!rec) { showToast('Enter recipient username or Telegram ID'); return; }
      if (!msg) { showToast('Enter message text to send'); return; }

      ubMsgForm.sending = true;
      try {
        const r = await api('/api/admin/userbot/send-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            account_id: ubMsgForm.account_id,
            recipient: rec,
            message: msg,
          }),
        });
        const data = await r.json();
        ubMsgForm.sending = false;
        if (r.ok) {
          ubMsgForm.show = false;
          showToast(`⚡ Message sent via Userbot #${ubMsgForm.account_id}!`);
        } else {
          showToast(`❌ ${data.detail || 'Failed to send message'}`);
        }
      } catch (e) {
        ubMsgForm.sending = false;
        showToast(`❌ ${e.message}`);
      }
    };

    // ── Boot ───────────────────────────────────
    onMounted(async () => {
      try {
        const cfg = await fetch('/api/config', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (ME && ME.id === cfg.admin_id) isAdmin.value = true;
      } catch {}

      await loadGifts();
      await loadUserbotAccounts();
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
      tab, gifts, selected, recipient, giftMsg, paying, errMsg, toast,
      isAdmin, showAdmin, aTab, adminGifts, adminOrders, adminUserbots, ubForm, ubMsgForm, myOrders, user, form,
      checkingUser, verifiedUser, userCheckError, userbotAccounts, selectedSender, selectedUserbot,
      sheetGlowStyle, sheetRingStyle, getGiftImg, getFallbackPng, scrollToGifts, openRealUserContact, isNumeric,
      openSheet, closeSheet, pickContact, setRecipientMe, pay, loadHistory,
      onRecipientInput, checkRecipientNow, clearRecipient,
      loadAdminGifts, loadAdminOrders, loadAdminUserbots, openAddUserbot, editUserbot, saveUserbot, openAddForm, editGift, saveGift, toggleActive, delGift,
      openUserbotMsg, sendUserbotMsg,
    };
  },
}).mount('#app');
