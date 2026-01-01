import React from 'react'
import Chat from './components/Chat'
import Navbar from './components/Navbar'
import './styles.css'

export default function App(){
  return (
    <div className="app-container">
      <Navbar />
      <main className="app-main">
        <Chat />
      </main>
    </div>
  )
}
