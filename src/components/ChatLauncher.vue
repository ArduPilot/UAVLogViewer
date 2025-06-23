<template>
  <button
    class="chat-launcher-btn"
    @click="$emit('open')"
    title="Chat with Flight Assistant"
  >
    <div class="launcher-content">
      <svg viewBox="0 0 24 24" fill="currentColor" class="plane-icon">
        <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
      </svg>
      <span class="launcher-text">Flight Assistant</span>
    </div>
  </button>
</template>

<script>
export default {
  name: 'ChatLauncher'
}
</script>

<style scoped>
.chat-launcher-btn {
  position: fixed;
  bottom: 30px;
  right: 30px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 50px;
  padding: 16px 24px;
  cursor: pointer;
  box-shadow: 0 8px 32px rgba(102, 126, 234, 0.4);
  z-index: 1100;
  transition: all 0.3s ease;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  display: flex;
  align-items: center;
  gap: 12px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.chat-launcher-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.6);
  background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
}

.chat-launcher-btn:active {
  transform: translateY(0);
}

.launcher-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plane-icon {
  width: 24px;
  height: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-3px); }
}

.launcher-text {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

/* Responsive design */
@media (max-width: 768px) {
  .chat-launcher-btn {
    bottom: 20px;
    right: 20px;
    padding: 14px 20px;
  }
  
  .launcher-text {
    display: none;
  }
  
  .plane-icon {
    width: 28px;
    height: 28px;
  }
}

@media (max-width: 480px) {
  .chat-launcher-btn {
    bottom: 15px;
    right: 15px;
    padding: 12px 16px;
  }
}
</style>