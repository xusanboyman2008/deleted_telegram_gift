<template>
  <div class="page">
    <div class="page-title" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h2>🤖 {{ t('userbots') }}</h2>
      <div style="display: flex; gap: 8px; align-items: center;">
        <button class="v-btn" @click="$emit('refresh-stars')" :disabled="starsRefreshing" style="background: rgba(234, 179, 8, 0.15); border: 1px solid rgba(234, 179, 8, 0.4); color: #FACC15; padding: 6px 14px; border-radius: 10px; font-size: 0.8rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; gap: 6px;">
          <span v-if="starsRefreshing" class="tg-spinner" style="width: 12px; height: 12px; border-width: 2px;"></span>
          <span v-else>🔄 Sync Stars</span>
        </button>
        <button class="add-btn v-btn" @click="$emit('open-add-userbot')" style="display: flex; align-items: center; gap: 6px;">
          ➕ Add Account
        </button>
      </div>
    </div>

    <!-- 🦴 Skeleton Loader for Admin Userbots -->
    <div v-if="userbotsLoading && !adminUserbots.length" class="skeleton-userbots-grid">
      <div v-for="n in 2" :key="n" class="skeleton-userbot-card">
        <div class="skeleton-userbot-header">
          <div class="skeleton-userbot-avatar shimmer-skeleton"></div>
          <div class="skeleton-userbot-details">
            <div class="skeleton-userbot-name shimmer-skeleton"></div>
            <div class="skeleton-userbot-username shimmer-skeleton"></div>
          </div>
        </div>
        <div class="skeleton-userbot-meta shimmer-skeleton"></div>
        <div class="skeleton-userbot-actions">
          <div class="skeleton-userbot-btn shimmer-skeleton"></div>
          <div class="skeleton-userbot-btn shimmer-skeleton"></div>
          <div class="skeleton-userbot-btn shimmer-skeleton"></div>
        </div>
      </div>
    </div>

    <div v-else>
      <!-- 1. Users Telegram Accounts -->
      <h3 style="margin: 20px 0 10px 0; font-size: 1.05rem; color: #fff; font-weight: 600; display: flex; align-items: center; gap: 8px;">
        <span>👤</span> {{ t('userAccounts') }}
      </h3>
      <div v-if="!userLinkedAccounts.length" style="color: rgba(255,255,255,0.4); background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; font-size: 0.9rem; text-align: center;">
        No user-linked Telegram accounts yet.
      </div>
      <transition-group v-else name="scale-pop" tag="div" class="premium-userbot-grid">
        <div
          v-for="ub in userLinkedAccounts"
          :key="ub.id"
          v-memo="[ub.id, ub.active, ub.stars_balance, starsRefreshing]"
          :class="['premium-userbot-card', ub.active === false ? 'disabled' : '']"
        >
          <div class="pub-header">
            <img v-if="ub.photo" :src="ub.photo" class="pub-avatar" alt="avatar" />
            <div v-else class="pub-avatar-placeholder">👤</div>
            <div class="pub-details">
              <div class="pub-name">
                {{ ub.first_name || 'Account #'+ub.id }} {{ ub.last_name || '' }}
                <span :class="['status-pill', ub.active !== false ? 'active' : 'inactive']">
                  {{ ub.active !== false ? '🟢 Active' : '🔴 Disabled' }}
                </span>
                <span class="stars-badge" style="background: rgba(234, 179, 8, 0.2); color: #FACC15; padding: 2px 8px; border-radius: 8px; font-size: 0.78rem; font-weight: 700; border: 1px solid rgba(234, 179, 8, 0.4); margin-left: 6px; display: inline-flex; align-items: center; gap: 3px;">
                  <span v-if="starsRefreshing" class="tg-spinner" style="width: 10px; height: 10px; border-width: 1.5px;"></span>
                  <span v-else>⭐</span> {{ ub.stars_balance || 0 }} Stars
                </span>
              </div>
              <div class="pub-username">@{{ ub.username || 'no_username' }}</div>
            </div>
          </div>
          <div class="pub-meta" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div>📞 {{ ub.phone }}</div>
              <div style="color: #c084fc; font-weight: 500;">Owner ID: {{ ub.owner_tg_id }}</div>
            </div>
          </div>
          <div class="pub-actions">
            <button class="btn-chat v-btn" @click="$emit('jump-to-chat', ub)" title="Chat as this userbot">
              💬 Chat
            </button>
            <button v-if="ub.toggling" class="btn-edit" disabled style="opacity: 0.6; cursor: wait;">
              ⏳ ...
            </button>
            <button v-else-if="ub.active !== false" class="btn-disable v-btn" @click="$emit('toggle-active', ub)" title="Disable Userbot">
              🔴 Stop
            </button>
            <button v-else class="btn-enable v-btn" @click="$emit('toggle-active', ub)" title="Enable Userbot">
              🟢 Start
            </button>
            <button class="btn-edit v-btn" @click="$emit('edit-userbot', ub)">✏️ Edit</button>
            <button class="btn-msg v-btn" @click="$emit('open-msg', ub)">✉️ Message</button>
          </div>
        </div>
      </transition-group>

      <!-- 2. System Userbots -->
      <h3 style="margin: 30px 0 10px 0; font-size: 1.05rem; color: #fff; font-weight: 600; display: flex; align-items: center; gap: 8px;">
        <span>🤖</span> {{ t('systemUserbots') }}
      </h3>
      <div v-if="!systemUserbots.length" style="color: rgba(255,255,255,0.4); background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; font-size: 0.9rem; text-align: center;">
        No system userbots configured yet.
      </div>
      <transition-group v-else name="scale-pop" tag="div" class="premium-userbot-grid">
        <div
          v-for="ub in systemUserbots"
          :key="ub.id"
          v-memo="[ub.id, ub.active, ub.stars_balance, starsRefreshing]"
          :class="['premium-userbot-card', ub.active === false ? 'disabled' : '']"
        >
          <div class="pub-header">
            <img v-if="ub.photo" :src="ub.photo" class="pub-avatar" alt="avatar" />
            <div v-else class="pub-avatar-placeholder">🤖</div>
            <div class="pub-details">
              <div class="pub-name">
                {{ ub.first_name || 'Account #'+ub.id }} {{ ub.last_name || '' }}
                <span :class="['status-pill', ub.active !== false ? 'active' : 'inactive']">
                  {{ ub.active !== false ? '🟢 Active' : '🔴 Disabled' }}
                </span>
                <span class="stars-badge" style="background: rgba(234, 179, 8, 0.2); color: #FACC15; padding: 2px 8px; border-radius: 8px; font-size: 0.78rem; font-weight: 700; border: 1px solid rgba(234, 179, 8, 0.4); margin-left: 6px; display: inline-flex; align-items: center; gap: 3px;">
                  <span v-if="starsRefreshing" class="tg-spinner" style="width: 10px; height: 10px; border-width: 1.5px;"></span>
                  <span v-else>⭐</span> {{ ub.stars_balance || 0 }} Stars
                </span>
              </div>
              <div class="pub-username">@{{ ub.username || 'no_username' }}</div>
            </div>
          </div>
          <div class="pub-meta" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div>📞 {{ ub.phone }}</div>
              <div style="color: #4ade80; font-weight: 500;">Official Platform Bot</div>
            </div>
          </div>
          <div class="pub-actions">
            <button class="btn-chat v-btn" @click="$emit('jump-to-chat', ub)" title="Chat as this userbot">
              💬 Chat
            </button>
            <button v-if="ub.toggling" class="btn-edit" disabled style="opacity: 0.6; cursor: wait;">
              ⏳ ...
            </button>
            <button v-else-if="ub.active !== false" class="btn-disable v-btn" @click="$emit('toggle-active', ub)" title="Disable Userbot">
              🔴 Stop
            </button>
            <button v-else class="btn-enable v-btn" @click="$emit('toggle-active', ub)" title="Enable Userbot">
              🟢 Start
            </button>
            <button class="btn-edit v-btn" @click="$emit('edit-userbot', ub)">✏️ Edit</button>
            <button class="btn-msg v-btn" @click="$emit('open-msg', ub)">✉️ Message</button>
          </div>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
defineProps({
  adminUserbots: { type: Array, required: true },
  userLinkedAccounts: { type: Array, required: true },
  systemUserbots: { type: Array, required: true },
  userbotsLoading: { type: Boolean, default: false },
  starsRefreshing: { type: Boolean, default: false },
  t: { type: Function, required: true }
});

defineEmits([
  'refresh-stars', 'open-add-userbot', 'jump-to-chat', 'toggle-active',
  'edit-userbot', 'open-msg'
]);
</script>
