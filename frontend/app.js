/* ═══════════════════════════════════════════════
   TgGifts — Vue 3 App Logic with i18n & Phone Auth
   ═══════════════════════════════════════════════ */

if (typeof window !== 'undefined' && (!window.crypto || !window.crypto.randomUUID)) {
  if (!window.crypto) window.crypto = {};
  window.crypto.randomUUID = function() {
    return '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, function(c) {
      var r = (window.crypto && window.crypto.getRandomValues ? window.crypto.getRandomValues(new Uint8Array(1))[0] : Math.floor(Math.random() * 256));
      return (c ^ (r & (15 >> (c / 4)))).toString(16);
    });
  };
}

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

// ── i18n Translations Dictionary ───────────────
const I18N = {
  en: {
    gifts: "Gifts",
    history: "History",
    settings: "Settings",
    chooseLanguage: "Language",
    senderType: "Sender",
    officialBot: "Official Bot",
    officialBotSub: "Official Bot",
    userbotSender: "Userbot",
    userbotSenderSub: "Userbot",
    myAccountSender: "My Account",
    myAccountSenderSub: "Personal Account (50⭐ gift + 0⭐ bot fee)",
    connectMyAccount: "Connect Account",
    myAccountConnected: "Connected",
    disconnectAccount: "Disconnect",
    phoneAuthTitle: "Connect Telegram",
    phoneLabel: "Phone Number",
    phonePlaceholder: "+998901234567",
    sendCodeBtn: "Send Code",
    enterCodeTitle: "Enter Code",
    codeLabel: "Code",
    codePlaceholder: "12345",
    passwordLabel: "2FA Password",
    confirmCodeBtn: "Confirm",
    supportContact: "Support",
    supportBtn: "💬 @xusanboyman200",
    somethingWentWrong: "Error! Support: @xusanboyman200",
    adminPanel: "Admin Panel",
    pricingSettings: "Pricing (⭐)",
    botPriceLabel: "Bot Stars",
    userbotPriceLabel: "Userbot Stars",
    myAccountPriceLabel: "My Account Stars",
    savePricingBtn: "Save Prices",
    payBtn: "Pay",
    buyDirectBtn: "Buy Direct",
    chooseSender: "Choose Sender...",
    chooseSenderSub: "Tap to select official bot or userbot",
    recipientInputPlaceholder: "Username or ID",
    giftMsgPlaceholder: "Message...",
    userNotConnectedWarning: "Please connect account or pick another sender.",
    userbots: "Userbots",
    userAccounts: "Users",
    systemUserbots: "System Userbots",
    gift_bunny_basket: "Bunny Basket",
    gift_balloon_bear: "Balloon Bear",
    gift_rose_bear: "Rose Bear",
    gift_worker_bear: "Worker Bear",
    gift_football_bear: "Football Bear",
    gift_santa_teddy: "Santa Teddy",
    gift_gnome_bear: "Gnome Bear",
    gift_i_love_u: "I Love U",
    gift_christmas_tree: "Christmas Tree",
    gift_hug_bear: "Hug Bear",
    chats: "Chats",
    botPanel: "Bot Panel",
  },
  uz: {
    gifts: "Sovg'alar",
    history: "Tarix",
    settings: "Sozlamalar",
    chooseLanguage: "Til",
    senderType: "Yuboruvchi",
    officialBot: "Rasmiy Bot",
    officialBotSub: "Rasmiy Bot",
    userbotSender: "Userbot",
    userbotSenderSub: "Userbot",
    myAccountSender: "O'z hisobim",
    myAccountSenderSub: "Shaxsiy hisob (50⭐ sovg'a + 0⭐ komissiya)",
    connectMyAccount: "Hisobni ulash",
    myAccountConnected: "Ulangan",
    disconnectAccount: "Uzish",
    phoneAuthTitle: "Telegram ulash",
    phoneLabel: "Telefon raqam",
    phonePlaceholder: "+998901234567",
    sendCodeBtn: "Kodni yuborish",
    enterCodeTitle: "Telegram kodi",
    codeLabel: "Telegram kodi",
    codePlaceholder: "12345",
    passwordLabel: "2FA Parol",
    confirmCodeBtn: "Tasdiqlash",
    supportContact: "Yordam",
    supportBtn: "💬 @xusanboyman200",
    somethingWentWrong: "Xato! Admin: @xusanboyman200",
    adminPanel: "Admin Panel",
    pricingSettings: "Narxlar (⭐)",
    botPriceLabel: "Bot Stars",
    userbotPriceLabel: "Userbot Stars",
    myAccountPriceLabel: "Hisobim Stars",
    savePricingBtn: "Saqlash",
    payBtn: "To'lash",
    buyDirectBtn: "Sotib olish",
    chooseSender: "Yuboruvchini tanlang...",
    chooseSenderSub: "Tanlash uchun bosing",
    recipientInputPlaceholder: "Username yoki ID",
    giftMsgPlaceholder: "Xabar...",
    userNotConnectedWarning: "Hisobni ulang yoki boshqa yuboruvchini tanlang.",
    userbots: "Userbotlar",
    userAccounts: "Foydalanuvchilar",
    systemUserbots: "Tizim Userbotlari",
    gift_bunny_basket: "Quyon savatchasi",
    gift_balloon_bear: "Sharli ayiqcha",
    gift_rose_bear: "Atirgul ayiqcha",
    gift_worker_bear: "Ishchi ayiqcha",
    gift_football_bear: "Futbolchi ayiqcha",
    gift_santa_teddy: "Qorbobo ayiqcha",
    gift_gnome_bear: "Gnom ayiqcha",
    gift_i_love_u: "Sevaman ❤️",
    gift_christmas_tree: "Rojdestvo daraxti",
    gift_hug_bear: "Quchoq ayiqcha",
    chats: "Suhbatlar",
    botPanel: "Bot Paneli",
  },
  ru: {
    gifts: "Подарки",
    history: "История",
    settings: "Настройки",
    chooseLanguage: "Язык",
    senderType: "Отправитель",
    officialBot: "Официальный Бот",
    officialBotSub: "Официальный Бот",
    userbotSender: "Юзербот",
    userbotSenderSub: "Юзербот",
    myAccountSender: "Мой аккаунт",
    myAccountSenderSub: "Свой аккаунт (50⭐ подарок + 0⭐ комиссия)",
    connectMyAccount: "Подключить аккаунт",
    myAccountConnected: "Подключен",
    disconnectAccount: "Отключить",
    phoneAuthTitle: "Подключение Telegram",
    phoneLabel: "Номер телефона",
    phonePlaceholder: "+998901234567",
    sendCodeBtn: "Отправить код",
    enterCodeTitle: "Введите код",
    codeLabel: "Код Telegram",
    codePlaceholder: "12345",
    passwordLabel: "2FA Пароль",
    confirmCodeBtn: "Подтвердить",
    supportContact: "Поддержка",
    supportBtn: "💬 @xusanboyman200",
    somethingWentWrong: "Ошибка! Поддержка: @xusanboyman200",
    adminPanel: "Панель",
    pricingSettings: "Цены (⭐)",
    botPriceLabel: "Цена Бот (Stars)",
    userbotPriceLabel: "Цена Юзербот (Stars)",
    myAccountPriceLabel: "Цена Аккаунт (Stars)",
    savePricingBtn: "Сохранить",
    payBtn: "Оплатить",
    buyDirectBtn: "Купить напрямую",
    chooseSender: "Выберите отправителя...",
    chooseSenderSub: "Нажмите для выбора бота или юзербота",
    recipientInputPlaceholder: "Username или ID",
    giftMsgPlaceholder: "Сообщение...",
    userNotConnectedWarning: "Подключите аккаунт или выберите другого отправителя.",
    userbots: "Юзерботы",
    userAccounts: "Пользователи",
    systemUserbots: "Системные Юзерботы",
    gift_bunny_basket: "Зайчик с корзинкой",
    gift_balloon_bear: "Мишка с шариком",
    gift_rose_bear: "Мишка с розами",
    gift_worker_bear: "Мишка-строитель",
    gift_football_bear: "Мишка-футболист",
    gift_santa_teddy: "Мишка Санта",
    gift_gnome_bear: "Мишка-гном",
    gift_i_love_u: "Люблю тебя ❤️",
    gift_christmas_tree: "Рождественская ёлка",
    gift_hug_bear: "Мишка-обнимашка",
    chats: "Чаты",
    botPanel: "Панель Бота",
  }
};

