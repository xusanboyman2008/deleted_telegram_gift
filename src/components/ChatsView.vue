<template>
  <div class="view" style="padding: 0; display: flex; flex-direction: column; height: calc(100vh - 120px);">
    <div class="tg-chat-app" style="display: flex; width: 100%; height: 100%; position: relative; overflow: hidden;">
      
      <!-- ── Contacts Sidebar List ───────────────── -->
      <div :class="['tg-chat-sidebar', mobileShowChat ? 'mobile-hidden' : '']" style="flex: 1; max-width: 380px; width: 100%; display: flex; flex-direction: column; border-right: 1px solid rgba(255,255,255,0.06); background: rgba(13, 14, 26, 0.6);">
        
        <!-- Search & Filter Bar -->
        <div class="tg-search-bar-wrap" style="padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05);">
          <div class="tg-search-input-box" style="display: flex; align-items: center; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 6px 12px; gap: 8px;">
            <span style="opacity: 0.5; font-size: 0.9rem;">🔍</span>
            <input
              type="text"
              v-model="searchQuery"
              placeholder="Search chats, bots, username..."
              style="background: transparent; border: none; outline: none; color: #fff; width: 100%; font-size: 0.85rem;"
            />
            <button v-if="searchQuery" @click="searchQuery = ''" style="background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer;">✕</button>
          </div>

          <!-- Category Filter Tabs -->
          <div class="tg-search-tabs" style="display: flex; gap: 6px; margin-top: 10px; overflow-x: auto; padding-bottom: 2px;">
            <button
              v-for="st in ['all', 'chats', 'bots', 'users']"
              :key="st"
              :class="['tg-stab-btn', searchTab === st ? 'active' : '']"
              @click="searchTab = st"
              style="padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: 600; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.6); cursor: pointer; text-transform: capitalize;"
            >
              {{ st }}
            </button>
          </div>
        </div>

        <!-- Contacts Item List -->
        <div class="tg-contacts-scroll" style="flex: 1; overflow-y: auto; padding: 6px;">
          <div
            v-for="chat in filteredChatList"
            :key="chat.peer"
            v-memo="[chat.peer, chat.last_msg, chat.last_time, chat.unread, (currentChatPeer === chat.peer)]"
            :class="['tg-chat-item', currentChatPeer === chat.peer ? 'active' : '']"
            @click="$emit('select-chat', chat)"
            style="display: flex; align-items: center; padding: 10px 12px; border-radius: 12px; margin-bottom: 4px; cursor: pointer; transition: background 0.15s ease;"
          >
            <div class="tg-ci-avatar-wrap" style="position: relative; margin-right: 12px;">
              <img v-if="chat.photo" :src="chat.photo" class="tg-ci-avatar" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover;" alt="chat" />
              <div v-else class="tg-ci-avatar-placeholder" :style="{ background: chat.color || '#3390ec', width: '44px', height: '44px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700', color: '#fff', fontSize: '1rem' }">
                {{ chat.icon || (chat.title || 'C')[0] }}
              </div>
              <span v-if="chat.online" class="tg-ci-online-dot" style="position: absolute; bottom: 1px; right: 1px; width: 10px; height: 10px; background: #10B981; border: 2px solid #0D0E1A; border-radius: 50%;"></span>
            </div>
            <div class="tg-ci-content" style="flex: 1; min-width: 0;">
              <div class="tg-ci-top" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                <span class="tg-ci-title" style="font-weight: 600; color: #fff; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                  {{ chat.title }}
                </span>
                <span class="tg-ci-time" style="font-size: 0.72rem; color: rgba(255,255,255,0.4);">
                  {{ chat.last_time }}
                </span>
              </div>
              <div class="tg-ci-bottom" style="display: flex; justify-content: space-between; align-items: center;">
                <span class="tg-ci-preview" style="font-size: 0.8rem; color: rgba(255,255,255,0.5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                  {{ chat.last_msg || 'No messages yet' }}
                </span>
                <span v-if="chat.unread" class="tg-ci-badge" style="background: #3390ec; color: #fff; font-size: 0.7rem; font-weight: 700; padding: 2px 6px; border-radius: 10px; margin-left: 6px;">
                  {{ chat.unread }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Chat Main Conversation Window ──────── -->
      <div :class="['tg-chat-main', !mobileShowChat ? 'mobile-hidden' : '']" style="flex: 2; display: flex; flex-direction: column; background: rgba(10, 11, 20, 0.95);">
        
        <!-- Header -->
        <div v-if="activeChat" class="tg-chat-header" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(13, 14, 26, 0.8);">
          <div style="display: flex; align-items: center; gap: 12px;">
            <button @click="$emit('close-mobile-chat')" class="tg-back-btn" style="background: none; border: none; color: #fff; font-size: 1.2rem; cursor: pointer;">←</button>
            <img v-if="activeChat.photo" :src="activeChat.photo" style="width: 38px; height: 38px; border-radius: 50%; object-fit: cover;" alt="avatar" />
            <div v-else style="width: 38px; height: 38px; border-radius: 50%; background: #3390ec; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700;">
              {{ activeChat.icon || (activeChat.title || 'C')[0] }}
            </div>
            <div>
              <div style="font-weight: 700; color: #fff; font-size: 0.92rem;">{{ activeChat.title }}</div>
              <div style="font-size: 0.75rem; color: rgba(255,255,255,0.4);">
                {{ activeChat.online ? 'online' : activeChat.is_bot ? 'bot' : 'user' }}
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state when no chat selected -->
        <div v-else style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: rgba(255,255,255,0.3);">
          <div style="font-size: 3rem; margin-bottom: 10px;">💬</div>
          <div>Select a chat to start messaging</div>
        </div>

        <!-- Message Stream Scroll Container -->
        <div v-if="activeChat" ref="messagesStreamEl" class="tg-msg-stream" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
          
          <div v-if="chatLoading" class="tg-skeleton-container" style="display: flex; flex-direction: column; gap: 12px;">
            <div class="shimmer-skeleton" style="width: 60%; height: 42px; border-radius: 12px;"></div>
            <div class="shimmer-skeleton" style="width: 45%; height: 36px; border-radius: 12px; align-self: flex-end;"></div>
            <div class="shimmer-skeleton" style="width: 70%; height: 50px; border-radius: 12px;"></div>
          </div>

          <div
            v-else-if="currentMessages"
            v-for="msg in currentMessages"
            :key="msg.id"
            v-memo="[msg.id, msg.text, msg.out, msg.time, msg.sending, msg.failed]"
            :class="['tg-msg-bubble', msg.out ? 'outgoing' : 'incoming']"
            style="max-width: 75%; padding: 10px 14px; border-radius: 14px; font-size: 0.88rem; line-height: 1.4; position: relative;"
            :style="{
              alignSelf: msg.out ? 'flex-end' : 'flex-start',
              background: msg.out ? 'linear-gradient(135deg, #2563EB, #1D4ED8)' : 'rgba(255,255,255,0.06)',
              color: '#fff'
            }"
          >
            <!-- Media Attachment -->
            <img v-if="msg.photo" :src="msg.photo" style="max-width: 100%; border-radius: 10px; margin-bottom: 6px; display: block;" alt="photo" />
            <div>{{ msg.text }}</div>
            <div style="font-size: 0.68rem; opacity: 0.6; text-align: right; margin-top: 4px;">{{ msg.time }}</div>
          </div>
        </div>

        <!-- Message Input Bar -->
        <div v-if="activeChat" class="tg-chat-input-bar" style="padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; align-items: center; gap: 10px; background: rgba(13, 14, 26, 0.9);">
          <input
            type="text"
            v-model="inputMsgText"
            placeholder="Write a message..."
            @keyup.enter="$emit('send-msg', inputMsgText); inputMsgText = ''"
            style="flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 10px 14px; color: #fff; outline: none; font-size: 0.88rem;"
          />
          <button
            @click="$emit('send-msg', inputMsgText); inputMsgText = ''"
            style="background: #2563EB; color: #fff; border: none; padding: 10px 16px; border-radius: 12px; font-weight: 700; cursor: pointer;"
          >
            Send
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

defineProps({
  filteredChatList: { type: Array, required: true },
  currentChatPeer: { type: String, default: '' },
  activeChat: { type: Object, default: null },
  currentMessages: { type: Array, default: () => [] },
  chatLoading: { type: Boolean, default: false },
  mobileShowChat: { type: Boolean, default: false }
});

defineEmits(['select-chat', 'close-mobile-chat', 'send-msg']);

const searchQuery = ref('');
const searchTab = ref('all');
const inputMsgText = ref('');
</script>
