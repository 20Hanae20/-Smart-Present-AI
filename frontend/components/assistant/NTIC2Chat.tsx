'use client';

import { useState, useRef, useEffect } from 'react';

const QUICK_ACTIONS = [
  { text: "Menu principal", icon: "🏠" },
  { text: "Débouchés après formation", icon: "💼" },
  { text: "Contact ISTA", icon: "📞" },
  { text: "Infos Stage", icon: "📋" },
  { text: "EFM Régionaux", icon: "✍️" },
  { text: "Absences Professeurs", icon: "👥" },
  { text: "Professeur Parrain", icon: "👨‍🏫" }
];

interface Message {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  sources?: any[];
  timestamp: Date;
  isStreaming?: boolean;
}

export default function NTIC2Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { 
      id: 1, 
      role: 'assistant', 
      text: '👋 Bonjour! Je suis votre assistant intelligent ISTA NTIC. Je peux vous aider avec:\n\n📅 Emplois du temps\n📝 EFM et examens\n👨‍🏫 Professeurs parrains\n💼 Débouchés professionnels\n📞 Informations de contact\n\nPosez-moi vos questions!', 
      sources: [],
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ chunks: 0, connected: true });
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    checkStatus();
  }, []);

  async function checkStatus() {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/chat/status`);
      const data = await res.json();
      setStatus({ chunks: data.chunks || 0, connected: true });
    } catch (e) {
      setStatus({ chunks: 0, connected: false });
    }
  }

  const getUserId = () => {
    let userId = localStorage.getItem('ntic2_chat_user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('ntic2_chat_user_id', userId);
    }
    return userId;
  };

  const renderMessageWithLinks = (text: string) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = text.split(urlRegex);
    
    return parts.map((part, index) => {
      if (part.match(urlRegex)) {
        return (
          <a
            key={index}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 underline"
          >
            {part}
          </a>
        );
      }
      // Return text as-is to preserve newlines and formatting
      return <>{part}</>;
    });
  };

  async function send(text = input) {
    if (!text.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      text: text.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    const assistantMsgId = Date.now() + 1;
    setMessages(prev => [...prev, {
      id: assistantMsgId,
      role: 'assistant',
      text: '',
      sources: [],
      timestamp: new Date(),
      isStreaming: true
    }]);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          user_id: getUserId()
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'content') {
                  fullText += data.content;
                  setMessages(prev => prev.map(m => 
                    m.id === assistantMsgId ? { ...m, text: fullText } : m
                  ));
                } else if (data.type === 'end') {
                  const finalData = data.data;
                  setMessages(prev => prev.map(m => 
                    m.id === assistantMsgId ? { 
                      ...m, 
                      text: finalData.reply || fullText, 
                      sources: finalData.sources || [],
                      isStreaming: false
                    } : m
                  ));
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }
    } catch (e) {
      console.error('Chat error:', e);
      setMessages(prev => prev.map(m => 
        m.id === assistantMsgId ? { 
          ...m, 
          text: 'Erreur de connexion. Veuillez réessayer.',
          isStreaming: false
        } : m
      ));
    }

    setLoading(false);
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-black text-white">
      {/* Minimal Header */}
      <div className="border-b border-white/10 bg-black/50 backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold">Assistant IA</h1>
            <div className="flex items-center gap-2 ml-4">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <span className="text-xs text-white/50">Connecté</span>
            </div>
          </div>
          <button className="text-white/50 hover:text-white transition-colors px-3 py-1 text-sm">Effacer</button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto max-w-6xl mx-auto w-full px-6 py-8 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 flex-shrink-0 text-xl">🤖</div>
            )}
            
            <div className={`max-w-2xl ${msg.role === 'user' 
              ? 'bg-orange-600 rounded-lg rounded-tr-none' 
              : 'bg-white/5 border border-white/10 rounded-lg rounded-tl-none'
            } px-5 py-3`}>
              <div className="text-sm leading-relaxed text-white/90 whitespace-pre-wrap">
                {renderMessageWithLinks(msg.text)}
              </div>
              
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-xs text-white/40 mb-2">Sources ({msg.sources.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src, i) => (
                      <a
                        key={i}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs px-2 py-1 rounded bg-white/5 border border-white/10 text-blue-300 hover:text-blue-200 transition-all"
                      >
                        {src.title || `Source ${i + 1}`}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 flex-shrink-0 text-xl">👤</div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick Actions & Input Bar */}
      <div className="border-t border-white/10 bg-black/50 backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 py-4 space-y-4">
          {/* Quick Action Buttons */}
          <div className="flex flex-wrap gap-2">
            {QUICK_ACTIONS.map((action, i) => (
              <button
                key={i}
                onClick={() => send(action.text)}
                disabled={loading}
                className="px-3 py-2 rounded-full border border-white/20 text-xs text-white/70 hover:text-white hover:border-white/40 hover:bg-white/5 transition-all disabled:opacity-50"
              >
                {action.icon} {action.text}
              </button>
            ))}
          </div>

          {/* Input Area */}
          <div className="flex gap-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={loading}
              placeholder="Écrivez votre question ici... (Shift + Entrée pour nouvelle ligne)"
              className="flex-1 px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/30 resize-none transition-all text-sm"
              rows={1}
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              className="px-6 py-3 rounded-lg bg-orange-600 hover:bg-orange-700 text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm"
            >
              {loading ? '⏳' : '▶'} Envoyer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
