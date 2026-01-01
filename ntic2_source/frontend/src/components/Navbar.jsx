import React, { useState } from 'react'

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  
  const menuItems = [
    { label: 'Menu principal', active: false },
    { label: 'Débouchés après formation', active: false },
    { label: 'Contact ISTA', active: false },
    { label: 'Infos Stage', active: false },
    { label: 'EFM Régionaux', active: false },
    { label: 'Absences Professeurs', active: false },
    { label: 'Professeur Parrain', active: false }
  ]
  
  return (
    <>
      <nav className="navbar">
        <div className="navbar-container">
          <div className="navbar-brand">
            <div className="brand-icon">🎓</div>
            <div className="brand-text">
              <span className="brand-title">Assistant IA</span>
              <span className="brand-status">
                <span className="status-dot"></span>
                En ligne
              </span>
            </div>
          </div>
          
          <div className="navbar-menu">
            {menuItems.map((item, idx) => (
              <button 
                key={idx} 
                className={`navbar-menu-btn ${item.active ? 'active' : ''}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          
          <button 
            className="navbar-toggle"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </nav>
      
      {menuOpen && (
        <div className="mobile-menu">
          {menuItems.map((item, idx) => (
            <button 
              key={idx} 
              className={`mobile-menu-item ${item.active ? 'active' : ''}`}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </>
  )
}
