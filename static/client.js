// ============================================
// Session Management
// ============================================
const SESSION_KEY = 'catalog_agent_session_id';
let sessionId = localStorage.getItem(SESSION_KEY);
if (!sessionId) {
    sessionId = globalThis.crypto?.randomUUID?.() || `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(SESSION_KEY, sessionId);
}

// ============================================
// Tab Configuration
// ============================================
const TAB_CONFIG = {
    catalogo: {
        title: 'Catálogo',
        description: 'Olá! Posso ajudar você a encontrar calcinhas, ver preços, tamanhos e cores disponíveis.',
        examples: [
            'Quero ver calcinhas de renda',
            'Qual o preço do fio dental preto?',
            'Tem tamanho M disponível?',
            'Quais cores tem a hot pants?',
        ],
    },
    financeiro: {
        title: 'Financeiro',
        description: 'Consulte pagamentos, parcelas, faturamento e informações financeiras.',
        examples: [
            'Quais formas de pagamento?',
            'Posso parcelar em quantas vezes?',
            'Tem desconto no PIX?',
            'Qual o valor mínimo para frete grátis?',
        ],
    },
    pdv: {
        title: 'PDV',
        description: 'Registre vendas, consulte estoque e finalize pedidos.',
        examples: [
            'Registrar venda de 2 fio dental M preto',
            'Consultar estoque do produto 5',
            'Fechar pedido da cliente Maria',
            'Gerar resumo do dia',
        ],
    },
};

let activeTab = 'catalogo';

// ============================================
// DOM Elements
// ============================================
const chatPlaceholder = document.getElementById('chat-placeholder');
const messagesDiv = document.getElementById('messages');
const chatMessagesArea = document.querySelector('.chat-messages-area');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const messageForm = document.getElementById('message-form');
const typingIndicator = document.getElementById('typing-indicator');
const placeholderTitle = document.getElementById('placeholder-title');
const placeholderDescription = document.getElementById('placeholder-description');
const formatHelp = document.getElementById('format-help');

let isProcessing = false;

// ============================================
// Tab Navigation
// ============================================
function switchTab(tabName) {
    if (tabName === activeTab) return;

    activeTab = tabName;

    // Update active tab styling
    document.querySelectorAll('.nav-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update placeholder content
    const config = TAB_CONFIG[tabName];
    placeholderTitle.textContent = config.title;
    placeholderDescription.textContent = config.description;

    // Update examples
    const examplesHtml = config.examples
        .map((ex) => `<code>${ex}</code>`)
        .join('<br>');
    formatHelp.innerHTML = `<strong>Exemplos de perguntas:</strong><br>${examplesHtml}`;

    // Clear current chat (cada tab é uma conversa separada)
    clearChat();

    // Rebind format-help click events
    bindFormatHelpClicks();

    messageInput.focus();
}

function clearChat() {
    messagesDiv.innerHTML = '';
    messagesDiv.classList.add('hidden');
    chatPlaceholder.classList.remove('hidden');
    hideTyping();
}

function bindFormatHelpClicks() {
    document.querySelectorAll('.format-help code').forEach((code) => {
        code.addEventListener('click', () => {
            messageInput.value = code.textContent;
            messageInput.focus();
            autoResize();
            updateSendButton();
        });
    });
}

// Initialize tab listeners
document.querySelectorAll('.nav-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
        switchTab(tab.dataset.tab);
    });
});

// ============================================
// Chat Functions
// ============================================
function updateSendButton() {
    const hasText = messageInput.value.trim().length > 0;
    const shouldEnable = hasText && !isProcessing;
    sendBtn.disabled = !shouldEnable;
}

function formatTime() {
    return new Date().toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMessage(text) {
    let formatted = escapeHtml(text);
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/`(.*?)`/g, '<code>$1</code>');
    formatted = formatted.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank">$1</a>'
    );
    return formatted;
}

function scrollChatToBottom() {
    requestAnimationFrame(() => {
        chatMessagesArea.scrollTo({
            top: chatMessagesArea.scrollHeight,
            behavior: 'smooth',
        });
    });
}

function addMessage(text, isOwn = false, messageId = 0) {
    chatPlaceholder.classList.add('hidden');
    messagesDiv.classList.remove('hidden');

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isOwn ? 'own' : 'bot'}`;
    if (messageId) {
        msgDiv.dataset.msgId = messageId;
    }

    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.innerHTML = formatMessage(text);

    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = formatTime();

    msgDiv.appendChild(textDiv);
    msgDiv.appendChild(timeDiv);

    // Add feedback buttons for bot messages with valid messageId
    if (!isOwn && messageId) {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-row';
        feedbackDiv.innerHTML = `
            <button class="feedback-btn" onclick="submitFeedback(${messageId}, 1)" title="Útil">👍</button>
            <button class="feedback-btn" onclick="submitFeedback(${messageId}, -1)" title="Não útil">👎</button>
        `;
        msgDiv.appendChild(feedbackDiv);
    }

    messagesDiv.appendChild(msgDiv);
    scrollChatToBottom();
}

