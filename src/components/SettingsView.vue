<template>
  <div class="view">
    <h2 class="view-title">⚙️ {{ t('settings') }}</h2>

    <!-- 🦴 Skeleton Loader for Settings Tab -->
    <div v-if="accountsLoading && !userAccount" class="skeleton-settings">
      <div class="skeleton-settings-card">
        <div class="skeleton-settings-header">
          <div class="skeleton-settings-icon shimmer-skeleton"></div>
          <div class="skeleton-settings-title shimmer-skeleton"></div>
        </div>
        <div class="skeleton-settings-content shimmer-skeleton"></div>
      </div>
      <div class="skeleton-settings-card">
        <div class="skeleton-settings-header">
          <div class="skeleton-settings-icon shimmer-skeleton"></div>
          <div class="skeleton-settings-title shimmer-skeleton"></div>
        </div>
        <div class="skeleton-settings-content shimmer-skeleton"></div>
      </div>
    </div>

    <div v-else>
      <!-- Connected Personal Telegram Account Status Card -->
      <div class="settings-card shadow-glass" style="margin-bottom: 20px;">
        <div class="settings-header">
          <div class="settings-icon">📱</div>
          <div class="settings-title">{{ t('myAccountSender') }}</div>
        </div>
        <div class="settings-body" style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); padding: 14px 16px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);">
          <div v-if="userAccount" style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; color: #fff;">
              {{ (userAccount.first_name || 'U')[0] }}
            </div>
            <div>
              <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">
                {{ userAccount.first_name }} {{ userAccount.last_name || '' }}
              </div>
              <div style="font-size: 0.8rem; color: #10b981; font-weight: 600;">
                🟢 {{ t('myAccountConnected') }} ({{ userAccount.phone }})
              </div>
            </div>
          </div>

          <div v-else style="display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 0.85rem; color: rgba(255,255,255,0.5);">
              Not connected
            </div>
          </div>

          <div>
            <button v-if="userAccount" class="v-btn" @click="$emit('disconnect-account')" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 8px 14px; border-radius: 10px; font-size: 0.82rem; font-weight: 600; cursor: pointer;">
              {{ t('disconnectAccount') }}
            </button>
            <button v-else class="v-btn" @click="$emit('open-phone-auth')" style="background: linear-gradient(135deg, #10b981, #059669); border: none; color: #fff; padding: 8px 16px; border-radius: 10px; font-size: 0.85rem; font-weight: 700; cursor: pointer; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3);">
              {{ t('connectMyAccount') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Language Selector -->
      <div class="settings-card shadow-glass" style="margin-bottom: 20px;">
        <div class="settings-header">
          <div class="settings-icon">🌐</div>
          <div class="settings-title">{{ t('chooseLanguage') }}</div>
        </div>
        <div class="lang-selector-grid">
          <button :class="['lang-btn', currentLang === 'en' ? 'active' : '']" @click="$emit('set-language', 'en')">
            <span class="flag">🇺🇸</span> English
          </button>
          <button :class="['lang-btn', currentLang === 'uz' ? 'active' : '']" @click="$emit('set-language', 'uz')">
            <span class="flag">🇺🇿</span> O'zbekcha
          </button>
          <button :class="['lang-btn', currentLang === 'ru' ? 'active' : '']" @click="$emit('set-language', 'ru')">
            <span class="flag">🇷🇺</span> Русский
          </button>
        </div>
      </div>

      <!-- Contact Support & Direct Transfers Card -->
      <div class="settings-card shadow-glass">
        <div class="settings-header">
          <div class="settings-icon">💬</div>
          <div class="settings-title">{{ t('supportContact') }}</div>
        </div>
        <div class="settings-body">
          <p style="font-size: 0.85rem; color: rgba(255,255,255,0.6); margin-bottom: 12px; line-height: 1.4;">
            Have questions or need manual gift delivery assistance? Contact the owner directly:
          </p>
          <button class="v-btn" @click="$emit('open-real-user')" style="width: 100%; background: linear-gradient(135deg, #3B82F6, #2563EB); color: #fff; border: none; padding: 12px; border-radius: 12px; font-weight: 700; font-size: 0.9rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;">
            <span>💬</span> {{ t('supportBtn') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  userAccount: { type: Object, default: null },
  accountsLoading: { type: Boolean, default: false },
  currentLang: { type: String, default: 'en' },
  t: { type: Function, required: true }
});

defineEmits(['connect-account', 'disconnect-account', 'open-phone-auth', 'set-language', 'open-real-user']);
</script>
