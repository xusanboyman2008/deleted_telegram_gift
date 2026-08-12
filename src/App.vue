<template>
  <div id="app-root">
    <!-- Active Tab Component Container with Vue 3 Transitions -->
    <div class="view-wrap">
      <transition name="fade-slide" mode="out-in">
        <GiftsView
          v-if="tab === 'home'"
          key="home"
          :gifts="gifts"
          :gifts-loading="giftsLoading"
          :pricing="pricing"
          :is-admin="isAdmin"
          :t="t"
          :gift-name="giftName"
          @open-sheet="openSheet"
          @open-real-user="openRealUserContact"
          @open-admin="openAdmin"
          @open-add-form="openAddForm"
        />
        <ChatsView
          v-else-if="tab === 'chat'"
          key="chat"
          :filtered-chat-list="filteredChatList"
          :current-chat-peer="currentChatPeer"
          :active-chat="activeChat"
          :current-messages="currentMessages"
          :chat-loading="chatLoading"
          :mobile-show-chat="mobileShowChat"
          @select-chat="selectChat"
          @close-mobile-chat="closeMobileChat"
          @send-msg="sendMsg"
        />
        <HistoryView
          v-else-if="tab === 'history'"
          key="history"
          :user="user"
          :my-orders="myOrders"
          :history-loading="historyLoading"
          :history-loading-more="historyLoadingMore"
          :history-has-more="historyHasMore"
          :t="t"
          :gift-name="giftName"
        />
        <SettingsView
          v-else-if="tab === 'settings'"
          key="settings"
          :user-account="userAccount"
          :accounts-loading="accountsLoading"
          :current-lang="currentLang"
          :t="t"
          @disconnect-account="disconnectMyAccount"
          @open-phone-auth="openPhoneAuth"
          @set-language="setLanguage"
          @open-real-user="openRealUserContact"
        />
        <UserbotsView
          v-else-if="tab === 'userbots'"
          key="userbots"
          :admin-userbots="adminUserbots"
          :user-linked-accounts="userLinkedAccounts"
          :system-userbots="systemUserbots"
          :userbots-loading="userbotsLoading"
          :stars-refreshing="starsRefreshing"
          :t="t"
          @refresh-stars="refreshUserbotStars"
          @open-add-userbot="openAddUserbot"
          @jump-to-chat="jumpToUserbotChat"
          @toggle-active="toggleUserbotActive"
          @edit-userbot="editUserbot"
          @open-msg="openUserbotMsg"
        />
        <BotPanel
          v-else-if="tab === 'bot_control'"
          key="bot_control"
          :managed-bots="managedBots"
          :bot-loading="botLoading"
          :t="t"
          @open-broadcast-modal="openBroadcastModal"
          @open-add-bot="openAddBot"
          @toggle-bot="toggleBot"
          @config-bot="configBot"
          @delete-bot="deleteBot"
        />
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import GiftsView from './components/GiftsView.vue';
import ChatsView from './components/ChatsView.vue';
import HistoryView from './components/HistoryView.vue';
import SettingsView from './components/SettingsView.vue';
import UserbotsView from './components/UserbotsView.vue';
import BotPanel from './components/BotPanel.vue';

// Access active global Vue refs from window scope
const tab = ref(window.appTab || 'home');
const gifts = ref(window.appGifts || []);
const giftsLoading = ref(false);
const myOrders = ref(window.appOrders || []);
const historyLoading = ref(false);
const historyLoadingMore = ref(false);
const historyHasMore = ref(true);
const userAccount = ref(window.appUserAccount || null);
const accountsLoading = ref(false);
const adminUserbots = ref(window.appAdminUserbots || []);
const userLinkedAccounts = computed(() => adminUserbots.value.filter(u => u.owner_tg_id));
const systemUserbots = computed(() => adminUserbots.value.filter(u => !u.owner_tg_id));
const userbotsLoading = ref(false);
const starsRefreshing = ref(false);
const currentLang = ref('en');
const isAdmin = ref(false);
const user = ref(null);
const pricing = ref({ bot_stars: 3 });

// Chat State
const filteredChatList = ref(window.appChatList || []);
const currentChatPeer = ref('');
const activeChat = ref(null);
const currentMessages = ref([]);
const chatLoading = ref(false);
const mobileShowChat = ref(false);

// Bot Control State
const managedBots = ref(window.appManagedBots || []);
const botLoading = ref(false);

const t = (k) => k;
const giftName = (g) => g.name || g.gift_id || 'Gift';

const openSheet = (g) => window.openSheet?.(g);
const openRealUserContact = () => window.openRealUserContact?.();
const openAdmin = () => window.openAdmin?.();
const openAddForm = () => window.openAddForm?.();
const disconnectMyAccount = () => window.disconnectMyAccount?.();
const openPhoneAuth = () => window.openPhoneAuth?.();
const setLanguage = (l) => window.setLanguage?.(l);
const refreshUserbotStars = () => window.refreshUserbotStars?.();
const openAddUserbot = () => window.openAddUserbot?.();
const jumpToUserbotChat = (ub) => window.jumpToUserbotChat?.(ub);
const toggleUserbotActive = (ub) => window.toggleUserbotActive?.(ub);
const editUserbot = (ub) => window.editUserbot?.(ub);
const openUserbotMsg = (ub) => window.openUserbotMsg?.(ub);

const selectChat = (c) => window.openChatWindow?.(c);
const closeMobileChat = () => { mobileShowChat.value = false; };
const sendMsg = (txt) => window.sendChatMessage?.(txt);

const openBroadcastModal = () => window.openBroadcastModal?.();
const openAddBot = () => window.showAddBotModal = true;
const toggleBot = (b) => window.toggleBotStatus?.(b);
const configBot = (b) => window.openBotConfig?.(b);
const deleteBot = (b) => window.deleteBot?.(b);
</script>