async function loadHistory() {
    try {
        const response = await fetch(`/v1/chat/history/${encodeURIComponent(sessionId)}`);
        if (!response.ok) {
            throw new Error(`Erro ${response.status}`);
        }

        const history = await response.json();
        history.forEach((message) => {
            addMessage(message.content, message.role === 'user', message.id);
        });
    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
    }
}

function showTyping() {
    typingIndicator.classList.remove('hidden');
    scrollChatToBottom();
}

function hideTyping() {
    typingIndicator.classList.add('hidden');
}

async function sendMessage(text) {
    if (isProcessing || !text.trim()) return;

    isProcessing = true;
    updateSendButton();
    messageInput.value = '';
    autoResize();
    updateSendButton();

    addMessage(text, true);
    showTyping();

    try {
        const response = await fetch('/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text.trim(),
                session_id: sessionId,
                context: activeTab,
            }),
        });

        if (!response.ok) {
            throw new Error(`Erro ${response.status}`);
        }

        const data = await response.json();
        hideTyping();
        addMessage(data.reply, false, data.message_id);
    } catch (error) {
        hideTyping();
        addMessage(
            'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.',
            false
        );
        console.error('Erro ao enviar mensagem:', error);
    } finally {
        isProcessing = false;
        updateSendButton();
        messageInput.focus();
    }
}

function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

// ============================================
// Event Listeners
// ============================================
messageInput.addEventListener('input', () => {
    autoResize();
    updateSendButton();
});

messageInput.addEventListener('keyup', () => {
    updateSendButton();
});

messageForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (text && !isProcessing) {
        sendMessage(text);
    }
});

sendBtn.addEventListener('click', () => {
    const text = messageInput.value.trim();
    if (text && !isProcessing) {
        sendMessage(text);
    }
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const text = messageInput.value.trim();
        if (text && !isProcessing) {
            sendMessage(text);
        }
    }
});

// ============================================
// Init
// ============================================
bindFormatHelpClicks();
messageInput.focus();
updateSendButton();
loadHistory();

// ============================================
// RAG Reindex
// ============================================
let isReindexing = false;

function startReindex() {
  if (isReindexing) return;

  const btn = document.getElementById("btn-reindex");
  const progress = document.getElementById("reindex-progress");
  const fill = document.getElementById("reindex-fill");
  const text = document.getElementById("reindex-text");

  isReindexing = true;
  btn.classList.add("reindexing");
  progress.classList.remove("hidden");
  fill.style.width = "0%";
  text.textContent = "Iniciando reindexação...";

  const evtSource = new EventSource("/v1/rag/reindex");

  evtSource.onmessage = (event) => {
    if (event.data === "[DONE]") {
      evtSource.close();
      isReindexing = false;
      btn.classList.remove("reindexing");
      fill.style.width = "100%";
      fill.style.background = "var(--wa-green)";
      text.textContent = "✅ Reindexação concluída!";
      setTimeout(() => {
        progress.classList.add("hidden");
        fill.style.background = "";
      }, 3000);
      return;
    }

    try {
      const data = JSON.parse(event.data);
      const pct = data.total > 0 ? Math.round((data.current / data.total) * 100) : 0;
      fill.style.width = pct + "%";
      text.textContent = data.message;
    } catch (e) {
      text.textContent = event.data;
    }
  };

  evtSource.onerror = () => {
    evtSource.close();
    isReindexing = false;
    btn.classList.remove("reindexing");
    fill.style.width = "100%";
    fill.style.background = "var(--wa-red)";
    text.textContent = "❌ Erro na reindexação";
    setTimeout(() => {
      progress.classList.add("hidden");
      fill.style.background = "";
    }, 3000);
  };
}