// ── Gift Name i18n mapping ─────────────────────
const GIFT_NAME_KEYS = {
  'Bunny Basket': 'gift_bunny_basket',
  'Balloon Bear': 'gift_balloon_bear',
  'Rose Bear': 'gift_rose_bear',
  'Worker Bear': 'gift_worker_bear',
  'Football Bear': 'gift_football_bear',
  'Santa Teddy': 'gift_santa_teddy',
  'Gnome Bear': 'gift_gnome_bear',
  'I Love U': 'gift_i_love_u',
  'Christmas Tree': 'gift_christmas_tree',
  'Hug Bear': 'gift_hug_bear',
};

// ── Image & Fallback mapping ───────────────────
const IMG_MAP = {};
const getFallbackPng = anim => null;

// ── Lottie Dash Fix ───────────────────────────
function fixLottieDashes(obj) {
  if (!obj || typeof obj !== 'object') return;
  if (Array.isArray(obj)) { obj.forEach(fixLottieDashes); return; }
  if ((obj.ty === 'st' || obj.ty === 'gs') && Array.isArray(obj.d)) {
    obj.d.forEach(d => { if (d.n !== undefined && d.nm === undefined) d.nm = d.n; });
  }
  for (const k in obj) if (obj.hasOwnProperty(k)) fixLottieDashes(obj[k]);
}

function getRenderer(filename) {
  return 'svg';
}

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

const LottieAnim = {
  props: { filename: String, fallbackImg: String },
  setup(props) {
    const el = ref(null);
    const failed = ref(false);
    let inst = null;
    const pageLoading = Vue.inject('pageLoading', ref(false));

    const destroy = () => {
      if (inst) {
        try { inst.destroy(); } catch {}
        inst = null;
      }
    };

    const playOnce = () => {
      if (inst) {
        try {
          inst.goToAndPlay(0, true);
        } catch {}
      }
    };

    const init = async () => {
      destroy();
      failed.value = false;
      if (!props.filename) return;

      const data = await preloadAnim(props.filename);
      if (!data) { failed.value = true; return; }

      await nextTick();
      if (!el.value) return;

      try {
        inst = lottie.loadAnimation({
          container: el.value,
          renderer: 'svg',
          loop: false,
          autoplay: !pageLoading.value,
          animationData: data,
        });
      } catch (e) {
        console.error('Lottie setup error:', e);
        failed.value = true;
      }
    };

    onMounted(init);
    watch(() => props.filename, init);
    watch(pageLoading, (loading) => {
      if (!loading && inst) {
        playOnce();
      }
    });

    const onHover = () => {
      playOnce();
    };

    return () => {
      if (failed.value && props.fallbackImg) {
        return Vue.h('img', { src: props.fallbackImg, class: 'gift-png-fallback' });
      }
      return Vue.h('div', {
        ref: el,
        class: 'lottie-box',
        onMouseenter: onHover,
        onTouchstart: onHover,
      });
    };
  },
};

const COLOR_MAP = {
  '🧸': { c1: '#FF9A9E', c2: '#FECFEF', glow: 'rgba(255, 154, 158, 0.4)' },
  '🎈': { c1: '#A18CD1', c2: '#FBC2EB', glow: 'rgba(161, 140, 209, 0.4)' },
  '🌹': { c1: '#FF758C', c2: '#FF7EB3', glow: 'rgba(255, 117, 140, 0.4)' },
  '👷': { c1: '#F6D365', c2: '#FDA085', glow: 'rgba(246, 211, 101, 0.4)' },
  '⚽': { c1: '#84FAB0', c2: '#8FD3F4', glow: 'rgba(132, 250, 176, 0.4)' },
  '🎅': { c1: '#FF4E50', c2: '#F9D423', glow: 'rgba(255, 78, 80, 0.4)' },
  '🧙': { c1: '#43E97B', c2: '#38F9D7', glow: 'rgba(67, 233, 123, 0.4)' },
  '❤️': { c1: '#FF0844', c2: '#FFB199', glow: 'rgba(255, 8, 68, 0.4)' },
  '🎄': { c1: '#11998E', c2: '#38EF7D', glow: 'rgba(17, 153, 142, 0.4)' },
};
const gc = emoji => COLOR_MAP[emoji] || { c1: '#7B61FF', c2: '#5A3FD4', glow: 'rgba(123, 97, 255, 0.4)' };

