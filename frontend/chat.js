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
  // Telegram links (t.me/username)
  s = s.replace(/(https?:\/\/)?(?:t\.me|telegram\.me)\/([a-zA-Z0-9_]{4,32})/gi, '<a href="#" class="tg-username-link" data-peer="$2">t.me/$2</a>');
  // Usernames: @username
  s = s.replace(/(^|[^a-zA-Z0-9_="/])@([a-zA-Z0-9_]{4,32})/g, '$1<a href="#" class="tg-username-link" data-peer="$2">@$2</a>');
  // General HTTP/HTTPS URLs
  s = s.replace(/(?<!href=")(https?:\/\/[^\s<>"]+)/g, '<a href="$1" target="_blank">$1</a>');
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

  let chatSocket = null;

  const selectChatAccount = (acc) => {
    activeChatAccount.value = acc;
    showAccountDropdown.value = false;
    activeChat.value = null;
    currentChatPeer.value = null;
    if (chatSocket) {
      try {
        chatSocket.close();
      } catch (e) {}
      chatSocket = null;
    }
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
  const messagesStreamEl = ref(null);

  // Profile Drawer / Modal State
  const profileModal = reactive({
    show: false,
    loading: false,
    data: null,
  });

  const openProfileModal = async (peer) => {
    const targetPeer = peer || currentChatPeer.value;
    if (!targetPeer) return;
    profileModal.show = true;
    profileModal.loading = true;
    profileModal.data = null;
    try {
      const accountId = activeChatAccount.value?.raw_id || activeChatAccount.value?.id || 1;
      const res = await api(`/api/userbot/chat/profile?account_id=${encodeURIComponent(accountId)}&recipient=${encodeURIComponent(targetPeer)}`);
      const data = await res.json();
      if (data.success) {
        profileModal.data = data;
      }
    } catch (e) {
      console.error('Failed to load profile modal:', e);
    } finally {
      profileModal.loading = false;
    }
  };

  const scrollToBottom = async () => {
    await nextTick();
    const el = messagesStreamEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  };

  const connectChatSocket = (peer) => {
    if (chatSocket) {
      try {
        chatSocket.close();
      } catch (e) {}
      chatSocket = null;
    }

    if (!activeChatAccount.value?.id) return;

    const initData = tg?.initData || '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
    const wsUrl = `${protocol}//${host}/api/ws/chat?account_id=${encodeURIComponent(accountId)}&recipient=${encodeURIComponent(peer)}&init_data=${encodeURIComponent(initData)}`;

    const ws = new WebSocket(wsUrl);
    chatSocket = ws;

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'message' && data.message) {
          // Check if matches an optimistic/sending message
          const optIdx = currentMessages.value.findIndex(m => m.sending && m.text === data.message.text);
          if (optIdx >= 0) {
            currentMessages.value[optIdx].id = data.message.id;
            currentMessages.value[optIdx].sending = false;
          } else {
            const exists = currentMessages.value.some(m => m.id === data.message.id);
            if (!exists) {
              currentMessages.value.push(data.message);
              await scrollToBottom();
            }
          }

          // Also update contact's preview in the sidebar list!
          const chat = chatList.value.find(c => c.peer.toLowerCase() === peer.toLowerCase());
          if (chat) {
            chat.last_msg = data.message.text || '';
            chat.last_time = data.message.date || '';
            chat.last_out = data.message.out;
          }
        }
      } catch (err) {
        console.error('WS message processing failed:', err);
      }
    };

    let pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        try { ws.send('ping'); } catch {}
      }
    }, 20000);

    ws.onclose = () => {
      clearInterval(pingInterval);
      // Reconnect after 5s if still active on this chat and socket matches
      if (chatSocket === ws && activeChat.value && activeChat.value.peer === peer) {
        setTimeout(() => {
          if (activeChat.value && activeChat.value.peer === peer) {
            connectChatSocket(peer);
          }
        }, 5000);
      }
    };
  };

  const openChatWindow = async (chat) => {
    activeChat.value = chat;
    currentChatPeer.value = chat.peer;
    mobileShowChat.value = true;
    showSearchMenu.value = false;
    chatSearchQuery.value = '';
    currentMessages.value = [];

    // Clear unread badge
    chat.unread = 0;

    // Load real messages & read chat history if account available
    if (activeChatAccount.value?.id) {
      const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
      api('/api/userbot/chat/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId, recipient: chat.peer })
      }).catch(() => {});

      await loadChatHistory(chat.peer);
      connectChatSocket(chat.peer);
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

  // ── Start Chat With Query (Usernames or numeric Telegram IDs) ──────────
  const startChatWithQuery = (query) => {
    let clean = query.trim();
    if (!clean) return;

    // Check if it's a numeric ID or a username
    let peer = clean;
    if (!clean.startsWith('@') && isNaN(clean)) {
      peer = '@' + clean;
    }

    // Check if already in list
    let existing = chatList.value.find(c => c.peer.toLowerCase() === peer.toLowerCase());
    if (existing) {
      openChatWindow(existing);
      return;
    }

    // Otherwise, create a temporary chat contact
    const isBot = peer.toLowerCase().endsWith('bot');
    const newChat = {
      peer: peer,
      title: peer,
      is_bot: isBot,
      icon: isBot ? '🤖' : '👤',
      color: isBot ? '#7B61FF' : '#10B981',
      last_msg: isBot ? 'Bot started. Press START to interact.' : 'Tap to start conversation...',
      last_time: '',
      unread: 0
    };

    // Add to chatList and open it!
    chatList.value.unshift(newChat);
    openChatWindow(newChat);
  };

  // ── Send Bot START Command ─────────────────────
  const sendStartCommand = async () => {
    chatInputText.value = '/start';
    await sendChatMessage();
  };

  // ── Message Stream Click Handler (Username Click Link Delegation) ─────
  const handleMessageStreamClick = (e) => {
    const link = e.target.closest('.tg-username-link');
    if (link) {
      e.preventDefault();
      const peer = link.getAttribute('data-peer');
      if (peer) {
        startChatWithQuery(peer);
      }
    }
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
    startChatWithQuery,
    sendStartCommand,
    handleMessageStreamClick,
    profileModal,
    openProfileModal,
  };
}
