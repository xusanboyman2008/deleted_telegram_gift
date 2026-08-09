/* ═══════════════════════════════════════════════
   TgGifts — Telegram-style Chat Module
   ═══════════════════════════════════════════════ */

// Default chat contacts (popular bots + default chats)
const DEFAULT_CHAT_CONTACTS = [
  {
    peer: '@PremiumBot',
    title: 'Telegram Premium',
    is_bot: true,
    icon: '⭐',
    color: '#0088CC',
    last_msg: 'Check Telegram Premium benefits',
    last_time: '',
    unread: 0,
  },
  {
    peer: '@GiftsBot',
    title: 'Telegram Gifts',
    is_bot: true,
    icon: '🎁',
    color: '#7B61FF',
    last_msg: 'Browse and send gifts',
    last_time: '',
    unread: 0,
  },
  {
    peer: '@xusanboyman200',
    title: 'xusanboyman200',
    is_bot: false,
    icon: '👤',
    color: '#10B981',
    last_msg: 'Contact for direct gift transfers',
    last_time: '',
    unread: 0,
  },
];

// Format message text (markdown-like bold, italics, code, links)
function formatTelegramMessageText(text) {
  if (!text) return '';
  let s = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Bold
  s = s.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  s = s.replace(/\*(.+?)\*/g, '<b>$1</b>');
  // Italic
  s = s.replace(/_(.+?)_/g, '<i>$1</i>');
  // Code
  s = s.replace(/`(.+?)`/g, '<code>$1</code>');
  // URLs
  s = s.replace(/(https?:\/\/[^\s<>"]+)/g, '<a href="$1" target="_blank">$1</a>');
  // Newlines
  s = s.replace(/\n/g, '<br>');
  return s;
}

// Setup chat state (returns reactive refs for Vue)
function setupChatState(Vue, api, showToast, tg) {
  const { ref, reactive, computed, watch, nextTick } = Vue;

  // ── Account Selection ──────────────────────────
  const allAvailableAccounts = ref([]); // accounts user can chat as
  const activeChatAccount = ref(null);  // currently selected account
  const showAccountDropdown = ref(false);

  const selectChatAccount = (acc) => {
    activeChatAccount.value = acc;
    showAccountDropdown.value = false;
    // Reload contacts for new account
    loadChatContacts();
  };

  // ── Chat List / Contacts ───────────────────────
  const chatList = ref([...DEFAULT_CHAT_CONTACTS]);
  const chatSearchQuery = ref('');
  const showSearchMenu = ref(false);
  const searchTab = ref('all'); // all, chats, bots, users
  const mobileShowChat = ref(false);

  const filteredChatList = computed(() => {
    let list = chatList.value;
    const q = chatSearchQuery.value.trim().toLowerCase();

    if (searchTab.value === 'bots') {
      list = list.filter(c => c.is_bot);
    } else if (searchTab.value === 'users') {
      list = list.filter(c => !c.is_bot);
    } else if (searchTab.value === 'chats') {
      // chats = has messages
      list = list.filter(c => c.last_msg);
    }

    if (q) {
      list = list.filter(c =>
        (c.title || '').toLowerCase().includes(q) ||
        (c.peer || '').toLowerCase().includes(q) ||
        (c.last_msg || '').toLowerCase().includes(q)
      );
    }
    return list;
  });

  // ── Active Chat Window ─────────────────────────
  const activeChat = ref(null);     // current chat object
  const currentChatPeer = ref('');  // current peer identifier
  const currentMessages = ref([]);  // messages for current chat
  const chatLoading = ref(false);
  const messagesStreamEl = ref(null);

  const scrollToBottom = async () => {
    await nextTick();
    const el = messagesStreamEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  };

  const openChatWindow = async (chat) => {
    activeChat.value = chat;
    currentChatPeer.value = chat.peer;
    mobileShowChat.value = true;
    showSearchMenu.value = false;
    chatSearchQuery.value = '';
    currentMessages.value = [];

    // Load real messages if account available
    if (activeChatAccount.value?.id) {
      await loadChatHistory(chat.peer);
    }
  };

  const loadChatHistory = async (peer) => {
    if (!activeChatAccount.value?.id) return;
    chatLoading.value = true;
    try {
      const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
      const res = await api(`/api/userbot/chat/history?account_id=${encodeURIComponent(accountId)}&recipient=${encodeURIComponent(peer)}`);
      const data = await res.json();
      if (data.success && Array.isArray(data.messages)) {
        currentMessages.value = data.messages;
        // Update contact's last_msg
        const chat = chatList.value.find(c => c.peer === peer);
        if (chat && data.messages.length > 0) {
          const last = data.messages[data.messages.length - 1];
          chat.last_msg = last.text || '';
          chat.last_time = last.date || '';
          chat.last_out = last.out;
        }
      }
    } catch (e) {
      console.error('loadChatHistory error:', e);
    } finally {
      chatLoading.value = false;
      await scrollToBottom();
    }
  };

  const loadChatContacts = async () => {
    if (!activeChatAccount.value?.id) {
      chatList.value = [...DEFAULT_CHAT_CONTACTS];
      return;
    }
    try {
      const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
      const res = await api(`/api/userbot/chat/contacts?account_id=${encodeURIComponent(accountId)}&limit=30`);
      const data = await res.json();
      if (data.success && Array.isArray(data.contacts) && data.contacts.length > 0) {
        chatList.value = data.contacts;
      } else {
        chatList.value = [...DEFAULT_CHAT_CONTACTS];
      }
    } catch (e) {
      console.error('loadChatContacts error:', e);
      chatList.value = [...DEFAULT_CHAT_CONTACTS];
    }
  };

  // ── Sending Messages ───────────────────────────
  const chatInputText = ref('');
  const chatSending = ref(false);
  const showEmojiPicker = ref(false);

  const sendChatMessage = async () => {
    const text = chatInputText.value.trim();
    if (!text || !activeChat.value) return;

    if (!activeChatAccount.value) {
      showToast('⚠️ Please select an account first');
      showAccountDropdown.value = true;
      return;
    }

    // Optimistic UI: add outgoing message immediately
    const tempId = Date.now();
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    currentMessages.value.push({
      id: tempId,
      text,
      out: true,
      date: timeStr,
      sending: true,
    });
    chatInputText.value = '';
    showEmojiPicker.value = false;
    await scrollToBottom();

    chatSending.value = true;
    try {
      const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
      const res = await api('/api/userbot/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          account_id: accountId,
          recipient: currentChatPeer.value,
          message: text,
        }),
      });
      const data = await res.json();
      // Mark as sent
      const msgIdx = currentMessages.value.findIndex(m => m.id === tempId);
      if (msgIdx >= 0) {
        currentMessages.value[msgIdx].sending = false;
        if (data.success) {
          currentMessages.value[msgIdx].id = data.message_id || tempId;
        } else {
          currentMessages.value[msgIdx].failed = true;
          showToast('❌ Failed to send: ' + (data.error || 'Unknown error'));
        }
      }
    } catch (e) {
      const msgIdx = currentMessages.value.findIndex(m => m.id === tempId);
      if (msgIdx >= 0) currentMessages.value[msgIdx].failed = true;
      showToast('❌ Send error: ' + e.message);
    } finally {
      chatSending.value = false;
    }

    // Update contact preview
    const chat = chatList.value.find(c => c.peer === currentChatPeer.value);
    if (chat) {
      chat.last_msg = text;
      chat.last_time = timeStr;
      chat.last_out = true;
    }
  };

  // ── Bot Button Click Handler ───────────────────
  const handleBotButtonClick = async (btn) => {
    if (!btn) return;
    // URL button — open link
    if (btn.url) {
      if (tg?.openLink) {
        tg.openLink(btn.url);
      } else {
        window.open(btn.url, '_blank');
      }
      return;
    }
    // Inline callback button — send as message
    if (btn.text) {
      showToast(`⚡ Button: "${btn.text}"`);
      if (activeChatAccount.value && activeChat.value) {
        chatInputText.value = btn.text;
        await sendChatMessage();
      }
    }
  };

  // ── Attachment / File handling ─────────────────
  const triggerAttachment = () => {
    showToast('📎 File sharing coming soon!');
  };

  return {
    allAvailableAccounts,
    activeChatAccount,
    showAccountDropdown,
    selectChatAccount,
    chatList,
    chatSearchQuery,
    showSearchMenu,
    searchTab,
    mobileShowChat,
    filteredChatList,
    activeChat,
    currentChatPeer,
    currentMessages,
    chatLoading,
    messagesStreamEl,
    chatInputText,
    chatSending,
    showEmojiPicker,
    openChatWindow,
    loadChatHistory,
    loadChatContacts,
    sendChatMessage,
    handleBotButtonClick,
    triggerAttachment,
    formatTelegramMessageText,
    DEFAULT_CHAT_CONTACTS,
  };
}