function confetti() {
  const canvas = document.getElementById('confetti');
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

const DEFAULT_GIFTS_SEED = [
  { id: 1, emoji: "🧸", display_name: "Bunny Basket", date_label: "03/08/26", gift_tg_id: "5866352046986232958", base_stars: 50, commission: 10, active: 1, animation: "bunny_bear.json" },
  { id: 2, emoji: "🧸", display_name: "Balloon Bear", date_label: "03/17/26", gift_tg_id: "5893356958802511476", base_stars: 50, commission: 10, active: 1, animation: "joker_bear.json" },
  { id: 3, emoji: "🧸", display_name: "Rose Bear", date_label: "02/14/26", gift_tg_id: "5801108895304779062", base_stars: 50, commission: 10, active: 1, animation: "pink_bear.json" },
  { id: 4, emoji: "🧸", display_name: "Worker Bear", date_label: "04/01/26", gift_tg_id: "5935895822435615975", base_stars: 50, commission: 10, active: 1, animation: "worker_bear.json" },
  { id: 5, emoji: "🧸", display_name: "Football Bear", date_label: "05/01/26", gift_tg_id: "6026193266406327981", base_stars: 50, commission: 10, active: 1, animation: "football_bear.json" },
  { id: 6, emoji: "🧸", display_name: "Santa Teddy", date_label: "12/25/25", gift_tg_id: "5922558454332916696", base_stars: 50, commission: 10, active: 1, animation: "santa_bear.json" },
  { id: 7, emoji: "🧸", display_name: "Gnome Bear", date_label: "07/20/26", gift_tg_id: "5974210632977745012", base_stars: 50, commission: 10, active: 1, animation: "gnome_bear.json" },
  { id: 8, emoji: "💖", display_name: "I Love U", date_label: "02/14/26", gift_tg_id: "5800655655995968839", base_stars: 50, commission: 10, active: 1, animation: "hear.json" },
  { id: 9, emoji: "🎄", display_name: "Christmas Tree", date_label: "12/31/25", gift_tg_id: "5956217000635139069", base_stars: 50, commission: 10, active: 1, animation: "green_tree.json" },
  { id: 10, emoji: "🧸", display_name: "Hug Bear", date_label: "05/10/26", gift_tg_id: "5800655655995968830", base_stars: 50, commission: 10, active: 1, animation: "hug_bear.json" }
];

// ── Main App ───────────────────────────────────
createApp({
  components: { 'lottie-anim': LottieAnim },

  setup() {
    const pageLoading = ref(true);
    Vue.provide('pageLoading', pageLoading);
    const tab = ref('home');
    const gifts = ref(DEFAULT_GIFTS_SEED);
    const selected = ref(null);
    const hoveredGiftId = ref(null);
    const recipient = ref('');
    const giftMsg = ref('');
    const paying = ref(false);
    const errMsg = ref('');
    const toast = ref('');

    let toastTimer = null;
    const showToast = msg => {
      toast.value = msg;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { toast.value = ''; }, 3200);
    };

    const isAdmin = ref(true);
    const showAdmin = ref(false);
    const aTab = ref('gifts');
    const adminGifts = ref([]);
    const adminOrders = ref([]);
    const myOrders = ref([]);
    const user = ref(ME);

    // ── Bot Panel State ──
    const botMenuTab = ref('managed');
    const botPanelUsers = ref([]);
    const broadcastShow = ref(false);
    const broadcastText = ref('');
    const botCommands = ref([]);


    // ── Language i18n State ─────────────────────
    const currentLang = ref(localStorage.getItem('user_lang') || 'en');
    const setLanguage = (lang) => {
      currentLang.value = lang;
      localStorage.setItem('user_lang', lang);
      showToast(lang === 'uz' ? "Til O'zbekchaga o'zgartirildi" : lang === 'ru' ? 'Язык изменен на русский' : 'Language set to English');
    };
    const t = (key) => I18N[currentLang.value]?.[key] || I18N['en']?.[key] || key;

    // ── Pricing Settings State ──────────────────
    const pricing = reactive({
      bot_stars: 53,
      userbot_stars: 55,
      myaccount_stars: 50,
    });

    const loadPricing = async () => {
      try {
        const p = await fetch('/api/pricing', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (p) Object.assign(pricing, p);
      } catch (e) {
        console.error('loadPricing error:', e);
      }
    };

    const savePricing = async () => {
      try {
        const r = await api('/api/admin/pricing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pricing),
        });
        if (r.ok) showToast('✅ Pricing settings saved!');
        else showToast('❌ Failed to save pricing');
      } catch (e) {
        showToast(`❌ ${e.message}`);
      }
    };

    // ── Userbot Accounts & Sender Selection State ─
    const userbotAccounts = ref([]);
    const selectedSender = ref(null); // 'bot', 'userbot', 'myaccount' (default nothing)
    const selectedUserbot = ref(null);

    const userAccount = computed(() => {
      if (!ME) return null;
      return userbotAccounts.value.find(acc => acc.owner_tg_id === ME.id && (acc.active === 1 || acc.active === true)) || null;
    });

    const publicUserbots = computed(() => {
      return userbotAccounts.value.filter(acc => !acc.owner_tg_id && (acc.active === 1 || acc.active === true));
    });

    const accountsLoading = ref(true);

    const loadUserbotAccounts = async () => {
      accountsLoading.value = true;
      try {
        const d = await api('/api/userbot-accounts').then(r => r.json());
        userbotAccounts.value = Array.isArray(d) ? d : [];
        if (publicUserbots.value.length > 0 && !selectedUserbot.value) {
          selectedUserbot.value = publicUserbots.value[0].id;
        }
      } catch (e) {
        console.error('loadUserbotAccounts error:', e);
      } finally {
        accountsLoading.value = false;
      }
    };

    // ── Chat State Module ───────────────────────
    const chatState = setupChatState(Vue, api, showToast, tg);
    watch(userbotAccounts, (accs) => {
      chatState.allAvailableAccounts.value = accs;
      if (!chatState.activeChatAccount.value && accs.length > 0) {
        const myAcc = accs.find(a => a.owner_tg_id === ME?.id);
        chatState.selectChatAccount(myAcc || accs[0]);
      }
    }, { immediate: true });

    // ── Phone Auth Modal State for "Use My Account" ─
    const phoneModal = reactive({
      show: false,
      step: 1, // 1: phone, 2: code, 3: password
      phone: '',
      code: '',
      password: '',
      requires_password: false,
      show_password: false,
      loading: false,
      error: '',
    });

    const openPhoneAuth = () => {
      Object.assign(phoneModal, {
        show: true,
        step: 1,
        phone: ME?.phone_number || '',
        code: '',
        password: '',
        requires_password: false,
        show_password: false,
        loading: false,
        error: '',
      });
    };

    const requestPhoneCode = async () => {
      if (phoneModal.loading) return;
      const cleanPhone = (phoneModal.phone || '').trim();
      if (!cleanPhone) {
        phoneModal.error = 'Please enter phone number (+998...)';
        return;
      }
      phoneModal.loading = true;
      phoneModal.error = '';
      try {
        const r = await api('/api/user/userbot/request-code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: cleanPhone }),
        });
        const data = await r.json();
        phoneModal.loading = false;
        if (data.success) {
          phoneModal.step = 2;
          phoneModal.error = '';
          showToast('📩 Verification code sent to Telegram!');
        } else {
          phoneModal.error = data.error || data.support_message || 'Failed to send verification code.';
        }
      } catch (e) {
        console.error('requestPhoneCode catch error:', e);
        phoneModal.loading = false;
        phoneModal.error = e.message || 'Something went wrong! Please contact support: @xusanboyman200';
      }
    };

    const resendPhoneCode = async () => {
      if (phoneModal.loading) return;
      const cleanPhone = (phoneModal.phone || '').trim();
      if (!cleanPhone) return;
      phoneModal.loading = true;
      phoneModal.error = '';
      try {
        const r = await api('/api/user/userbot/request-code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: cleanPhone, force: true }),
        });
        const data = await r.json();
        phoneModal.loading = false;
        if (data.success) {
          phoneModal.step = 2;
          phoneModal.code = '';
          phoneModal.error = '';
          showToast('📩 Fresh verification code sent to Telegram!');
        } else {
          phoneModal.error = data.error || data.support_message || 'Failed to resend code.';
        }
      } catch (e) {
        console.error('resendPhoneCode catch error:', e);
        phoneModal.loading = false;
        phoneModal.error = e.message || 'Something went wrong! Please contact support: @xusanboyman200';
      }
    };

    const confirmPhoneCode = async () => {
      if (phoneModal.loading) return;
      const cleanPhone = (phoneModal.phone || '').trim();
      const cleanCode = (phoneModal.code || '').trim();
      const cleanPass = (phoneModal.password || '').trim() || null;
      if (!cleanCode) {
        phoneModal.error = 'Please enter verification code';
        return;
      }
      phoneModal.loading = true;
      phoneModal.error = '';
      try {
        const r = await api('/api/user/userbot/confirm-code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            phone: cleanPhone,
            code: cleanCode,
            password: cleanPass,
          }),
        });
        const data = await r.json();
        phoneModal.loading = false;
        if (data.success) {
          phoneModal.show = false;
          showToast('🎉 Account connected successfully!');
          await loadUserbotAccounts();
          selectedSender.value = 'myaccount';
        } else if (data.requires_password) {
          phoneModal.requires_password = true;
          phoneModal.show_password = true;
          phoneModal.step = 3;
          phoneModal.error = data.error || '2FA Password is required for this account.';
        } else {
          // Close modal on insufficient stars and show a helpful toast instead
          const errMsg = data.error || data.support_message || 'Failed to confirm code.';
          if (errMsg.includes('Stars') || errMsg.includes('stars') || errMsg.includes('⭐')) {
            phoneModal.show = false;
            showToast('⚠️ ' + errMsg);
          } else {
            phoneModal.error = errMsg;
          }
        }
      } catch (e) {
        console.error('confirmPhoneCode catch error:', e);
        phoneModal.loading = false;
        phoneModal.error = e.message || 'Something went wrong! Please contact support: @xusanboyman200';
      }
    };

    const disconnectMyAccount = async () => {
      const myAcc = userAccount.value;
      if (!myAcc) return;
      const doDisconnect = async () => {
        try {
          const r = await api(`/api/user/userbot/account/${myAcc.id}`, { method: 'DELETE' });
          if (r.ok) {
            showToast('🔌 Account disconnected');
            await loadUserbotAccounts();
            selectedSender.value = 'bot';
          }
        } catch (e) {
          showToast('❌ Failed to disconnect account');
        }
      };
      if (window.Telegram?.WebApp?.showConfirm) {
        window.Telegram.WebApp.showConfirm('Disconnect your Telegram account?', ok => { if (ok) doDisconnect(); });
      } else {
        doDisconnect();
      }
    };

    // ── Form & Recipient Verification State ────────
    const form = reactive({ show: false, id: null, emoji: '', display_name: '', date_label: '', gift_tg_id: '', base_stars: 50, commission: 10 });
    const checkingUser = ref(false);
    const verifiedUser = ref(null);
    const userCheckError = ref('');
    let checkTimeout = null;

    const getGiftImg = anim => IMG_MAP[anim] || null;
    const giftName = (g) => {
      const key = GIFT_NAME_KEYS[g.display_name];
      if (key) return t(key);
      return g.display_name || g.emoji;
    };

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

    const loadGifts = async () => {
      try {
        const res = await fetch('/api/gifts', { headers: { 'ngrok-skip-browser-warning': '69420' } });
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          gifts.value = data;
        }
      } catch (e) { console.error('loadGifts error:', e); }
    };

    const loadHistory = async () => {
      if (!ME) return;
      try {
        const d = await api('/api/my-orders').then(r => r.json());
        myOrders.value = Array.isArray(d) ? d : [];
      } catch {}
    };

    const openSheet = g => {
      selected.value = g; recipient.value = ''; giftMsg.value = ''; errMsg.value = '';
      verifiedUser.value = null; userCheckError.value = '';
      selectedSender.value = null; showSenderDropdown.value = false;
      if (tg) { tg.BackButton.show(); tg.BackButton.onClick(closeSheet); }
    };
    const closeSheet = () => {
      selected.value = null;
      if (tg) tg.BackButton.hide();
    };

    const setRecipientMe = () => {
      if (!ME) { showToast('Open in Telegram to auto-fill username'); return; }
      recipient.value = ME.username ? `@${ME.username}` : `${ME.id}`;
      checkRecipientNow();
    };

    const isNumeric = str => /^\d+$/.test(str.trim());

    const checkRecipientNow = async () => {
      const q = recipient.value.trim();
      if (!q) { verifiedUser.value = null; userCheckError.value = ''; checkingUser.value = false; return; }
      checkingUser.value = true; userCheckError.value = ''; verifiedUser.value = null;

      const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('Search timeout')), 10000));
      try {
        const fetchPromise = api(`/api/check-user?query=${encodeURIComponent(q)}`).then(r => r.json());
        const res = await Promise.race([fetchPromise, timeoutPromise]);
        checkingUser.value = false;
        if (res.found) {
          verifiedUser.value = res;
        } else {
          userCheckError.value = res.error || 'User not found on Telegram.';
        }
      } catch (e) {
        checkingUser.value = false;
        userCheckError.value = e.message === 'Search timeout' ? 'Verification timed out. Try again.' : 'Failed to verify recipient.';
      }
    };

    const onRecipientInput = () => {
      verifiedUser.value = null; userCheckError.value = '';
      clearTimeout(checkTimeout);
      const q = recipient.value.trim();
      if (!q) {
        checkingUser.value = false;
        return;
      }
      const cleanQ = q.replace(/^@/, '');
      if (!isNumeric(q) && cleanQ.length < 3) {
        checkingUser.value = false;
        return;
      }
      checkingUser.value = true;
      checkTimeout = setTimeout(() => { checkRecipientNow(); }, 500);
    };

    const clearRecipient = () => {
      recipient.value = ''; verifiedUser.value = null; userCheckError.value = '';
    };

    const pickContact = () => {
      if (!tg) {
        const inp = prompt('Enter Telegram Username (@username) or User ID:');
        if (inp) { recipient.value = inp.trim(); checkRecipientNow(); }
        return;
      }

      if (typeof tg.requestChat === 'function') {
        try {
          tg.requestChat({
            request_id: Math.floor(Math.random() * 1000000),
            chat_is_channel: false,
            chat_is_forum: false,
            chat_has_username: true,
            chat_is_created: false,
            bot_is_member: false
          }, (ok, chat) => {
            if (ok && chat) {
              const val = chat.username ? `@${chat.username}` : `${chat.id}`;
              recipient.value = val; checkRecipientNow(); showToast(`Selected: ${val}`);
            }
          });
          return;
        } catch (e) {
          console.error("tg.requestChat error:", e);
        }
      }

      if (typeof tg.requestUser === 'function') {
        try {
          tg.requestUser({ bot_is_member: false }, (ok, u) => {
            if (ok && u) {
              const val = u.username ? `@${u.username}` : `${u.id}`;
              recipient.value = val; checkRecipientNow(); showToast(`Selected: ${val}`);
            }
          });
          return;
        } catch (e) {}
      }

      const inp = prompt('Enter Telegram Username (@username) or User ID:');
      if (inp) { recipient.value = inp.trim(); checkRecipientNow(); }
    };

    const pay = async () => {
      if (selectedSender.value === 'myaccount' && !userAccount.value) {
        openPhoneAuth();
        return;
      }

      let rcpt = recipient.value.trim();
      if (!rcpt) { errMsg.value = t('recipientInputPlaceholder'); return; }
      if (!ME) { showToast('Open in Telegram to purchase'); return; }

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
            userbot_id: selectedSender.value === 'myaccount' ? userAccount.value?.id : (selectedSender.value === 'userbot' ? selectedUserbot.value : null)
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
        errMsg.value = t('somethingWentWrong');
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

    const openAdmin = () => {
      showAdmin.value = true;
      aTab.value = 'gifts';
      loadAdminGifts();
      loadAdminOrders();
      loadAdminUserbots();
    };

    const showSenderDropdown = ref(false);
    const getSelectedUserbotObj = () => {
      if (!publicUserbots.value || !publicUserbots.value.length) return null;
      return publicUserbots.value.find(u => u.id === selectedUserbot.value) || publicUserbots.value[0];
    };
    const getSelectedUserbotName = () => {
      const u = getSelectedUserbotObj();
      if (!u) return 'Userbot';
      const name = (u.first_name || '').trim().split(' ')[0];
      return name || (u.username ? '@' + u.username : 'Userbot');
    };

    const getUserFirstName = () => {
      if (userAccount.value && userAccount.value.first_name) {
        return userAccount.value.first_name.trim().split(' ')[0];
      }
      if (ME && ME.first_name) {
        return ME.first_name.trim().split(' ')[0];
      }
      return 'My Account';
    };

    const getUserPhoto = () => {
      if (ME && ME.photo_url) return ME.photo_url;
      if (userAccount.value && userAccount.value.photo) return userAccount.value.photo;
      return null;
    };

    const sortedAdminGifts = computed(() => {
      if (!adminGifts.value) return [];
      return [...adminGifts.value].sort((a, b) => {
        const aActive = a.active ? 1 : 0;
        const bActive = b.active ? 1 : 0;
        if (aActive === bActive) return a.id - b.id;
        return bActive - aActive; // Active first (1), deleted at bottom (0)
      });
    });

    const openAddForm = () => {
      Object.assign(form, { show: true, id: null, emoji: '🧸', display_name: '', date_label: '08/07/26', gift_tg_id: '', base_stars: 50, commission: 10, animation: '' });
    };
    const editGift = g => {
      Object.assign(form, { show: true, id: g.id, emoji: g.emoji || '🧸', display_name: g.display_name || '', date_label: g.date_label, gift_tg_id: g.gift_tg_id, base_stars: g.base_stars, commission: g.commission, animation: g.animation || '' });
    };
    const onAnimationFileSelect = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith('.json')) {
        showToast('❌ Only .json files allowed!');
        return;
      }
      const formData = new FormData();
      formData.append('file', file);
      try {
        const r = await api('/api/admin/upload-animation', {
          method: 'POST',
          body: formData,
        });
        const data = await r.json();
        if (r.ok && data.filename) {
          form.animation = data.filename;
          showToast(`✅ Uploaded: ${data.filename}`);
        } else {
          showToast(`❌ Upload failed: ${data.detail || 'Error'}`);
        }
      } catch (err) {
        showToast('❌ Upload error!');
      }
    };
    const saveGift = async () => {
      const body = {
        emoji: form.emoji || '🧸',
        display_name: form.display_name || 'New Gift',
        date_label: form.date_label || '08/07/26',
        gift_tg_id: form.gift_tg_id ? String(form.gift_tg_id) : '6012345678',
        base_stars: Number(form.base_stars) || 50,
        commission: Number(form.commission) || 10,
        animation: form.animation || ''
      };
      const url = form.id ? `/api/admin/gifts/${form.id}` : '/api/admin/gifts';
      const method = form.id ? 'PATCH' : 'POST';
      try {
        const r = await api(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        if (r.ok) {
          form.show = false;
          await loadAdminGifts();
          await loadGifts();
          showToast('✅ Gift Saved Successfully!');
        } else {
          const errData = await r.json().catch(() => ({}));
          showToast(`❌ Save failed: ${errData.detail || 'Error'}`);
        }
      } catch (err) {
        showToast(`❌ Save error: ${err.message}`);
      }
    };
    const toggleActive = async g => {
      await api(`/api/admin/gifts/${g.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active: g.active ? 0 : 1 }) });
      showToast(g.active ? '🔴 Gift Deactivated' : '🟢 Gift Activated');
      loadAdminGifts(); loadGifts();
    };
    const delGift = async id => {
      const doDel = async () => {
        const r = await api(`/api/admin/gifts/${id}`, { method: 'DELETE' });
        if (r.ok) {
          showToast('🗑️ Gift Deleted');
          loadAdminGifts();
          loadGifts();
        } else {
          showToast('❌ Failed to delete gift');
        }
      };
      if (window.Telegram?.WebApp?.showConfirm) {
        window.Telegram.WebApp.showConfirm('Are you sure you want to delete this gift?', (ok) => {
          if (ok) doDel();
        });
      } else {
        doDel();
      }
    };

    const adminUserbots = ref([]);
    const userLinkedAccounts = computed(() => adminUserbots.value.filter(u => u.owner_tg_id));
    const systemUserbots = computed(() => adminUserbots.value.filter(u => !u.owner_tg_id));
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

    const toggleUserbotActive = async (ub) => {
      if (ub.toggling) return;
      ub.toggling = true;
      showToast('⏳ Updating Userbot status...');
      try {
        const newActive = ub.active === false ? true : false;
        const r = await api(`/api/admin/userbots/${ub.id}/toggle-active`, {
          method: 'POST',
        });
        const data = await r.json();
        if (r.ok) {
          ub.active = newActive;
          showToast(newActive ? '🟢 Userbot Re-activated' : '🔴 Userbot Disabled');
          await loadAdminUserbots();
          await loadUserbotAccounts();
        } else {
          showToast(`❌ ${data.detail || 'Failed to toggle userbot'}`);
        }
      } catch (e) {
        showToast(`❌ ${e.message}`);
      } finally {
        ub.toggling = false;
      }
    };

    const jumpToUserbotChat = (ub) => {
      const acc = userbotAccounts.value.find(a => a.id === ub.id) || ub;
      chatState.selectChatAccount(acc);
      tab.value = 'chat';
    };

    // ── Boot ───────────────────────────────────
    onMounted(async () => {
      isAdmin.value = true;
      try {
        const cfg = await fetch('/api/config', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
      } catch {}

      await loadPricing();
      await loadGifts();
      await loadUserbotAccounts();
      await loadBotCommands();
      await loadManagedBots();
      if (ME) loadHistory();

      pageLoading.value = false;

      if (tg) {
        tg.BackButton.onClick(() => {
          if (showAdmin.value) showAdmin.value = false;
          else if (phoneModal.show) phoneModal.show = false;
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

    const totalStars = computed(() => {
      if (!selected.value) return 0;
      if (selectedSender.value === 'myaccount') return pricing.myaccount_stars || 50;
      if (selectedSender.value === 'userbot') return pricing.userbot_stars || 55;
      return pricing.bot_stars || (selected.value.base_stars + selected.value.commission);
    });

    const priceBreakdown = computed(() => {
      if (!selected.value) return { base: 0, fee: 0, total: 0 };
      const base = selected.value.base_stars || 50;
      const total = totalStars.value;
      const fee = Math.max(0, total - base);
      return { base, fee, total };
    });

    // ── Telegram link helpers ─────────────────────
    const openTelegramLink = (peer) => {
      const clean = (peer || '').replace(/^@/, '');
      if (!clean) return;
      const url = `https://t.me/${clean}`;
      if (tg?.openTelegramLink) {
        tg.openTelegramLink(url);
      } else {
        window.open(url, '_blank');
      }
    };

    const openTelegramChatWithUserbot = (ub) => {
      if (ub.username) {
        openTelegramLink('@' + ub.username);
      } else {
        showToast('No username set for this userbot');
      }
    };

    // ── Bot Panel Admin Actions ───────────────────
    const loadBotPanelUsers = async () => {
      try {
        const users = await fetch('/api/admin/users', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        botPanelUsers.value = Array.isArray(users) ? users : [];
      } catch (e) {
        console.error('loadBotPanelUsers error:', e);
        showToast('Failed to load bot users');
      }
    };

    const restartTelegramBot = async () => {
      try {
        const res = await fetch('/api/admin/bot/restart', { method: 'POST', headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (res.success) {
          showToast('🤖 Bot restarted successfully!');
        } else {
          showToast('❌ Restart failed: ' + (res.error || 'Unknown error'));
        }
      } catch (e) {
        showToast('❌ Failed to restart bot');
      }
    };

    const refreshWebhook = async () => {
      try {
        const res = await fetch('/api/admin/bot/sync-webhook', { method: 'POST', headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (res.success) {
          showToast('⚡ Webhook synchronized successfully!');
        } else {
          showToast('❌ Sync failed: ' + (res.error || 'Unknown error'));
        }
      } catch (e) {
        showToast('❌ Webhook synchronization failed');
      }
    };

    const openBroadcastModal = () => {
      broadcastText.value = '';
      broadcastShow.value = true;
    };

    const sendBroadcast = async () => {
      if (!broadcastText.value.trim()) return;
      try {
        const res = await fetch('/api/admin/bot/broadcast', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': '69420'
          },
          body: JSON.stringify({ message: broadcastText.value })
        }).then(r => r.json());
        if (res.success) {
          showToast(`📢 Broadcast sent! Sent: ${res.sent}, Failed: ${res.failed}`);
          broadcastShow.value = false;
        } else {
          showToast('❌ Broadcast failed: ' + (res.error || 'Unknown error'));
        }
      } catch (e) {
        showToast('❌ Broadcast failed to send');
      }
    };
    const loadBotCommands = async () => {
      try {
        const res = await fetch('/api/admin/bot/commands', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (res.success) {
          botCommands.value = res.commands || [];
        }
      } catch (e) {
        console.error('loadBotCommands failed:', e);
      }
    };

    const saveBotCommands = async () => {
      try {
        const res = await fetch('/api/admin/bot/commands', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': '69420'
          },
          body: JSON.stringify({ commands: botCommands.value })
        }).then(r => r.json());
        if (res.success) {
          showToast('✅ Bot commands updated successfully!');
        } else {
          showToast('❌ Failed to update bot commands: ' + (res.error || 'Unknown error'));
        }
      } catch (e) {
        showToast('❌ Failed to update bot commands');
      }
    };

    const addBotCommand = () => {
      botCommands.value.push({ command: '', description: '' });
    };

    const removeBotCommand = (idx) => {
      botCommands.value.splice(idx, 1);
    };

    // ── Multi-Bot Management State & Logic ────────────────
    const managedBots = ref([]);
    const botLoading = ref(false);
    const showAddBotModal = ref(false);
    const newBotToken = ref('');
    const addingBot = ref(false);
    const showCommandModal = ref(false);
    const selectedBotForConfig = ref(null);
    const botCommandsList = ref([]);
    const activeBotNav = ref('bots'); // 'bots' or 'bot_chat'
    const selectedBotChat = ref(null);
    const botChatContacts = ref([]);
    const activeBotUser = ref(null);
    const botMessages = ref([]);
    const botInputText = ref('');
    const botSending = ref(false);

    window.handleGlobalBotMessage = (data) => {
      const msg = data.message;
      const token = data.bot_token;
      const userId = data.user_id;
      if (selectedBotChat.value && selectedBotChat.value.token === token && activeBotUser.value && activeBotUser.value.user_id === userId) {
        if (!botMessages.value.some(m => m.id === msg.id)) {
          botMessages.value.push(msg);
        }
      }
      if (selectedBotChat.value && selectedBotChat.value.token === token) {
        loadBotContacts(selectedBotChat.value.id);
      }
    };

    const loadManagedBots = async () => {
      botLoading.value = true;
      try {
        const r = await api('/api/admin/managed-bots');
        const data = await r.json();
        if (data.success) {
          managedBots.value = data.bots;
        }
      } catch (e) {
        console.error('loadManagedBots error:', e);
      } finally {
        botLoading.value = false;
      }
    };

    const addBotToken = async () => {
      const token = newBotToken.value.trim();
      if (!token) { showToast('⚠️ Enter Bot Token'); return; }
      addingBot.value = true;
      try {
        const r = await api('/api/admin/managed-bots', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token })
        });
        const data = await r.json();
        if (data.success) {
          showToast('🎉 Bot added successfully!');
          newBotToken.value = '';
          showAddBotModal.value = false;
          await loadManagedBots();
        } else {
          showToast('❌ ' + (data.error || 'Failed to add bot'));
        }
      } catch (e) {
        showToast('❌ Add bot error: ' + e.message);
      } finally {
        addingBot.value = false;
      }
    };

    const toggleBotStatus = async (bot) => {
      const nextState = !bot.active;
      try {
        const r = await api(`/api/admin/managed-bots/${bot.id}/toggle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ active: nextState })
        });
        const data = await r.json();
        if (data.success) {
          bot.active = nextState ? 1 : 0;
          showToast(nextState ? '🟢 Bot started' : '🔴 Bot stopped');
        }
      } catch (e) {
        showToast('❌ Error toggling bot');
      }
    };

    const deleteBot = async (bot) => {
      if (!confirm(`Delete bot @${bot.bot_username}?`)) return;
      try {
        const r = await api(`/api/admin/managed-bots/${bot.id}`, { method: 'DELETE' });
        const data = await r.json();
        if (data.success) {
          showToast('🗑️ Bot deleted');
          await loadManagedBots();
        }
      } catch (e) {
        showToast('❌ Error deleting bot');
      }
    };

    const openBotConfig = (bot) => {
      selectedBotForConfig.value = bot;
      botCommandsList.value = [];
      try {
        const scripts = JSON.parse(bot.scripts_json || '{}');
        for (const [cmd, reply] of Object.entries(scripts)) {
          botCommandsList.value.push({ cmd, reply });
        }
      } catch {}
      if (!botCommandsList.value.length) {
        botCommandsList.value.push({ cmd: '/start', reply: 'Welcome to our bot!' });
      }
      showCommandModal.value = true;
    };

    const addCommandRow = () => {
      botCommandsList.value.push({ cmd: '', reply: '' });
    };

    const removeCommandRow = (idx) => {
      botCommandsList.value.splice(idx, 1);
    };

    const saveManagedBotCommands = async () => {
      if (!selectedBotForConfig.value) return;
      const scripts = {};
      const commands = [];
      botCommandsList.value.forEach(row => {
        let c = row.cmd.trim();
        if (c && row.reply.trim()) {
          if (!c.startsWith('/')) c = '/' + c;
          scripts[c] = row.reply.trim();
          commands.push(c);
        }
      });
      try {
        const r = await api(`/api/admin/managed-bots/${selectedBotForConfig.value.id}/commands`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ commands, scripts })
        });
        const data = await r.json();
        if (data.success) {
          showToast('💾 Commands saved');
          showCommandModal.value = false;
          await loadManagedBots();
        }
      } catch (e) {
        showToast('❌ Error saving commands');
      }
    };

    const triggerBotAttachment = () => {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = 'image/*,video/*,audio/*,.pdf,.doc,.docx,.zip';
      fileInput.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file || !selectedBotChat.value || !activeBotUser.value) {
          showToast('⚠️ Select bot and user chat first');
          return;
        }

        showToast('⏳ Uploading media...');
        try {
          const formData = new FormData();
          formData.append('file', file);

          const uploadRes = await api('/api/upload-media', {
            method: 'POST',
            body: formData
          });
          const uploadData = await uploadRes.json();
          if (!uploadData.success) {
            showToast('❌ Upload failed: ' + (uploadData.error || 'Error'));
            return;
          }

          const mediaUrl = uploadData.url;
          const mediaType = uploadData.media_type;

          const r = await api(`/api/admin/managed-bots/${selectedBotChat.value.id}/send-media`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: activeBotUser.value.user_id,
              user_username: activeBotUser.value.user_username,
              user_first_name: activeBotUser.value.user_first_name,
              media_url: mediaUrl,
              media_type: mediaType,
              caption: botInputText.value.trim()
            })
          });
          const data = await r.json();
          if (data.success) {
            botInputText.value = '';
            if (data.message && !botMessages.value.some(m => m.id === data.message.id)) {
              botMessages.value.push(data.message);
            }
            showToast('✅ Bot media sent!');
          } else {
            showToast('❌ Send media error: ' + (data.error || 'Failed'));
          }
        } catch (err) {
          showToast('❌ Send media error: ' + err.message);
        }
      };
      fileInput.click();
    };

    // Bulk Commands Modal logic
    const showBulkModal = ref(false);
    const bulkBotIds = ref([]);
    const bulkApplyAll = ref(true);
    const bulkCommandsList = ref([{ cmd: '/start', reply: 'Hello! How can I help you?' }]);
    const bulkSaving = ref(false);

    const openBulkModal = () => {
      bulkBotIds.value = managedBots.value.map(b => b.id);
      bulkApplyAll.value = true;
      if (!bulkCommandsList.value.length) {
        bulkCommandsList.value = [{ cmd: '/start', reply: 'Hello! How can I help you?' }];
      }
      showBulkModal.value = true;
    };

    const addBulkRow = () => {
      bulkCommandsList.value.push({ cmd: '', reply: '' });
    };

    const removeBulkRow = (idx) => {
      bulkCommandsList.value.splice(idx, 1);
    };

    const saveBulkCommands = async () => {
      bulkSaving.value = true;
      try {
        const scripts = {};
        const commands = [];
        bulkCommandsList.value.forEach(row => {
          let c = row.cmd.trim();
          if (c && row.reply.trim()) {
            if (!c.startsWith('/')) c = '/' + c;
            scripts[c] = row.reply.trim();
            commands.push(c);
          }
        });

        const targetIds = bulkApplyAll.value ? managedBots.value.map(b => b.id) : bulkBotIds.value;

        const r = await api('/api/admin/managed-bots/bulk-commands', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bot_ids: targetIds,
            commands,
            scripts
          })
        });
        const data = await r.json();
        bulkSaving.value = false;
        if (data.success) {
          showToast('🚀 Bulk commands deployed to selected bots!');
          showBulkModal.value = false;
          await loadManagedBots();
        } else {
          showToast('❌ Bulk deploy error: ' + (data.error || 'Failed'));
        }
      } catch (e) {
        bulkSaving.value = false;
        showToast('❌ ' + e.message);
      }
    };

    const openBotChatNav = async (bot) => {
      selectedBotChat.value = bot;
      activeBotNav.value = 'bot_chat';
      activeBotUser.value = null;
      botMessages.value = [];
      await loadBotContacts(bot.id);
    };

    const loadBotContacts = async (botId) => {
      try {
        const r = await api(`/api/admin/managed-bots/${botId}/contacts`);
        const data = await r.json();
        if (data.success) {
          botChatContacts.value = data.contacts;
        }
      } catch (e) {
        console.error('loadBotContacts error:', e);
      }
    };

    const selectBotUserChat = async (user) => {
      activeBotUser.value = user;
      botMessages.value = [];
      if (!selectedBotChat.value) return;
      try {
        const r = await api(`/api/admin/managed-bots/${selectedBotChat.value.id}/history/${user.user_id}`);
        const data = await r.json();
        if (data.success) {
          botMessages.value = data.messages;
        }
      } catch (e) {
        console.error('selectBotUserChat history error:', e);
      }
    };

    const sendBotMessageToUser = async () => {
      const text = botInputText.value.trim();
      if (!text || !selectedBotChat.value || !activeBotUser.value) return;
      botSending.value = true;
      try {
        const r = await api(`/api/admin/managed-bots/${selectedBotChat.value.id}/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: activeBotUser.value.user_id,
            user_username: activeBotUser.value.user_username,
            user_first_name: activeBotUser.value.user_first_name,
            text
          })
        });
        const data = await r.json();
        botSending.value = false;
        if (data.success) {
          botInputText.value = '';
          if (data.message && !botMessages.value.some(m => m.id === data.message.id)) {
            botMessages.value.push(data.message);
          }
        } else {
          showToast('❌ Send error: ' + (data.error || 'Failed'));
        }
      } catch (e) {
        botSending.value = false;
        showToast('❌ ' + e.message);
      }
    };

    onMounted(() => {
      loadManagedBots();
    });

    return {
      pageLoading, botCommands, loadBotCommands, saveBotCommands, addBotCommand, removeBotCommand,
      botMenuTab, botPanelUsers, broadcastShow, broadcastText, loadBotPanelUsers, restartTelegramBot, refreshWebhook, openBroadcastModal, sendBroadcast,

      // Managed Bots Exports
      managedBots, botLoading, showAddBotModal, newBotToken, addingBot, showCommandModal, selectedBotForConfig,
      botCommandsList, activeBotNav, selectedBotChat, botChatContacts, activeBotUser, botMessages, botInputText, botSending,
      loadManagedBots, addBotToken, toggleBotStatus, deleteBot, openBotConfig, addCommandRow, removeCommandRow,
      saveManagedBotCommands, openBotChatNav, loadBotContacts, selectBotUserChat, sendBotMessageToUser,

      tab, gifts, selected, hoveredGiftId, recipient, giftMsg, paying, errMsg, toast, totalStars, priceBreakdown,
      isAdmin, showAdmin, aTab, adminGifts, sortedAdminGifts, adminOrders, adminUserbots, userLinkedAccounts, systemUserbots, ubForm, ubMsgForm, myOrders, user, form,
      checkingUser, verifiedUser, userCheckError, userbotAccounts, publicUserbots, selectedSender, selectedUserbot, userAccount, accountsLoading,
      showSenderDropdown, getSelectedUserbotObj, getSelectedUserbotName, getUserFirstName, getUserPhoto, onAnimationFileSelect,
      currentLang, setLanguage, t, pricing, savePricing, phoneModal, openPhoneAuth, requestPhoneCode, resendPhoneCode, confirmPhoneCode, disconnectMyAccount,
      sheetGlowStyle, sheetRingStyle, giftName, getGiftImg, getFallbackPng, scrollToGifts, openRealUserContact, isNumeric,
      openSheet, closeSheet, pickContact, setRecipientMe, pay, loadHistory, openAdmin,
      onRecipientInput, checkRecipientNow, clearRecipient,
      loadAdminGifts, loadAdminOrders, loadAdminUserbots, openAddUserbot, editUserbot, saveUserbot, openAddForm, editGift, saveGift, toggleActive, delGift,
      openUserbotMsg, sendUserbotMsg, toggleUserbotActive, jumpToUserbotChat,
      openTelegramLink, openTelegramChatWithUserbot,
      // ── Chat Module ──
      ...chatState,
    };
  },
}).mount('#app');
