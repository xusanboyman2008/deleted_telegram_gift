<template>
  <div class="view">
    <h2 class="view-title">📜 {{ t('history') }}</h2>

    <div v-if="!user" class="empty-state">
      <div class="empty-icon">🔒</div>
      <p>Open in Telegram to view your orders</p>
    </div>

    <!-- 🦴 Skeleton Loader for History Tab -->
    <div v-else-if="historyLoading && myOrders.length === 0" class="skeleton-orders-list">
      <div v-for="n in 4" :key="n" class="skeleton-order-item">
        <div class="skeleton-order-left">
          <div class="skeleton-order-emoji shimmer-skeleton"></div>
          <div class="skeleton-order-info">
            <div class="skeleton-order-title shimmer-skeleton"></div>
            <div class="skeleton-order-sub shimmer-skeleton"></div>
          </div>
        </div>
        <div class="skeleton-order-right">
          <div class="skeleton-order-stars shimmer-skeleton"></div>
          <div class="skeleton-order-status shimmer-skeleton"></div>
        </div>
      </div>
    </div>

    <div v-else-if="myOrders.length === 0" class="empty-state">
      <span class="empty-icon">🎁</span>
      <p>No orders yet</p>
    </div>

    <div v-else class="orders-list">
      <transition-group name="list-slide">
        <div
          v-for="o in myOrders"
          :key="o.id"
          v-memo="[o.id, o.status, o.total_stars]"
          class="order-item"
          :style="{'animation-delay': (o.id % 5) * 0.05 + 's'}"
        >
          <div class="oi-left">
            <div class="oi-media" style="width: 42px; height: 42px; flex-shrink: 0;">
              <LottieAnim v-if="o.animation" :filename="o.animation" />
              <span v-else class="oi-emoji">{{ o.emoji }}</span>
            </div>
            <div class="oi-info">
              <span class="oi-name">{{ giftName(o) }}</span>
              <span class="oi-recipient">To: {{ o.recipient_id }}</span>
            </div>
          </div>
          <div class="oi-right">
            <span class="oi-stars">⭐ {{ o.total_stars }}</span>
            <span :class="['oi-status', 'st-'+o.status]">{{ o.status }}</span>
          </div>
        </div>
      </transition-group>

      <!-- Incremental Lazy Loading Spinner Indicator -->
      <div v-if="historyLoadingMore" class="skeleton-orders-list" style="margin-top: 10px;">
        <div v-for="n in 2" :key="'loadmore-'+n" class="skeleton-order-item" style="padding: 10px 14px; opacity: 0.7;">
          <div class="skeleton-order-left">
            <div class="skeleton-order-emoji shimmer-skeleton" style="width: 36px; height: 36px;"></div>
            <div class="skeleton-order-info">
              <div class="skeleton-order-title shimmer-skeleton" style="width: 100px;"></div>
              <div class="skeleton-order-sub shimmer-skeleton" style="width: 70px;"></div>
            </div>
          </div>
          <div class="skeleton-order-right">
            <div class="skeleton-order-stars shimmer-skeleton" style="width: 45px;"></div>
          </div>
        </div>
      </div>

      <div v-else-if="!historyHasMore && myOrders.length >= 10" style="text-align: center; color: rgba(255,255,255,0.3); font-size: 0.75rem; padding: 16px 0 8px; font-weight: 500;">
        ✦ End of order history ✦
      </div>
    </div>
  </div>
</template>

<script setup>
import LottieAnim from './LottieAnim.vue';

defineProps({
  user: { type: Object, default: null },
  myOrders: { type: Array, required: true },
  historyLoading: { type: Boolean, default: false },
  historyLoadingMore: { type: Boolean, default: false },
  historyHasMore: { type: Boolean, default: true },
  t: { type: Function, required: true },
  giftName: { type: Function, required: true }
});
</script>