// ============================================
// RLHF Feedback
// ============================================
function showFeedbackModal(messageId, rating) {
  // Remove existing modal if any
  const existing = document.getElementById('feedback-modal');
  if (existing) existing.remove();

  const ratingLabel = rating === 1 ? 'Útil 👍' : 'Não útil 👎';
  const ratingColor = rating === 1 ? 'var(--wa-green)' : 'var(--wa-red)';

  const modal = document.createElement('div');
  modal.id = 'feedback-modal';
  modal.className = 'feedback-modal-overlay';
  modal.innerHTML = `
    <div class="feedback-modal">
      <div class="feedback-modal-header" style="border-left: 4px solid ${ratingColor}">
        <span class="feedback-modal-title">Feedback: ${ratingLabel}</span>
        <button class="feedback-modal-close" onclick="closeFeedbackModal()">&times;</button>
      </div>
      <div class="feedback-modal-body">
        <label for="feedback-comment">Comentário (opcional):</label>
        <textarea id="feedback-comment" rows="3" placeholder="O que podemos melhorar?"></textarea>
      </div>
      <div class="feedback-modal-footer">
        <button class="feedback-modal-btn cancel" onclick="closeFeedbackModal()">Cancelar</button>
        <button class="feedback-modal-btn submit" style="background: ${ratingColor}" onclick="confirmFeedback(${messageId}, ${rating})">Enviar</button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Focus on textarea
  setTimeout(() => {
    const textarea = document.getElementById('feedback-comment');
    if (textarea) textarea.focus();
  }, 100);

  // Close on overlay click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeFeedbackModal();
  });

  // Close on Escape
  document.addEventListener('keydown', function escHandler(e) {
    if (e.key === 'Escape') {
      closeFeedbackModal();
      document.removeEventListener('keydown', escHandler);
    }
  });
}

function closeFeedbackModal() {
  const modal = document.getElementById('feedback-modal');
  if (modal) modal.remove();
}

async function confirmFeedback(messageId, rating) {
  const commentEl = document.getElementById('feedback-comment');
  const comment = commentEl ? commentEl.value.trim() : '';
  closeFeedbackModal();
  await submitFeedbackWithComment(messageId, rating, comment);
}

async function submitFeedbackWithComment(messageId, rating, comment = '') {
  if (!messageId) return;

  try {
    const response = await fetch('/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message_id: messageId,
        session_id: sessionId,
        rating: rating,
        comment: comment,
      }),
    });

    if (!response.ok) {
      throw new Error(`Erro ${response.status}`);
    }

    const data = await response.json();

    if (data.status === 'already_feedbacked') {
      return;
    }

    // Update UI: highlight selected button, disable both
    const msgDiv = document.querySelector(`[data-msg-id="${messageId}"]`);
    if (msgDiv) {
      const feedbackRow = msgDiv.querySelector('.feedback-row');
      if (feedbackRow) {
        const buttons = feedbackRow.querySelectorAll('.feedback-btn');
        buttons.forEach(btn => {
          btn.disabled = true;
          btn.classList.add('disabled');
        });

        // Highlight the selected one
        if (rating === 1) {
          buttons[0].classList.add('active-positive');
        } else {
          buttons[1].classList.add('active-negative');
        }

        // Show comment if provided
        if (comment) {
          const commentDiv = document.createElement('div');
          commentDiv.className = 'feedback-comment';
          commentDiv.textContent = comment;
          feedbackRow.appendChild(commentDiv);
        }
      }
    }
  } catch (error) {
    console.error('Erro ao enviar feedback:', error);
  }
}

// Keep old function for backward compatibility
async function submitFeedback(messageId, rating) {
  showFeedbackModal(messageId, rating);
}