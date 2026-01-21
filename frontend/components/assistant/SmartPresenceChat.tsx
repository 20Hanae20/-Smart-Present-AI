'use client';

import { useState, useRef, useEffect } from 'react';

const QUICK_ACTIONS = [
  { text: "Comment faire le check-in ?", icon: "✅" },
  { text: "Problème reconnaissance faciale", icon: "👤" },
  { text: "Justifier une absence", icon: "📝" },
  { text: "Consulter mes présences", icon: "📊" },
  { text: "Check-in par QR code", icon: "📱" },
  { text: "Tableau de bord", icon: "📈" },
  { text: "Dépannage", icon: "🔧" }
];

interface Message {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  sources?: any[];
  timestamp: Date;
  isStreaming?: boolean;
}

export default function SmartPresenceChat() {
  const [messages, setMessages] = useState<Message[]>([
    { 
      id: 1, 
      role: 'assistant', 
      text: '👋 Bienvenue dans Smart Presence AI ! Je suis votre assistant intelligent pour la gestion des présences.\n\nJe peux vous aider avec:\n✅ Procédures de check-in/check-out\n👤 Reconnaissance faciale et QR codes\n📊 Consultation des présences et statistiques\n📝 Justifications d\'absences\n📈 Tableau de bord et rapports\n🔧 Dépannage et support technique\n\nPosez-moi vos questions !', 
      sources: [],
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ 
    rag_initialized: false, 
    knowledge_documents: 0,
    streaming_available: false,
    providers_configured: []
  });
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
      const res = await fetch(`${apiUrl}/api/chatbot/status`);
      const data = await res.json();
      setStatus(data);
    } catch (e) {
      console.error('Status check failed:', e);
    }
  }

  const getUserId = () => {
    let userId = localStorage.getItem('smartpresence_chat_user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('smartpresence_chat_user_id', userId);
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
      const response = await fetch(`${apiUrl}/api/chatbot/stream`, {
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
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-white">
      {/* Header with status */}
      <div className="border-b border-white/10 bg-black/30 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold bg-gradient-to-r from-orange-400 to-orange-600 bg-clip-text text-transparent">
              Smart Presence AI
            </h1>
            <div className="flex items-center gap-2 ml-4">
              <div className={`w-2 h-2 rounded-full ${status.rag_initialized ? 'bg-green-500' : 'bg-yellow-500'} animate-pulse`}></div>
              <span className="text-xs text-white/50">
                {status.rag_initialized ? 'IA Connectée' : 'Initialisation...'}
              </span>
              {status.knowledge_documents > 0 && (
                <span className="text-xs text-white/40 ml-2">
                  {status.knowledge_documents} documents
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {status.providers_configured.length > 0 && (
              <div className="text-xs text-white/40">
                Fournisseurs: {status.providers_configured.join(', ')}
              </div>
            )}
            <button 
              onClick={() => setMessages([messages[0]])}
              className="text-white/50 hover:text-white transition-colors px-3 py-1 text-sm"
            >
              Effacer
            </button>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto max-w-6xl mx-auto w-full px-6 py-8 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-10 h-10 flex-shrink-0 rounded-full bg-gradient-to-r from-orange-500 to-orange-600 flex items-center justify-center text-lg">
                🤖
              </div>
            )}
            
            <div className={`max-w-2xl ${msg.role === 'user' 
              ? 'bg-gradient-to-r from-orange-600 to-orange-700 rounded-lg rounded-tr-none shadow-lg' 
              : 'bg-white/5 border border-white/10 rounded-lg rounded-tl-none backdrop-blur-sm'
            } px-5 py-4`}>
              <div className="text-sm leading-relaxed text-white/90 whitespace-pre-wrap">
                {renderMessageWithLinks(msg.text)}
              </div>
              
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-xs text-white/40 mb-2">Sources ({msg.sources.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((src, i) => (
                      <div
                        key={i}
                        className="text-xs px-2 py-1 rounded bg-white/5 border border-white/10 text-blue-300"
                      >
                        📄 Source {i + 1}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {msg.isStreaming && (
                <div className="mt-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce delay-75"></div>
                    <div className="w-2 h-2 bg-orange-400 rounded-full animate-bounce delay-150"></div>
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-10 h-10 flex-shrink-0 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 flex items-center justify-center text-lg">
                👤
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick Actions & Input Bar */}
      <div className="border-t border-white/10 bg-black/30 backdrop-blur-sm">
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
              className="px-6 py-3 rounded-lg bg-gradient-to-r from-orange-600 to-orange-700 hover:from-orange-700 hover:to-orange-800 text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm shadow-lg"
            >
              {loading ? '⏳' : '▶'} Envoyer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
