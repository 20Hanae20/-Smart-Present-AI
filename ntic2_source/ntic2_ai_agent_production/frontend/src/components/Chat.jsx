import React, { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import rehypeRaw from 'rehype-raw'

// Questions fréquentes suggérées
const SUGGESTED_QUESTIONS = [
  "Quels sont les emplois du temps disponibles ?",
  "Comment consulter mes résultats ?",
  "Quels documents administratifs sont disponibles ?",
  "Quand commence la période de stage ?",
  "Où trouver les supports de cours ?",
  "Quelles sont les dates des EFM régionaux ?",
  "Comment contacter l'établissement ?"
]

export default function Chat() {
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      role: 'assistant', 
      text: 'Bonjour ! 👋 Je suis votre assistant intelligent pour l\'ISTA NTIC Sidi Maarouf. Je peux répondre à vos questions sur les cours, les emplois du temps, les résultats, les documents et bien plus encore. Comment puis-je vous aider ?', 
      sources: [],
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [retryCount, setRetryCount] = useState(0)
  const [status, setStatus] = useState({ chunks: 0, connected: true })
  const [statusMessage, setStatusMessage] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(true)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const textareaRef = useRef(null)

  // Générer un user_id unique et persistant
  const getUserId = () => {
    let userId = localStorage.getItem('chat_user_id')
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('chat_user_id', userId)
    }
    return userId
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Vérifier le statut au chargement
  useEffect(() => {
    async function checkStatus() {
      try {
        console.log('[Status] Vérification du statut...')
        const res = await fetch('/api/chat/status', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-cache' // Forcer la récupération à chaque fois
        })
        
        console.log('[Status] Réponse HTTP:', res.status, res.statusText)
        
        // Toujours essayer de lire le JSON, même si le statut HTTP n'est pas OK
        let data
        try {
          const text = await res.text()
          console.log('[Status] Réponse brute:', text.substring(0, 200))
          data = JSON.parse(text)
          console.log('[Status] Données parsées:', data)
        } catch (e) {
          console.error('[Status] Erreur parsing JSON:', e)
          // Si la réponse n'est pas du JSON, créer un objet par défaut
          data = {
            chunks: 0,
            connected: false,
            status: 'error',
            message: `Erreur HTTP ${res.status}: ${res.statusText}`
          }
        }
        
        // Mettre à jour le statut avec les données reçues
        const chunksValue = data.chunks !== undefined && data.chunks !== null ? Number(data.chunks) : 0
        const connectedValue = data.connected !== undefined ? Boolean(data.connected) : (res.ok && chunksValue > 0)
        const statusValue = data.status || (res.ok ? 'ok' : 'error')
        
        console.log('[Status] Valeurs extraites:', { chunksValue, connectedValue, statusValue })
        
          setStatus({
          chunks: chunksValue,
          connected: connectedValue,
          status: statusValue,
            message: data.message || ''
          })
          
          // Afficher un message informatif selon le statut
        if (chunksValue === 0) {
          if (statusValue === 'no_data') {
              setStatusMessage("Aucune donnée disponible. Exécutez l'ingestion: python -m backend.app.rag.ingest")
          } else if (!res.ok) {
            setStatusMessage(`Connexion au serveur perdue: ${res.statusText}`)
            } else {
              setStatusMessage("Aucune donnée disponible. Veuillez exécuter l'ingestion des données.")
            }
          } else {
            setStatusMessage(null)
          console.log(`[Status] ✅ ${chunksValue} chunks disponibles`)
        }
      } catch (e) {
        console.error('[Status] Erreur vérification statut:', e)
        setStatus(prev => ({ 
          ...prev, 
          connected: false,
          status: 'error',
          message: `Erreur: ${e.message}`
        }))
        setStatusMessage(`Impossible de se connecter au serveur. Assurez-vous que le backend est démarré sur http://localhost:5000`)
      }
    }
    
    // Vérifier immédiatement au chargement
    checkStatus()
    // Vérifier à nouveau après 1 seconde pour s'assurer que le proxy est prêt
    const immediateCheck = setTimeout(checkStatus, 1000)
    // Vérifier toutes les 10s
    const interval = setInterval(checkStatus, 10000)
    
    return () => {
      clearTimeout(immediateCheck)
      clearInterval(interval)
    }
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [input])

  async function send(retryMessage = null, retryAttempt = 0) {
    const text = retryMessage || input.trim()
    if (!text || loading) return

    const userMsg = { id: Date.now(), role: 'user', text, timestamp: new Date() }
    if (!retryMessage && retryAttempt === 0) {
      setMessages(prev => [...prev, userMsg])
      setInput('')
    }
    setLoading(true)
    setError(null)

    // Créer un message vide pour l'assistant qui sera rempli au fur et à mesure
    const assistantMsgId = Date.now() + 1
    const initialAssistantMsg = { 
      id: assistantMsgId, 
      role: 'assistant', 
      text: '', 
      sources: [],
      timestamp: new Date(),
      isStreaming: true
    }
    setMessages(prev => [...prev, initialAssistantMsg])

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: text, 
          user_id: getUserId() 
        })
      })

      if (!res.ok) throw new Error(`Erreur HTTP: ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ""
      let partialLine = ""

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value, { stream: true })
        const lines = (partialLine + chunk).split('\n')
        partialLine = lines.pop() || ""
        
        for (const line of lines) {
          if (line.trim().startsWith('data: ')) {
            try {
              const jsonStr = line.trim().substring(6)
              if (!jsonStr) continue
              const data = JSON.parse(jsonStr)
              
              if (data.type === 'content') {
                fullText += data.content
                setMessages(prev => prev.map(m => 
                  m.id === assistantMsgId ? { ...m, text: fullText } : m
                ))
              } else if (data.type === 'end') {
                // Finaliser le message avec les sources et suggestions
                const finalData = data.data
                setMessages(prev => prev.map(m => 
                  m.id === assistantMsgId ? { 
                    ...m, 
                    text: finalData.reply || fullText,
                    sources: finalData.sources || [],
                    rag_used: finalData.rag_used,
                    language: finalData.language,
                    suggestions: finalData.suggestions,
                    isStreaming: false
                  } : m
                ))
              } else if (data.type === 'error') {
                throw new Error(data.message)
              }
            } catch (e) {
              console.error("Erreur parsing SSE:", e)
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat error:", error)
      setError(error.message)
      setMessages(prev => prev.map(m => 
        m.id === assistantMsgId ? { 
          ...m, 
          text: `Désolé, une erreur est survenue : ${error.message}`,
          isError: true,
          isStreaming: false
        } : m
      ))
    } finally {
      setLoading(false)
      setTimeout(() => textareaRef.current?.focus(), 100)
    }
  }

  function retryLastMessage() {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')
    if (lastUserMessage) {
      setRetryCount(prev => prev + 1)
      // Remove the last assistant message (error message)
      setMessages(prev => prev.slice(0, -1))
      // Appeler send avec retryAttempt à 0 pour forcer un nouveau retry
      send(lastUserMessage.text, 0)
    }
  }

  async function clearConversation() {
    if (window.confirm('Êtes-vous sûr de vouloir effacer cette conversation ? L\'historique sera également effacé côté serveur.')) {
      try {
        // Appeler l'API pour effacer l'historique côté serveur
        await fetch('/api/chat/clear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: getUserId() })
        }).catch(() => {
          // Ignorer les erreurs - on efface quand même côté client
        })
      } catch (e) {
        // Ignorer les erreurs
      }
      
      setMessages([
        { id: Date.now(), role: 'assistant', text: 'Conversation effacée. Comment puis-je vous aider ?', timestamp: new Date() }
      ])
      setError(null)
      setRetryCount(0)
      // Les suggestions restent toujours visibles (showSuggestions reste true)
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-root">
      <header className="chat-header">
        <div className="chat-header-content">
          <div className="header-left">
            <span>🤖 Assistant ISTA NTIC</span>
            <span className={`status-badge ${status.connected ? 'connected' : 'disconnected'}`}>
              {status.connected ? '🟢' : '🔴'} {Number(status.chunks) || 0} {Number(status.chunks) === 1 ? 'chunk' : 'chunks'}
            </span>
            {/* Debug: afficher le statut brut */}
            {process.env.NODE_ENV === 'development' && (
              <span style={{ fontSize: '0.7em', opacity: 0.6, marginLeft: '8px' }}>
                (status: {status.status || 'unknown'})
              </span>
            )}
          </div>
          <button 
            className="chat-clear-btn" 
            onClick={clearConversation}
            title="Effacer la conversation"
          >
            🗑️
          </button>
        </div>
      </header>
      
      {statusMessage && (
        <div className={`chat-status-message ${status.connected ? 'info' : 'error'}`}>
          <span>ℹ️ {statusMessage}</span>
          {!status.connected && (
            <div style={{ marginTop: '8px', fontSize: '0.9em', opacity: 0.9 }}>
              💡 Assurez-vous que le backend est démarré : <code>cd backend && python -m app.main</code>
            </div>
          )}
        </div>
      )}
      
      {error && (
        <div className="chat-error">
          <div className="chat-error-content">
            <span>⚠️ {error}</span>
            {retryCount < 2 && (
              <button 
                className="chat-retry-btn" 
                onClick={retryLastMessage}
                disabled={loading}
              >
                Réessayer
              </button>
            )}
          </div>
        </div>
      )}
      
      <div className="chat-window">
        {/* Afficher les suggestions toujours visibles */}
        {showSuggestions && (
          <div className="suggestions-container">
            <div className="suggestions-label">💡 Questions fréquentes :</div>
            <div className="suggestions-grid">
              {SUGGESTED_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  className="suggestion-chip"
                  onClick={() => {
                    setInput(question)
                    setTimeout(() => send(question), 100)
                  }}
                  disabled={loading}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map(m => (
          <div key={m.id} className={`chat-msg ${m.role} ${m.isError ? 'error' : ''} ${m.isStreaming ? 'is-streaming' : ''}`}>
            <div className={`chat-bubble ${m.isError ? 'error-bubble' : ''}`}>
              <div className="message-header">
                {m.timestamp && (
                  <span className="message-timestamp">
                    {new Date(m.timestamp).toLocaleTimeString('fr-FR', { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </span>
                )}
                <button
                  className="copy-button"
                  onClick={async (e) => {
                    try {
                      await navigator.clipboard.writeText(m.text)
                      // Feedback visuel temporaire
                      const btn = e.currentTarget
                      const originalText = btn.textContent
                      btn.textContent = '✓ Copié'
                      btn.style.opacity = '0.7'
                      setTimeout(() => {
                        btn.textContent = originalText
                        btn.style.opacity = '1'
                      }, 2000)
                    } catch (err) {
                      console.error('Erreur lors de la copie:', err)
                    }
                  }}
                  title="Copier le message"
                >
                  📋
                </button>
              </div>
              {(m.usingRAG || (m.sources && m.sources.length > 0)) && (
                <div className="rag-indicator">
                  <span className="rag-badge">📚 Basé sur les données du site</span>
                </div>
              )}
              <div className="message-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw, rehypeHighlight]}
                  className="markdown-content"
                  components={{
                    code: ({ node, inline, className, children, ...props }) => {
                      const match = /language-(\w+)/.exec(className || '')
                      return !inline && match ? (
                        <pre className={`code-block ${className || ''}`}>
                          <code className={className} {...props}>
                            {children}
                          </code>
                        </pre>
                      ) : (
                        <code className="inline-code" {...props}>
                          {children}
                        </code>
                      )
                    },
                    a: ({ node, ...props }) => (
                      <a {...props} target="_blank" rel="noopener noreferrer" />
                    )
                  }}
                >
                  {m.text}
                </ReactMarkdown>
              </div>
              {m.sources && m.sources.length > 0 && (
                <div className="sources-badge">
                  <div className="sources-label">
                    📚 Sources ({m.sourcesCount || m.sources.length}):
                  </div>
                  <div className="sources-list">
                    {m.sources.map((source, idx) => {
                      const sourceTitle = source.title || source.display || source.section || 'Source'
                      const sourceUrl = source.url || ''
                      
                      return (
                        <a
                          key={idx} 
                          href={sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-link"
                          style={{
                            display: 'inline-block',
                            margin: '4px 8px 4px 0',
                            padding: '6px 12px',
                            backgroundColor: '#f0f0f0',
                            borderRadius: '4px',
                            textDecoration: 'none',
                            color: '#0066cc',
                            fontSize: '0.9em',
                            transition: 'background-color 0.2s'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#e0e0e0'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#f0f0f0'}
                        >
                          {sourceTitle} 🔗
                        </a>
                      )
                    })}
                  </div>
                </div>
              )}
              {m.usingRAG && (
                <div className="rag-info">
                  <span className="rag-info-text">
                    ✅ Réponse basée sur {m.chunkCount || 0} chunks du site ISTA NTIC
                  </span>
                </div>
              )}
              
              {/* Suggestions interactives */}
              {(() => {
                // Debug: vérifier les suggestions
                if (m.suggestions) {
                  console.log('🔍 Suggestions dans le message:', {
                    type: m.suggestions.type,
                    items: m.suggestions.items,
                    itemsLength: m.suggestions.items?.length,
                    group: m.suggestions.group,
                    day: m.suggestions.day
                  })
                }
                
                // Vérifier si les suggestions existent et ont des items
                const hasSuggestions = m.suggestions && 
                                      m.suggestions.items && 
                                      Array.isArray(m.suggestions.items) && 
                                      m.suggestions.items.length > 0
                
                if (!hasSuggestions && m.suggestions) {
                  console.warn('⚠️ Suggestions présentes mais items vides ou invalides:', m.suggestions)
                }
                
                return hasSuggestions ? (
                  <div className="interactive-suggestions">
                    <div className="suggestions-label">
                      {m.suggestions.type === 'groups' && '👥 Choisissez un groupe :'}
                      {m.suggestions.type === 'days_by_group' && `📅 Choisissez un jour pour le groupe ${m.suggestions.group} :`}
                      {m.suggestions.type === 'days' && '📅 Choisissez un jour :'}
                      {m.suggestions.type === 'groups_by_day' && `👥 Groupes disponibles le ${m.suggestions.day} :`}
                      {!m.suggestions.type && '💡 Suggestions :'}
                    </div>
                    <div className="suggestions-buttons">
                      {m.suggestions.items.map((item, idx) => (
                        <button
                          key={idx}
                          className="suggestion-button"
                          onClick={async () => {
                            let question = ''
                            if (m.suggestions.type === 'groups') {
                              // Étape 1: Groupe sélectionné → demander les jours pour ce groupe
                              question = `Quels sont les jours de cours pour le groupe ${item} ?`
                            } else if (m.suggestions.type === 'days_by_group') {
                              // Étape 2: Jour sélectionné pour un groupe → afficher les horaires
                              question = `Quel est l'emploi du temps du groupe ${m.suggestions.group} le ${item} ?`
                            } else if (m.suggestions.type === 'days') {
                              question = `Quel est l'emploi du temps du ${item} ?`
                            } else if (m.suggestions.type === 'groups_by_day') {
                              question = `Quel est l'emploi du temps du groupe ${item} le ${m.suggestions.day} ?`
                            } else {
                              question = item
                            }
                            setInput(question)
                            setTimeout(() => send(question), 100)
                          }}
                          disabled={loading}
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null
              })()}
            </div>
          </div>
        ))}
        
        {loading && !messages.some(m => m.isStreaming) && (
          <div className="chat-msg assistant">
            <div className="chat-bubble typing-indicator">
              <span className="typing-text">Assistant écrit</span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        
        <div ref={bottomRef} />
      </div>
      
      <div className="chat-input">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Posez une question sur l'ISTA NTIC... (Appuyez sur Entrée pour envoyer, Maj+Entrée pour une nouvelle ligne)"
          disabled={loading}
          rows={1}
        />
        <button 
          onClick={() => send()} 
          disabled={loading || !input.trim()}
          className={loading ? 'loading' : ''}
          title={loading ? 'Envoi en cours...' : 'Envoyer (Entrée)'}
        >
          {loading ? '⏳' : '📤'}
        </button>
      </div>
    </div>
  )
}
