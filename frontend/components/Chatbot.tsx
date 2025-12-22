'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Copy, Check, Sparkles, Zap } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  sources?: Array<{title: string; category?: string; relevance?: number}>; 
  rag_used?: boolean;
  streaming?: boolean;
};

const STORAGE_KEY = 'spa_chatbot_messages';
const STREAMING_ENABLED = true; // Toggle streaming feature

function nowId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function sendToApi(text: string, signal: AbortSignal): Promise<string | null> {
  try {
    const data = await apiClient<any>('/api/chatbot/ask', {
      method: 'POST',
      data: { question: text },
      signal,
    });
    const candidate: string | undefined =
      data.response || data.reply || data.answer || data.message || data.content;
    if (candidate && typeof candidate === 'string') return candidate;

    if (Array.isArray(data.messages) && data.messages.length) {
      const last = data.messages[data.messages.length - 1];
      if (typeof last === 'string') return last;
      if (typeof last?.content === 'string') return last.content;
    }

    if (typeof data === 'string' && data && data !== 'null') return data;
  } catch (e) {
    // Network or auth error -> null triggers fallback
  }

  return null;
}

async function* sendToApiStreaming(
  text: string, 
  signal: AbortSignal
): AsyncGenerator<{type: string; content?: string; data?: any}, void, unknown> {
  try {
    const response = await fetch('/api/chatbot/ask/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify({ question: text }),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.slice(6);
            const chunk = JSON.parse(jsonStr);
            yield chunk;
          } catch (e) {
            console.error('Failed to parse SSE chunk:', e);
          }
        }
      }
    }
  } catch (e) {
    console.error('Streaming error:', e);
    throw e;
  }
}

