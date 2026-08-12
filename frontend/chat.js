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

  // Contacts pagination state
  const contactsLimit = 30;
  const contactsOffset = ref(0);
  const contactsHasMore = ref(true);
  const chatContactsLoadingMore = ref(false);

  let chatSocket = null;

  const selectChatAccount = (acc, forceConnect = false) => {
    activeChatAccount.value = acc;
    showAccountDropdown.value = false;
    activeChat.value = null;
    currentChatPeer.value = null;
    contactsOffset.value = 0;
    contactsHasMore.value = true;
    if (chatSocket) {
      try {
        chatSocket.close();
      } catch (e) {}
      chatSocket = null;
    }
    // Connect WebSocket & load contacts ONLY when explicitly requested or on Chats tab
    if (forceConnect) {
      connectGlobalSocket();
      loadChatContacts();
    }
  };

  // ── Chat List / Contacts ───────────────────────
  const chatList = (Vue.shallowRef || Vue.ref)([...DEFAULT_CHAT_CONTACTS]);
  const chatSearchQuery = ref('');
  const showSearchMenu = ref(false);
  const searchTab = ref('all'); // all, chats, bots, users
  const mobileShowChat = ref(false);

  const filteredChatList = computed(() => {
    let list = chatList.value;
    const q = chatSearchQuery.value.trim().toLowerCase();
    if (!q && searchTab.value === 'all') return list;

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
  const currentMessages = (Vue.shallowRef || Vue.ref)([]);  // messages for current chat
  const messagesStreamEl = ref(null);
  const chatLoading = ref(false);

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

  // Global WebSocket for Real-Time Notification & Live Chat Sync
  let globalSocket = null;
  const connectGlobalSocket = () => {
    if (globalSocket) return;
    const initData = tg?.initData || '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/global?init_data=${encodeURIComponent(initData)}`;
    try {
      const ws = new WebSocket(wsUrl);
      globalSocket = ws;
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'message' && data.message) {
            const currentPeer = currentChatPeer.value ? currentChatPeer.value.toLowerCase().replace('@','') : '';
            const incomingPeer = data.peer ? data.peer.toLowerCase().replace('@','') : '';
            if (currentPeer && incomingPeer && (currentPeer === incomingPeer || currentPeer.includes(incomingPeer))) {
              const exists = currentMessages.value.some(m => m.id === data.message.id);
              if (!exists) {
                currentMessages.value.push(data.message);
                scrollToBottom();
              }
            }
            const chat = chatList.value.find(c => c.peer.toLowerCase().replace('@','') === incomingPeer);
            if (chat) {
              chat.last_msg = data.message.text || 'Message';
              chat.last_time = data.message.date || '';
              chat.last_out = data.message.out;
            }
          } else if (data.event === 'bot_message' && data.message) {
            if (typeof window.handleGlobalBotMessage === 'function') {
              window.handleGlobalBotMessage(data);
            }
            // Direct handle in chatState if active account is the bot
            if (activeChatAccount.value?.is_managed_bot && activeChatAccount.value.token === data.bot_token) {
              const incomingUserId = String(data.user_id);
              if (currentChatPeer.value === incomingUserId) {
                const exists = currentMessages.value.some(m => m.id === data.message.id);
                if (!exists) {
                  currentMessages.value.push({
                    id: data.message.id,
                    text: data.message.text || '',
                    photo: data.message.media_type === 'photo' ? data.message.media_data : (data.message.photo || null),
                    voice: (data.message.media_type === 'voice' || data.message.media_type === 'audio') ? data.message.media_data : (data.message.voice || null),
                    video: data.message.media_type === 'video' ? data.message.media_data : (data.message.video || null),
                    sticker: data.message.media_type === 'sticker' ? data.message.media_data : null,
                    document: data.message.media_type === 'document' ? data.message.media_data : null,
                    file_name: data.message.file_name || null,
                    out: !!data.message.out,
                    sender_name: data.message.out ? 'Bot' : (data.message.user_first_name || 'User'),
                    date: data.message.date || '',
                  });
                  scrollToBottom();
                }
              }
              const chat = chatList.value.find(c => c.peer === incomingUserId);
              if (chat) {
                chat.last_msg = data.message.text || '';
                chat.last_time = data.message.date || '';
                chat.last_out = !!data.message.out;
              } else {
                loadChatContacts();
              }
            }
          }
        } catch (e) {}
      };
      setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) { try { ws.send('ping'); } catch {} }
      }, 20000);
      ws.onclose = () => {
        globalSocket = null;
        if (activeChatAccount.value) {
          setTimeout(connectGlobalSocket, 5000);
        }
      };
    } catch (e) {}
  };

  const disconnectAllSockets = () => {
    if (chatSocket) {
      try {
        chatSocket.onclose = null;
        chatSocket.close();
      } catch (e) {}
      chatSocket = null;
    }
    if (globalSocket) {
      try {
        globalSocket.onclose = null;
        globalSocket.close();
      } catch (e) {}
      globalSocket = null;
    }
  };

  onMounted(() => {
    // Intentionally empty: WebSocket is not opened on app launch.
    // It opens ONLY when user opens Chats and selects an account!
  });

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

        // Handle send acknowledgement
        if (data.event === 'send_ack') {
          if (data.success && data.message_id) {
            // Find the optimistic sending message and update its id
            const optIdx = currentMessages.value.findIndex(m => m.sending);
            if (optIdx >= 0) {
              currentMessages.value[optIdx].id = data.message_id;
              currentMessages.value[optIdx].sending = false;
            }
          } else if (!data.success) {
            const optIdx = currentMessages.value.findIndex(m => m.sending);
            if (optIdx >= 0) {
              currentMessages.value[optIdx].failed = true;
              currentMessages.value[optIdx].sending = false;
            }
            showToast('❌ Send failed: ' + (data.error || 'Unknown error'));
          }
          chatSending.value = false;
          return;
        }

        if (data.event === 'message' && data.message) {
          // Check if this is our own outgoing message echoed back
          if (data.message.out) {
            // Try to match with optimistic message by text content
            const optIdx = currentMessages.value.findIndex(m => 
              (m.sending || m.id === data.message.id) && m.text === data.message.text
            );
            if (optIdx >= 0) {
              // Update the optimistic message with server data
              currentMessages.value[optIdx].id = data.message.id;
              currentMessages.value[optIdx].sending = false;
              currentMessages.value[optIdx].photo = data.message.photo || null;
              currentMessages.value[optIdx].voice = data.message.voice || null;
              return; // Don't add duplicate
            }
            // Check if already exists by message id
            const exists = currentMessages.value.some(m => m.id === data.message.id);
            if (exists) return;
          }

          // For incoming messages, check for duplicates
          const exists = currentMessages.value.some(m => m.id === data.message.id);
          if (!exists) {
            currentMessages.value.push(data.message);
            await scrollToBottom();
          }

          // Update contact's preview in the sidebar
          const chat = chatList.value.find(c => c.peer.toLowerCase().replace('@','') === peer.toLowerCase().replace('@',''));
          if (chat) {
            chat.last_msg = data.message.text || (data.message.photo ? '📷 Photo' : (data.message.voice ? '🎤 Voice' : ''));
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
      if (activeChatAccount.value.is_managed_bot) {
        await loadChatHistory(chat.peer);
      } else {
        const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
        api('/api/userbot/chat/read', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ account_id: accountId, recipient: chat.peer })
        }).catch(() => {});

        await loadChatHistory(chat.peer);
        connectChatSocket(chat.peer);
      }
    }
  };

  const loadChatHistory = async (peer) => {
    if (!activeChatAccount.value?.id) return;
    chatLoading.value = true;
    try {
      if (activeChatAccount.value.is_managed_bot) {
        const botId = activeChatAccount.value.managed_bot_id;
        const res = await api(`/api/admin/managed-bots/${botId}/history/${encodeURIComponent(peer)}`);
        const data = await res.json();
        if (data.success && Array.isArray(data.messages)) {
          currentMessages.value = data.messages.map(m => ({
            id: m.id || m.message_id,
            text: m.text || '',
            photo: m.media_type === 'photo' ? m.media_data : (m.photo || null),
            voice: (m.media_type === 'voice' || m.media_type === 'audio') ? m.media_data : (m.voice || null),
            video: m.media_type === 'video' ? m.media_data : (m.video || null),
            sticker: m.media_type === 'sticker' ? m.media_data : null,
            document: m.media_type === 'document' ? m.media_data : null,
            file_name: m.file_name || null,
            out: !!m.out,
            sender_name: m.out ? 'Bot' : (m.user_first_name || 'User'),
            date: m.date || '',
          }));
        }
      } else {
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
      }
    } catch (e) {
      console.error('loadChatHistory error:', e);
    } finally {
      chatLoading.value = false;
      await scrollToBottom();
    }
  };

  const chatContactsLoading = ref(false);

  const loadChatContacts = async (loadMore = false) => {
    if (!activeChatAccount.value?.id) {
      chatList.value = [...DEFAULT_CHAT_CONTACTS];
      chatContactsLoading.value = false;
      contactsHasMore.value = false;
      return;
    }

    if (loadMore) {
      if (chatContactsLoadingMore.value || !contactsHasMore.value) return;
      chatContactsLoadingMore.value = true;
    } else {
      chatContactsLoading.value = true;
      contactsOffset.value = 0;
      contactsHasMore.value = true;
    }

    try {
      if (activeChatAccount.value.is_managed_bot) {
        const botId = activeChatAccount.value.managed_bot_id;
        const res = await api(`/api/admin/managed-bots/${botId}/contacts`);
        const data = await res.json();
        if (data.success && Array.isArray(data.contacts)) {
          chatList.value = data.contacts.map(c => ({
            peer: String(c.user_id),
            title: c.user_first_name || (c.user_username ? '@' + c.user_username : 'User'),
            is_bot: false,
            photo: c.user_photo || null,
            last_msg: c.last_msg || '',
            last_time: c.last_time || '',
            last_out: !!c.last_out,
            unread: 0,
            online: false,
            user_id: c.user_id,
            user_username: c.user_username,
            user_first_name: c.user_first_name
          }));
        } else {
          chatList.value = [];
        }
        contactsHasMore.value = false;
      } else {
        const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
        const currentOffset = contactsOffset.value;
        const res = await api(`/api/userbot/chat/contacts?account_id=${encodeURIComponent(accountId)}&limit=${contactsLimit}&offset=${currentOffset}`);
        const data = await res.json();
        if (data.success && Array.isArray(data.contacts)) {
          if (loadMore) {
            const existingPeers = new Set(chatList.value.map(c => c.peer));
            const newContacts = data.contacts.filter(c => !existingPeers.has(c.peer));
            chatList.value = [...chatList.value, ...newContacts];
          } else {
            chatList.value = data.contacts;
          }
          if (data.contacts.length < contactsLimit) {
            contactsHasMore.value = false;
          } else {
            contactsOffset.value += data.contacts.length;
          }
        } else {
          if (!loadMore) {
            chatList.value = [...DEFAULT_CHAT_CONTACTS];
          }
          contactsHasMore.value = false;
        }
      }
    } catch (e) {
      console.error('loadChatContacts error:', e);
      if (!loadMore) {
        chatList.value = activeChatAccount.value?.is_managed_bot ? [] : [...DEFAULT_CHAT_CONTACTS];
      }
      contactsHasMore.value = false;
    } finally {
      chatContactsLoading.value = false;
      chatContactsLoadingMore.value = false;
    }
  };

  const handleContactsScroll = (e) => {
    const el = e.target;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 60) {
      if (!chatContactsLoadingMore.value && contactsHasMore.value && !chatContactsLoading.value) {
        loadChatContacts(true);
      }
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

    if (activeChatAccount.value.is_managed_bot) {
      try {
        const botId = activeChatAccount.value.managed_bot_id;
        const res = await api(`/api/admin/managed-bots/${botId}/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: parseInt(activeChat.value.peer),
            text: text,
            user_username: activeChat.value.user_username || '',
            user_first_name: activeChat.value.user_first_name || 'User',
          })
        });
        const data = await res.json();
        const msgIdx = currentMessages.value.findIndex(m => m.id === tempId);
        if (msgIdx >= 0) {
          currentMessages.value[msgIdx].sending = false;
          if (data.success) {
            currentMessages.value[msgIdx].id = data.message?.id || tempId;
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
    } else {
      // Send through WebSocket if connected, fallback to HTTP
      if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        try {
          chatSocket.send(JSON.stringify({ action: 'send', text: text }));
          // The WS onmessage handler will receive the send_ack and the broadcast message
          // Mark as sent after a short timeout (server will confirm via broadcast)
          setTimeout(() => {
            const msgIdx = currentMessages.value.findIndex(m => m.id === tempId && m.sending);
            if (msgIdx >= 0) {
              currentMessages.value[msgIdx].sending = false;
            }
            chatSending.value = false;
          }, 2000);
        } catch (e) {
          const msgIdx = currentMessages.value.findIndex(m => m.id === tempId);
          if (msgIdx >= 0) currentMessages.value[msgIdx].failed = true;
          showToast('❌ Send error: ' + e.message);
          chatSending.value = false;
        }
      } else {
        // Fallback: HTTP POST
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
      }
    }

    // Update contact preview
    const chat = chatList.value.find(c => c.peer.toLowerCase().replace('@','') === currentChatPeer.value.toLowerCase().replace('@',''));
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
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*,video/*,audio/*,.pdf,.doc,.docx,.zip';
    fileInput.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      if (!activeChat.value || !activeChatAccount.value) {
        showToast('⚠️ Select account and chat first');
        return;
      }

      showToast('⏳ Uploading media...');
      try {
        const formData = new FormData();
        formData.append('file', file);

        const uploadRes = await api('/api/upload-media', {
          method: 'POST',
          body: formData
        });
        const uploadData = await uploadRes.json();
        if (!uploadData.success) {
          showToast('❌ Upload failed: ' + (uploadData.error || 'Error'));
          return;
        }

        const mediaUrl = uploadData.url;
        const mediaType = uploadData.media_type;

        // Optimistic UI for outgoing media
        const tempId = Date.now();
        const now = new Date();
        const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
        const optMsg = {
          id: tempId,
          text: '',
          out: true,
          date: timeStr,
          sending: true,
        };
        if (mediaType === 'photo') optMsg.photo = mediaUrl;
        else if (mediaType === 'video') optMsg.video = mediaUrl;
        else if (mediaType === 'audio') optMsg.voice = mediaUrl;
        else optMsg.text = `📄 ${file.name}`;

        currentMessages.value.push(optMsg);
        await scrollToBottom();

        if (activeChatAccount.value.is_managed_bot) {
          const botId = activeChatAccount.value.managed_bot_id;
          const res = await api(`/api/admin/managed-bots/${botId}/send-media`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: parseInt(activeChat.value.peer),
              media_url: mediaUrl,
              media_type: mediaType === 'audio' ? 'voice' : mediaType,
              caption: '',
              user_username: activeChat.value.user_username || '',
              user_first_name: activeChat.value.user_first_name || 'User',
            })
          });
          const data = await res.json();
          const idx = currentMessages.value.findIndex(m => m.id === tempId);
          if (idx >= 0) {
            currentMessages.value[idx].sending = false;
            if (data.success) {
              currentMessages.value[idx].id = data.message?.id || tempId;
            }
          }
        } else {
          // Send media via WS or HTTP
          const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
          const res = await api('/api/userbot/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              account_id: accountId,
              recipient: currentChatPeer.value,
              message: mediaUrl,
            })
          });
          const data = await res.json();
          const idx = currentMessages.value.findIndex(m => m.id === tempId);
          if (idx >= 0) {
            currentMessages.value[idx].sending = false;
            if (data.success) {
              currentMessages.value[idx].id = data.message_id || tempId;
            }
          }
        }
        showToast('✅ Media sent!');
      } catch (err) {
        showToast('❌ Media send error: ' + err.message);
      }
    };
    fileInput.click();
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

  const clearActiveChatHistory = async () => {
    if (!activeChat.value || !activeChatAccount.value?.id) return;
    if (!confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) return;
    
    chatLoading.value = true;
    try {
      if (activeChatAccount.value.is_managed_bot) {
        const botId = activeChatAccount.value.managed_bot_id;
        const res = await api(`/api/admin/managed-bots/${botId}/history/${encodeURIComponent(activeChat.value.peer)}`, {
          method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
          currentMessages.value = [];
          showToast('🎉 Chat history cleared!');
        } else {
          showToast('❌ ' + (data.error || 'Failed to clear history'));
        }
      } else {
        const accountId = activeChatAccount.value.raw_id || activeChatAccount.value.id;
        const res = await api(`/api/userbot/chat/history?account_id=${encodeURIComponent(accountId)}&recipient=${encodeURIComponent(activeChat.value.peer)}`, {
          method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
          currentMessages.value = [];
          showToast('🎉 Chat history cleared!');
        } else {
          showToast('❌ ' + (data.error || 'Failed to clear history'));
        }
      }
    } catch (e) {
      showToast('❌ Clear history error: ' + e.message);
    } finally {
      chatLoading.value = false;
    }
  };

  return {
    clearActiveChatHistory,
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
    chatContactsLoading,
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
    disconnectAllSockets,
    contactsHasMore,
    chatContactsLoadingMore,
    handleContactsScroll,
  };
}
