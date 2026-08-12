<template>
  <div class="view">
    <!-- Direct Contact Owner Banner -->
    <div class="real-user-banner" @click="$emit('open-real-user')">
      <div class="rub-icon pulse-glow">👤</div>
      <div class="rub-info">
        <div class="rub-title">{{ t('buyDirectBtn') }}</div>
        <div class="rub-desc">Contact @xusanboyman200 for direct manual transfers</div>
      </div>
      <div class="rub-arrow bounce-x">↗</div>
    </div>

    <!-- 🦴 Skeleton Loader for Gifts Grid -->
    <div v-if="giftsLoading" class="skeleton-gifts-grid">
      <div v-for="n in (gifts.length || 10)" :key="n" class="skeleton-gift-card">
        <div class="skeleton-gift-media shimmer-skeleton"></div>
        <div class="skeleton-gift-title shimmer-skeleton" :style="{ width: (55 + ((n-1) % 4) * 8) + '%' }"></div>
        <div class="skeleton-gift-price"></div>
      </div>
    </div>

    <!-- 3-Column Pre-Compiled Grid -->
    <transition-group v-else name="gift-stagger" tag="div" class="gifts-grid" style="margin-top: 10px;">
      <div
        v-for="(g, index) in gifts"
        :key="g.id"
        v-memo="[g.id, g.base_stars, pricing.bot_stars, (hoveredGiftId === g.id)]"
        class="gift-card v-btn"
        :style="{ animationDelay: (index * 0.04) + 's' }"
        @click="$emit('open-sheet', g)"
        @mouseenter="hoveredGiftId = g.id"
        @mouseleave="hoveredGiftId = null"
      >
        <div class="card-badge" v-if="g.base_stars >= 50">🔥 RARE</div>
        <div class="card-media">
          <LottieAnim v-if="g.animation" :filename="g.animation" />
          <span v-else class="card-emoji-fallback">{{ g.emoji }}</span>
        </div>
        <div class="card-title">{{ giftName(g) }}</div>
        <div class="card-price-pill shine-effect">
          <span class="star-icon spin-star">⭐</span> {{ g.base_stars + (pricing.bot_stars || 3) }}
        </div>
      </div>
    </transition-group>

    <!-- Admin Management Box -->
    <div v-if="isAdmin" class="admin-bottom-box">
      <div class="admin-box-header">
        <div class="admin-box-title">⚡ Admin Management</div>
        <button class="admin-panel-btn v-btn" @click="$emit('open-admin')">Open Dashboard ⚙️</button>
      </div>
      <div class="admin-add-card v-btn" @click="$emit('open-add-form')">
        <div class="big-plus">+</div>
        <div class="add-card-text">Add New Gift</div>
      </div>
    </div>

    <p class="footer-note">⭐ Price shown in Telegram Stars</p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import LottieAnim from './LottieAnim.vue';

const props = defineProps({
  gifts: { type: Array, required: true },
  giftsLoading: { type: Boolean, default: false },
  pricing: { type: Object, required: true },
  isAdmin: { type: Boolean, default: false },
  t: { type: Function, required: true },
  giftName: { type: Function, required: true }
});

defineEmits(['open-sheet', 'open-real-user', 'open-admin', 'open-add-form']);

const hoveredGiftId = ref(null);
</script>