export default function Chatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [apiAvailable, setApiAvailable] = useState<boolean | null>(null);
  const [ragStatus, setRagStatus] = useState<{initialized: boolean; docs: number}>({initialized: false, docs: 0});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  // Load / persist conversation
  useEffect(() => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        const parsed = JSON.parse(cached) as ChatMessage[];
        if (Array.isArray(parsed)) setMessages(parsed);
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch {}
  }, [messages]);

  // Check backend status and RAG
  useEffect(() => {
    const ctrl = new AbortController();
    const run = async () => {
      try {
        const status = await apiClient<any>('/api/chatbot/status', { 
          method: 'GET', 
          signal: ctrl.signal
        });
        setApiAvailable(true);
        setRagStatus({
          initialized: status.rag_initialized || false,
          docs: status.knowledge_documents || 0
        });
      } catch {
        setApiAvailable(false);
      }
    };
    run();
    return () => ctrl.abort();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const placeholder = useMemo(() => {
    return loading ? "Assistant en train d'écrire…" : 'Écrire un message';
  }, [loading]);

  function clearConversation() {
    setMessages([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  function copyMessage(id: string, content: string) {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setInput('');
    
    const userMsg: ChatMessage = {
      id: nowId(),
      role: 'user',
      content: trimmed,
      timestamp: Date.now(),
    };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    if (STREAMING_ENABLED) {
      // Streaming mode
      try {
        const botMsgId = nowId();
        let botContent = '';
        let sources: any[] = [];
        let ragUsed = false;

        // Add initial streaming message
        const streamingMsg: ChatMessage = {
          id: botMsgId,
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          streaming: true,
        };
        setMessages((m) => [...m, streamingMsg]);

        for await (const chunk of sendToApiStreaming(trimmed, abortRef.current.signal)) {
          if (chunk.type === 'content' && chunk.content) {
            botContent += chunk.content;
            // Update message content
            setMessages((m) => 
              m.map((msg) => 
                msg.id === botMsgId 
                  ? { ...msg, content: botContent }
                  : msg
              )
            );
          } else if (chunk.type === 'end' && chunk.data) {
            sources = chunk.data.sources || [];
            ragUsed = chunk.data.rag_used || false;
          } else if (chunk.type === 'error') {
            botContent = `Erreur: ${chunk.content || 'Erreur inconnue'}`;
          }
        }

        // Finalize message
        setMessages((m) => 
          m.map((msg) => 
            msg.id === botMsgId 
              ? { 
                  ...msg, 
                  content: botContent || "Je n'ai pas pu générer une réponse.",
                  sources,
                  rag_used: ragUsed,
                  streaming: false
                }
              : msg
          )
        );
      } catch (e) {
        console.error('Streaming failed:', e);
        // Fallback to non-streaming
        const fallbackReply = await sendToApi(trimmed, abortRef.current.signal);
        const content = fallbackReply ?? "Erreur de communication avec le serveur.";
        const botMsg: ChatMessage = {
          id: nowId(),
          role: 'assistant',
          content,
          timestamp: Date.now(),
        };
        setMessages((m) => [...m, botMsg]);
      }
    } else {
      // Non-streaming mode (fallback)
      const reply = await sendToApi(trimmed, abortRef.current.signal);
      const content =
        reply ??
        `Je n'ai pas pu contacter l'API du chatbot. Vérifiez que le backend est accessible et réessayez.`;
      const botMsg: ChatMessage = {
        id: nowId(),
        role: 'assistant',
        content,
        timestamp: Date.now(),
      };
      setMessages((m) => [...m, botMsg]);
    }
    
    setLoading(false);
  }

  async function handleSend() {
    await sendMessage(input);
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const quickPrompts = [
    'Quel est mon prochain cours?',
    "Combien d'heures d'absence ai-je?",
    'Afficher mes présences de cette semaine',
    'Comment justifier une absence?',
  ];

  return (
    <div className="flex h-full w-full flex-col overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950">
      <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-400" />
            <span className="text-sm font-medium text-zinc-200">Assistant IA</span>
          </div>
          {apiAvailable === null ? (
            <span className="h-2 w-2 animate-pulse rounded-full bg-zinc-500" />
          ) : apiAvailable ? (
            <div className="flex items-center gap-1">
              <span title="API disponible" className="h-2 w-2 rounded-full bg-emerald-500" />
              {ragStatus.initialized && (
                <span title={`RAG actif: ${ragStatus.docs} documents`} className="flex items-center gap-1 text-[10px] text-emerald-400">
                  <Zap className="h-3 w-3" />
                  {ragStatus.docs}
                </span>
              )}
            </div>
          ) : (
            <span title="API indisponible" className="h-2 w-2 rounded-full bg-zinc-600" />
          )}
        </div>
        <button
          onClick={clearConversation}
          className="rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-700"
        >
          Effacer
        </button>
      </header>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="rounded border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-300">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-400" />
              <span className="font-semibold text-white">Bienvenue sur l'Assistant IA SmartPresence</span>
            </div>
            Je suis propulsé par un système RAG avancé avec support multi-LLM. 
            Je peux vous aider avec vos présences, absences, horaires, justifications et bien plus. 
            Posez votre question ci-dessous ou utilisez un prompt rapide.
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className="flex">
            <div
              className={
                m.role === 'user'
                  ? 'ml-auto max-w-[70%] rounded-lg bg-amber-600/20 px-3 py-2 text-amber-200'
                  : 'group mr-auto max-w-[70%] rounded-lg bg-zinc-800 px-3 py-2 text-zinc-200'
              }
            >
              <p className="whitespace-pre-wrap break-words text-sm">{m.content}</p>
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="text-[10px] text-zinc-400">Sources:</div>
                  <div className="flex flex-wrap gap-1">
                    {m.sources.map((src, i) => (
                      <span
                        key={i}
                        className="rounded bg-white/10 px-2 py-0.5 text-[10px] text-zinc-400"
                        title={src.category}
                      >
                        {src.title}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {m.rag_used && (
                <div className="mt-1 flex items-center gap-1 text-[10px] text-emerald-400">
                  <Zap className="h-3 w-3" />
                  <span>RAG</span>
                </div>
              )}
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="block text-[10px] text-zinc-400">
                  {new Date(m.timestamp).toLocaleTimeString()}
                </span>
                {m.role === 'assistant' && !m.streaming && (
                  <button
                    onClick={() => copyMessage(m.id, m.content)}
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    title="Copier"
                  >
                    {copiedId === m.id ? (
                      <Check className="h-3 w-3 text-emerald-400" />
                    ) : (
                      <Copy className="h-3 w-3 text-zinc-400 hover:text-white" />
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="mr-auto flex max-w-[70%] items-center gap-2 rounded-lg bg-zinc-800 px-3 py-2 text-zinc-300">
            <div className="flex gap-1">
              <span
                className="h-2 w-2 animate-bounce rounded-full bg-amber-400 anim-delay-0"
              />
              <span
                className="h-2 w-2 animate-bounce rounded-full bg-amber-400 anim-delay-150"
              />
              <span
                className="h-2 w-2 animate-bounce rounded-full bg-amber-400 anim-delay-300"
              />
            </div>
            <span className="text-sm">L'assistant écrit…</span>
          </div>
        )}
      </div>

      <div className="border-t border-zinc-800 p-3">
        <div className="mb-2 flex flex-wrap gap-2">
          {quickPrompts.map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              disabled={loading}
              className="rounded border border-zinc-700 bg-zinc-800/50 px-2 py-1 text-xs text-zinc-300 hover:border-amber-500/50 hover:bg-amber-500/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 rounded border border-white/10 bg-white/5 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-amber-500"
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="rounded bg-amber-600/90 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Envoyer
          </button>
        </div>
      </div>
    </div>
  );
}
