/* ═══════════════════════════════════════════════
   TgGifts — Vue 3 App Logic with i18n & Phone Auth
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

// ── i18n Translations Dictionary ───────────────
const I18N = {
  en: {
    gifts: "Gifts",
    history: "History",
    settings: "Settings",
    chooseLanguage: "Choose App Language",
    senderType: "Sender Type",
    officialBot: "Official Shop Bot 🤖",
    officialBotSub: "Sent directly by TgGifts main bot",
    userbotSender: "Telegram Userbot",
    userbotSenderSub: "Sent via automated userbot account",
    myAccountSender: "Use My Telegram Account 👤",
    myAccountSenderSub: "Connect & send using your own Telegram session",
    connectMyAccount: "Connect My Account",
    myAccountConnected: "My Account Connected",
    disconnectAccount: "Disconnect Account",
    phoneAuthTitle: "Connect Telegram Account",
    phoneLabel: "Phone Number",
    phonePlaceholder: "+998901234567",
    sendCodeBtn: "Send Verification Code",
    enterCodeTitle: "Enter Telegram Code",
    codeLabel: "Telegram Code",
    codePlaceholder: "12345",
    passwordLabel: "2FA Password (If required)",
    confirmCodeBtn: "Confirm & Connect",
    supportContact: "Need Help? Contact Support",
    supportBtn: "💬 @xusanboyman200 (24/7 Support)",
    somethingWentWrong: "Something went wrong! Please contact support: @xusanboyman200",
    adminPanel: "Admin Control Center",
    pricingSettings: "Pricing & Commissions (⭐ Stars)",
    botPriceLabel: "Official Bot Total Stars",
    userbotPriceLabel: "Userbot Total Stars",
    myAccountPriceLabel: "My Account Total Stars",
    savePricingBtn: "Save Stars Pricing",
    payBtn: "Pay",
    buyDirectBtn: "Buy Direct (@xusanboyman200)",
    recipientInputPlaceholder: "Recipient Username or ID",
    giftMsgPlaceholder: "Optional message on gift...",
    userNotConnectedWarning: "Please connect your Telegram Account in Settings or select another sender.",
    userbots: "Userbots",
    userAccounts: "Users' Telegram Accounts",
    systemUserbots: "Official System Userbots",
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
  },
  uz: {
    gifts: "Sovg'alar",
    history: "Tarix",
    settings: "Sozlamalar",
    chooseLanguage: "Dastur tilini tanlang",
    senderType: "Yuboruvchi turi",
    officialBot: "Rasmiy Bot 🤖",
    officialBotSub: "TgGifts asosiy boti orqali yuborish",
    userbotSender: "Telegram Userbot",
    userbotSenderSub: "Avtomatlashtirilgan userbot orqali yuborish",
    myAccountSender: "O'z hisobimdan yuborish 👤",
    myAccountSenderSub: "O'z Telegram hisobingizni ulang va yuboring",
    connectMyAccount: "Hisobimni ulash",
    myAccountConnected: "Hisobim ulangan",
    disconnectAccount: "Hisobni uzish",
    phoneAuthTitle: "Telegram hisobni ulash",
    phoneLabel: "Telefon raqam",
    phonePlaceholder: "+998901234567",
    sendCodeBtn: "Kodni yuborish",
    enterCodeTitle: "Telegram kodini kiriting",
    codeLabel: "Telegram Kodi",
    codePlaceholder: "12345",
    passwordLabel: "2FA Parol (Agar bor bo'lsa)",
    confirmCodeBtn: "Tasdiqlash va Ulash",
    supportContact: "Yordam kerakmi? Qo'llab-quvvatlash bilan bog'laning",
    supportBtn: "💬 @xusanboyman200 (24/7 Yordam)",
    somethingWentWrong: "Nimadir xato ketdi! Iltimos admin bilan bog'laning: @xusanboyman200",
    adminPanel: "Admin Boshqaruv Paneli",
    pricingSettings: "Narxlar va Komissiyalar (⭐ Stars)",
    botPriceLabel: "Rasmiy Bot Stars Narxi",
    userbotPriceLabel: "Userbot Stars Narxi",
    myAccountPriceLabel: "O'z Hisobim Stars Narxi",
    savePricingBtn: "Narxlarni saqlash",
    payBtn: "To'lash",
    buyDirectBtn: "To'g'ridan-to'g'ri sotib olish (@xusanboyman200)",
    recipientInputPlaceholder: "Qabul qiluvchi Username yoki ID",
    giftMsgPlaceholder: "Sovg'aga qo'shimcha xabar...",
    userNotConnectedWarning: "Iltimos Sozlamalar bo'limida Telegram hisobingizni ulang yoki boshqa yuboruvchini tanlang.",
    userbots: "Userbotlar",
    userAccounts: "Foydalanuvchi akkauntlari",
    systemUserbots: "Rasmiy tizim userbotlari",
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
  },
  ru: {
    gifts: "Подарки",
    history: "История",
    settings: "Настройки",
    chooseLanguage: "Выберите язык приложения",
    senderType: "Тип отправителя",
    officialBot: "Официальный Бот 🤖",
    officialBotSub: "Отправка через основного бота TgGifts",
    userbotSender: "Telegram Юзербот",
    userbotSenderSub: "Отправка через автоматический юзербот",
    myAccountSender: "Использовать мой аккаунт 👤",
    myAccountSenderSub: "Подключить и отправить со своего Telegram аккаунта",
    connectMyAccount: "Подключить мой аккаунт",
    myAccountConnected: "Мой аккаунт подключен",
    disconnectAccount: "Отключить аккаунт",
    phoneAuthTitle: "Подключение аккаунта Telegram",
    phoneLabel: "Номер телефона",
    phonePlaceholder: "+998901234567",
    sendCodeBtn: "Отправить код",
    enterCodeTitle: "Введите код Telegram",
    codeLabel: "Код Telegram",
    codePlaceholder: "12345",
    passwordLabel: "2FA Пароль (Если включен)",
    confirmCodeBtn: "Подтвердить и подключить",
    supportContact: "Нужна помощь? Свяжитесь с поддержкой",
    supportBtn: "💬 @xusanboyman200 (24/7 Поддержка)",
    somethingWentWrong: "Что-то пошло не так! Пожалуйста, свяжитесь с поддержкой: @xusanboyman200",
    adminPanel: "Панель администратора",
    pricingSettings: "Настройка цен и комиссий (⭐ Stars)",
    botPriceLabel: "Цена через Бот (Stars)",
    userbotPriceLabel: "Цена через Юзербот (Stars)",
    myAccountPriceLabel: "Цена через Свой аккаунт (Stars)",
    savePricingBtn: "Сохранить цены",
    payBtn: "Оплатить",
    buyDirectBtn: "Купить напрямую (@xusanboyman200)",
    recipientInputPlaceholder: "Username или ID получателя",
    giftMsgPlaceholder: "Сообщение к подарку...",
    userNotConnectedWarning: "Пожалуйста, подключите аккаунт Telegram в Настройках или выберите другого отправителя.",
    userbots: "Юзерботы",
    userAccounts: "Telegram-аккаунты пользователей",
    systemUserbots: "Официальные юзерботы",
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
    let isPlaying = false;
    let failTimer = null;
    let hasPlayed = false;

    const destroy = () => {
      if (failTimer) { clearTimeout(failTimer); failTimer = null; }
      if (inst) {
        try { inst.destroy(); } catch {}
        inst = null;
      }
    };

    const replay = () => {
      if (inst && hasPlayed) {
        inst.goToAndPlay(0, true);
      }
    };

    const init = async () => {
      destroy();
      failed.value = false;
      hasPlayed = false;
      if (!props.filename) return;

      const data = await preloadAnim(props.filename);
      if (!data) { failed.value = true; return; }

      await nextTick();
      if (!el.value) return;

      failTimer = setTimeout(() => {
        if (!isPlaying) {
          console.warn('Lottie render timeout, falling back to PNG:', props.filename);
          failed.value = true;
          destroy();
        }
      }, 3000);

      try {
        inst = lottie.loadAnimation({
          container: el.value,
          renderer: getRenderer(props.filename),
          loop: false,
          autoplay: true,
          animationData: data,
        });

        const onReady = () => {
          isPlaying = true;
          if (failTimer) { clearTimeout(failTimer); failTimer = null; }
        };

        inst.addEventListener('DOMLoaded', onReady);
        inst.addEventListener('data_ready', onReady);
        inst.addEventListener('configReady', onReady);
        inst.addEventListener('drawnFrame', onReady);
        inst.addEventListener('complete', () => {
          hasPlayed = true;
        });
        inst.addEventListener('error', (err) => {
          console.error('Lottie runtime error:', props.filename, err);
          isPlaying = false;
          failed.value = true;
          destroy();
        });
      } catch (e) {
        console.error('Lottie setup error:', e);
        failed.value = true;
      }
    };

    onMounted(init);
    watch(() => props.filename, init);

    return () => {
      if (failed.value && props.fallbackImg) {
        return Vue.h('img', { src: props.fallbackImg, class: 'gift-png-fallback' });
      }
      return Vue.h('div', {
        ref: el,
        class: 'lottie-box',
        onMouseenter: replay,
        onTouchstart: replay,
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
    const tab = ref('home');
    const gifts = ref(DEFAULT_GIFTS_SEED);
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
      myaccount_stars: 60,
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
    const selectedSender = ref('bot'); // 'bot', 'userbot', 'myaccount'
    const selectedUserbot = ref(null);

    const userAccount = computed(() => {
      if (!ME) return null;
      return userbotAccounts.value.find(acc => acc.owner_tg_id === ME.id) || null;
    });

    const publicUserbots = computed(() => {
      return userbotAccounts.value.filter(acc => !acc.owner_tg_id);
    });

    const loadUserbotAccounts = async () => {
      try {
        const d = await api('/api/userbot-accounts').then(r => r.json());
        userbotAccounts.value = Array.isArray(d) ? d : [];
        if (publicUserbots.value.length > 0 && !selectedUserbot.value) {
          selectedUserbot.value = publicUserbots.value[0].id;
        }
      } catch (e) {
        console.error('loadUserbotAccounts error:', e);
      }
    };

    // ── Phone Auth Modal State for "Use My Account" ─
    const phoneModal = reactive({
      show: false,
      step: 1, // 1: phone, 2: code, 3: password
      phone: '',
      code: '',
      password: '',
      requires_password: false,
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
        loading: false,
        error: '',
      });
    };

    const requestPhoneCode = async () => {
      if (!phoneModal.phone.trim()) {
        phoneModal.error = 'Please enter phone number (+998...)';
        return;
      }
      phoneModal.loading = true;
      phoneModal.error = '';
      try {
        const r = await api('/api/user/userbot/request-code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: phoneModal.phone.trim() }),
        });
        const data = await r.json();
        phoneModal.loading = false;
        if (data.success) {
          phoneModal.step = 2;
          showToast('📩 Verification code sent to Telegram!');
        } else {
          phoneModal.error = data.support_message || data.error || 'Failed to send verification code.';
        }
      } catch (e) {
        phoneModal.loading = false;
        phoneModal.error = 'Something went wrong! Please contact support: @xusanboyman200';
      }
    };

    const confirmPhoneCode = async () => {
      if (!phoneModal.code.trim()) {
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
            phone: phoneModal.phone.trim(),
            code: phoneModal.code.trim(),
            password: phoneModal.password.trim() || null,
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
          phoneModal.step = 3;
          phoneModal.error = '2FA Password is required for this account.';
        } else {
          phoneModal.error = data.support_message || data.error || 'Failed to confirm code.';
        }
      } catch (e) {
        phoneModal.loading = false;
        phoneModal.error = 'Something went wrong! Please contact support: @xusanboyman200';
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

    let toastTimer = null;
    const showToast = msg => {
      toast.value = msg;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { toast.value = ''; }, 3200);
    };

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
          data.forEach(g => g.animation && preloadAnim(g.animation));
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
      if (!q) { verifiedUser.value = null; userCheckError.value = ''; return; }
      checkingUser.value = true; userCheckError.value = ''; verifiedUser.value = null;
      try {
        const res = await api(`/api/check-user?query=${encodeURIComponent(q)}`).then(r => r.json());
        checkingUser.value = false;
        if (res.found) {
          verifiedUser.value = res;
        } else {
          userCheckError.value = res.error || 'Recipient profile could not be verified.';
        }
      } catch (e) {
        checkingUser.value = false;
        userCheckError.value = 'Failed to verify recipient.';
      }
    };

    const onRecipientInput = () => {
      verifiedUser.value = null; userCheckError.value = '';
      clearTimeout(checkTimeout);
      const q = recipient.value.trim();
      if (!q) return;
      checkTimeout = setTimeout(() => { checkRecipientNow(); }, 700);
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

      if (typeof tg.requestContact === 'function') {
        try {
          tg.requestContact((ok, res) => {
            if (ok && res) {
              const c = res.responseUnsafe?.contact || res;
              const val = c.username ? `@${c.username}` : (c.user_id ? `${c.user_id}` : (c.phone_number || ''));
              if (val) { recipient.value = val; checkRecipientNow(); showToast(`Selected: ${val}`); }
            }
          });
          return;
        } catch (e) {}
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
      const body = { emoji: form.emoji || '🧸', display_name: form.display_name, date_label: form.date_label, gift_tg_id: form.gift_tg_id, base_stars: form.base_stars, commission: form.commission, animation: form.animation };
      const url = form.id ? `/api/admin/gifts/${form.id}` : '/api/admin/gifts';
      const method = form.id ? 'PATCH' : 'POST';
      const r = await api(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (r.ok) { form.show = false; loadAdminGifts(); loadGifts(); showToast('✅ Saved'); }
      else showToast('❌ Save failed');
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

    // ── Boot ───────────────────────────────────
    onMounted(async () => {
      try {
        const cfg = await fetch('/api/config', { headers: { 'ngrok-skip-browser-warning': '69420' } }).then(r => r.json());
        if (ME && ME.id === cfg.admin_id) isAdmin.value = true;
      } catch {}

      await loadPricing();
      await loadGifts();
      await loadUserbotAccounts();
      if (ME) loadHistory();

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
      if (selectedSender.value === 'myaccount') return pricing.myaccount_stars || 60;
      if (selectedSender.value === 'userbot') return pricing.userbot_stars || 55;
      return pricing.bot_stars || (selected.value.base_stars + selected.value.commission);
    });

    return {
      tab, gifts, selected, recipient, giftMsg, paying, errMsg, toast, totalStars,
      isAdmin, showAdmin, aTab, adminGifts, sortedAdminGifts, adminOrders, adminUserbots, userLinkedAccounts, systemUserbots, ubForm, ubMsgForm, myOrders, user, form,
      checkingUser, verifiedUser, userCheckError, userbotAccounts, publicUserbots, selectedSender, selectedUserbot, userAccount,
      showSenderDropdown, getSelectedUserbotObj, getSelectedUserbotName, getUserFirstName, getUserPhoto, onAnimationFileSelect,
      currentLang, setLanguage, t, pricing, savePricing, phoneModal, openPhoneAuth, requestPhoneCode, confirmPhoneCode, disconnectMyAccount,
      sheetGlowStyle, sheetRingStyle, giftName, getGiftImg, getFallbackPng, scrollToGifts, openRealUserContact, isNumeric,
      openSheet, closeSheet, pickContact, setRecipientMe, pay, loadHistory, openAdmin,
      onRecipientInput, checkRecipientNow, clearRecipient,
      loadAdminGifts, loadAdminOrders, loadAdminUserbots, openAddUserbot, editUserbot, saveUserbot, openAddForm, editGift, saveGift, toggleActive, delGift,
      openUserbotMsg, sendUserbotMsg,
    };
  },
}).mount('#app');
