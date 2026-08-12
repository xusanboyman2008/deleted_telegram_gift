<template>
  <div class="page">
    <div class="page-title" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h2>🤖 {{ t('botPanel') }}</h2>
      <div style="display: flex; gap: 8px;">
        <button class="v-btn" @click="$emit('open-broadcast-modal')" style="background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.3); color: #c084fc; padding: 6px 14px; border-radius: 10px; font-size: 0.8rem; font-weight: 700; cursor: pointer;">
          📢 Broadcast
        </button>
        <button class="v-btn" @click="$emit('open-add-bot')" style="background: linear-gradient(135deg, #10b981, #059669); color: #fff; border: none; padding: 6px 14px; border-radius: 10px; font-size: 0.8rem; font-weight: 700; cursor: pointer;">
          ➕ Add Bot
        </button>
      </div>
    </div>

    <!-- Managed Bots Grid -->
    <div v-if="botLoading" class="skeleton-userbots-grid">
      <div v-for="n in 2" :key="n" class="skeleton-userbot-card shimmer-skeleton"></div>
    </div>

    <div v-else class="premium-userbot-grid">
      <div
        v-for="bot in managedBots"
        :key="bot.id"
        class="premium-userbot-card"
      >
        <div class="pub-header">
          <div class="pub-avatar-placeholder">🤖</div>
          <div class="pub-details">
            <div class="pub-name">
              {{ bot.bot_name || 'Bot #'+bot.id }}
              <span :class="['status-pill', bot.active ? 'active' : 'inactive']">
                {{ bot.active ? '🟢 Running' : '🔴 Stopped' }}
              </span>
            </div>
            <div class="pub-username">@{{ bot.bot_username || 'no_username' }}</div>
          </div>
        </div>
        <div class="pub-actions" style="margin-top: 14px;">
          <button v-if="bot.active" class="btn-disable v-btn" @click="$emit('toggle-bot', bot)">Stop Bot</button>
          <button v-else class="btn-enable v-btn" @click="$emit('toggle-bot', bot)">Start Bot</button>
          <button class="btn-edit v-btn" @click="$emit('config-bot', bot)">⚙️ Config</button>
          <button class="btn-msg v-btn" @click="$emit('delete-bot', bot)" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3);">🗑️ Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  managedBots: { type: Array, required: true },
  botLoading: { type: Boolean, default: false },
  t: { type: Function, required: true }
});

defineEmits(['open-broadcast-modal', 'open-add-bot', 'toggle-bot', 'config-bot', 'delete-bot']);
</script>
