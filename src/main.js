import { createApp, ref, reactive, computed, onMounted, watch, nextTick, shallowRef } from 'vue';

// ── Telegram WebApp SDK Initialization ────────────────────────
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  try {
    if (tg.isVersionAtLeast && tg.isVersionAtLeast('6.1')) {
      if (typeof tg.setBackgroundColor === 'function') tg.setBackgroundColor('#0D0E1A');
      if (typeof tg.setHeaderColor === 'function') tg.setHeaderColor('#0D0E1A');
    }
  } catch (e) {}
}

console.log('⚡ TgGifts Ultra-Fast Vite + Vue 3 Engine Initialized');
