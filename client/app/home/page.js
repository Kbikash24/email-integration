'use client';

import { useState, useEffect, useCallback } from 'react';
import axios from '../../lib/axios';
import { auth, getIdToken } from '../lib/firebase';

// Helper accessible to list + detail
function headerValue(msg, key) {
  if (!msg) return ''
  if (msg.headers && typeof msg.headers === 'object') return msg.headers[key] || ''
  const arr = msg.payload?.headers || []
  return (arr.find(h => h.name === key) || {}).value || ''
}

// Gmail like three-pane UI with auto load + conditional connect state
export default function GmailIntegration() {
  const [connected, setConnected] = useState(false)
  const [messages, setMessages] = useState([]) // raw list
  const [selectedMessage, setSelectedMessage] = useState(null)
  const [form, setForm] = useState({ to: '', subject: '', body: '' })
  const [loading, setLoading] = useState(false)
  const [initializing, setInitializing] = useState(true)
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)
  const [showCompose, setShowCompose] = useState(true) // compose shown by default
  const [disconnecting, setDisconnecting] = useState(false)
  const [accounts, setAccounts] = useState([])
  // Active Gmail account id (returned by /email/auth-url) required as header `accountId`
  const [activeAccountId, setActiveAccountId] = useState(null)

  // headerValue now defined at module scope

  // Listen for popup -> main window message (post OAuth)
  useEffect(() => {
    function listener(e) {
      if (e.data?.type === 'GMAIL_CONNECTED') {
        setConnected(true)
        // After OAuth finishes, refresh accounts then messages.
        loadAccounts().then(() => {
          // If backend provided accountId via message, prefer it
          if (e.data.accountId) {
            setActiveAccountId(e.data.accountId)
            try { localStorage.setItem('gmailAccountId', e.data.accountId) } catch(_) {}
          }
          // If we have an active account id, load its messages
          loadMessages()
        })
      }
    }
    window.addEventListener('message', listener)
    return () => window.removeEventListener('message', listener)
  }, [])

  const connectGmail = async () => {
    try {
      const user = auth.currentUser
      if (!user) return alert('Please sign in first.')
      const idToken = await getIdToken()
      const { data } = await axios.get('/email/auth-url', { headers: { Authorization: idToken } })
      if (data?.accountId) {
        setActiveAccountId(data.accountId)
        try { localStorage.setItem('gmailAccountId', data.accountId) } catch (_) {}
      }
      window.open(data.url, 'gmailOAuth', 'width=600,height=700')
    } catch (e) {
      alert('Failed to initiate Gmail connect')
    }
  }

  // Loads latest messages for current Gmail account.
  // Backend requires:
  //  - Authorization: Firebase ID token
  //  - accountId: value returned by /email/auth-url (also persisted in localStorage)
  // Query param maxResults=30 limits the returned messages.
  const loadMessages = useCallback(async () => {
    if (!activeAccountId) {
      // No account id yet – skip until we have one
      setInitializing(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const idToken = await getIdToken()
      const { data } = await axios.get('/email/messages?maxResults=30', { headers: { Authorization: idToken, account_id: activeAccountId } })
      const list = data.messages || []
      setMessages(list)
      if (list.length) setSelectedMessage(list[0])
      setConnected(true) // success implies connected
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load messages')
      setConnected(false)
    } finally {
      setLoading(false)
      setInitializing(false)
    }
  }, [activeAccountId])

  const loadAccounts = async () => {
    try {
      const idToken = await getIdToken()
      const { data } = await axios.get('/email/accounts', { headers: { Authorization: idToken } })
      setAccounts(data.accounts || [])
    } catch (e) {
      console.warn('Failed to load accounts')
    }
  }

  // Auto load on mount
  // Restore previously selected account id if available
  useEffect(() => {
    try {
      const stored = localStorage.getItem('gmailAccountId')
      if (stored) setActiveAccountId(stored)
    } catch (_) {}
  }, [])

  useEffect(() => {
    if (activeAccountId) loadMessages()
    loadAccounts()
  }, [loadMessages, activeAccountId])

  const disconnect = async () => {
    if (!confirm('Disconnect Gmail account? You will need to reconnect to access emails.')) return
    setDisconnecting(true)
    try {
      const idToken = await getIdToken()
      await axios.post('/email/disconnect', {}, { headers: { Authorization: idToken } })
    } catch (e) {
      console.warn('Failed to notify backend disconnect, proceeding local reset.')
    } finally {
      setDisconnecting(false)
      setConnected(false)
      setMessages([])
      setSelectedMessage(null)
      setShowCompose(true)
    }
  }

  const sendEmail = async (e) => {
    e.preventDefault()
    setSending(true)
    try {
      const idToken = await getIdToken()
      await axios.post('/email/send', { ...form }, { headers: { Authorization: idToken } })
      alert('Email sent!')
      setForm({ to: '', subject: '', body: '' })
    } catch (err) {
      alert('Error sending email: ' + (err.response?.data?.error || err.message))
    } finally {
      setSending(false)
    }
  }

  const statusBar = (
    <div className="status-bar">
      {loading && <span className="badge loading">Loading…</span>}
      {!loading && connected && <span className="badge success">Connected</span>}
      {!loading && !connected && <span className="badge danger">Not Connected</span>}
      {error && <span className="error-text">{error}</span>}
      <div style={{marginLeft:'auto',display:'flex',gap:8}}>
        {connected && accounts.length > 0 && (
          <select
            value={activeAccountId || ''}
            onChange={e => {
              const val = e.target.value || null
              setActiveAccountId(val)
              try { localStorage.setItem('gmailAccountId', val || '') } catch(_) {}
              setMessages([])
              setSelectedMessage(null)
            }}
            className="btn ghost"
            style={{padding:'6px 8px'}}
          >
            <option value="">Select account</option>
            {accounts.map(a => (
              <option key={a.accountId} value={a.accountId}>{a.emailAddress || a.name || a.accountId}</option>
            ))}
          </select>
        )}
        {connected && <button className="btn primary" onClick={()=>{ setShowCompose(true); setSelectedMessage(null) }}>Compose</button>}
        {connected && <button className="btn danger" onClick={disconnect} disabled={disconnecting}>{disconnecting? 'Disconnecting…':'Disconnect'}</button>}
        <button className="btn ghost" onClick={loadMessages} disabled={loading}>Refresh</button>
        {connected && (
          <button className="btn ghost" onClick={() => { auth.signOut(); window.location.reload() }}>Logout</button>
        )}
      </div>
    </div>
  )

  if (initializing && loading) {
    return (
      <div className="email-root initializing">
        <div className="loader" />
        <p>Loading messages…</p>
        <style jsx>{styles}</style>
      </div>
    )
  }

  if (!connected) {
    return (
      <div className="email-root connect-state">
        {statusBar}
        <div className="connect-panel">
          <h1>Gmail Integration</h1>
            <p>Connect your Gmail to view and send emails from the dashboard.</p>
          <div style={{marginBottom: accounts.length? 16: 24, display:'flex', flexDirection:'column', gap:12}}>
            {accounts.length > 0 && (
              <>
                <div style={{fontSize:14,fontWeight:500}}>Connected accounts ({accounts.length})</div>
                <select
                  value={activeAccountId || ''}
                  onChange={e => {
                    const val = e.target.value || null
                    setActiveAccountId(val)
                    try { localStorage.setItem('gmailAccountId', val || '') } catch(_) {}
                    setMessages([])
                    setSelectedMessage(null)
                    if (val) loadMessages()
                  }}
                  style={{padding:10,border:'1px solid #cbd5e1', borderRadius:6}}
                >
                  <option value="">Select account</option>
                  {accounts.map(a => (
                    <option key={a.accountId} value={a.accountId}>{a.emailAddress || a.name || a.accountId}</option>
                  ))}
                </select>
              </>
            )}
            <button className="btn primary" onClick={connectGmail}>Connect Gmail</button>
          </div>
          {error && <p className="error-text" style={{marginTop:12}}>{error}</p>}
        </div>
        <style jsx>{styles}</style>
      </div>
    )
  }

  return (
    <div className="email-root">
      {statusBar}
      {connected && !!accounts.length && (
        <div className="accounts-bar">
          {accounts.map(a => (
            <div key={a.accountId} className="acct-chip" title={a.emailAddress || a.accountId}>
              <span className="acct-initial">{(a.emailAddress || a.name || 'Account').charAt(0).toUpperCase()}</span>
              <span className="acct-label">{a.emailAddress || a.name || 'Unnamed Account'}</span>
            </div>
          ))}
        </div>
      )}
      <div className="layout two-col">
        <aside className="message-list-pane" style={{maxHeight: '100vh'}}>
          <div className="pane-header">Inbox ({messages.length})</div>
          <div className="messages-scroll">
            {messages.length === 0 && !loading && (
              <div className="empty-hint">No messages.</div>
            )}
            {loading && <div className="skeleton-list" />}
            {!loading && messages.map(m => {
              const date = m.headers?.Date || (m.internalDate ? new Date(Number(m.internalDate)).toLocaleDateString() : '')
              return (
                <div
                  key={m.id}
                  className={"message-row" + (selectedMessage?.id === m.id ? ' active' : '')}
                  onClick={() => { setSelectedMessage(m); setShowCompose(false) }}
                >
                  <div className="row-top">
                    <span className="from">{headerValue(m,'From') || 'Unknown'}</span>
                    <span className="date">{date}</span>
                  </div>
                  <div className="subject">{headerValue(m,'Subject') || '(No Subject)'}</div>
                  <div className="snippet" title={m.snippet}>{m.snippet}</div>
                </div>
              )
            })}
          </div>
        </aside>
        <main className="message-detail-pane">
          {showCompose ? (
            <div className="compose-wrapper">
              <div className="pane-header inside">Compose</div>
              <form onSubmit={sendEmail} className="compose-form in-detail">
                <label>
                  <span>To</span>
                  <input type="email" required value={form.to} onChange={e=>setForm(f=>({...f,to:e.target.value}))} />
                </label>
                <label>
                  <span>Subject</span>
                  <input required value={form.subject} onChange={e=>setForm(f=>({...f,subject:e.target.value}))} />
                </label>
                <label className="grow">
                  <span>Body</span>
                  <textarea required value={form.body} onChange={e=>setForm(f=>({...f,body:e.target.value}))} />
                </label>
                <div style={{display:'flex', gap:8}}>
                  <button className="btn primary" type="submit" disabled={sending}>{sending? 'Sending…':'Send'}</button>
                  {selectedMessage && <button type="button" className="btn ghost" onClick={()=>{ setShowCompose(false) }}>View Message</button>}
                </div>
              </form>
            </div>
          ) : selectedMessage ? (
            <MessageDetail message={selectedMessage} onBackToCompose={()=> setShowCompose(true)} />
          ) : (
            <div className="placeholder">Select a message or click Compose</div>
          )}
        </main>
      </div>
      <style jsx>{styles}</style>
    </div>
  )
}

function MessageDetail({ message, onBackToCompose }) {
  const subject = headerValue(message,'Subject') || '(No Subject)'
  const from = headerValue(message,'From') || 'Unknown'
  const to = headerValue(message,'To') || ''
  const date = message.headers?.Date || (message.internalDate ? new Date(Number(message.internalDate)).toLocaleString() : '')
  const bodySnippet = message.snippet || 'No preview available.'
  return (
    <div className="detail-wrapper">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
        <h1 className="detail-subject" style={{marginBottom:0}}>{subject}</h1>
        {onBackToCompose && <button className="btn ghost" onClick={onBackToCompose}>Compose</button>}
      </div>
      <div className="meta"><strong>From:</strong> {from}</div>
      <div className="meta"><strong>To:</strong> {to}</div>
      <div className="meta"><strong>Date:</strong> {date}</div>
      <div className="body-box">{bodySnippet}</div>
    </div>
  )
}

const styles = `
  .email-root { display:flex; flex-direction:column; height:100vh; background:#f5f7fb; font-family: system-ui,-apple-system,Segoe UI,Roboto,Ubuntu; color:#1f2937; }
  .email-root.connect-state { align-items:center; justify-content:flex-start; padding-top:80px; }
  .status-bar { display:flex; align-items:center; gap:12px; padding:10px 16px; background:#fff; border-bottom:1px solid #e5e7eb; font-size:14px; }
  .accounts-bar { display:flex; gap:8px; padding:6px 12px 10px 16px; background:#fff; border-bottom:1px solid #e5e7eb; flex-wrap:wrap; }
  .acct-chip { display:inline-flex; align-items:center; gap:6px; background:#eff6ff; border:1px solid #bfdbfe; padding:4px 10px 4px 6px; border-radius:24px; font-size:12px; font-weight:500; color:#1e3a8a; }
  .acct-initial { background:#3b82f6; color:#fff; width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:600; }
  .acct-label { max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .badge { padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600; letter-spacing:.5px; text-transform:uppercase; }
  .badge.success { background:#dcfce7; color:#166534; }
  .badge.danger { background:#fee2e2; color:#991b1b; }
  .badge.loading { background:#e0f2fe; color:#0369a1; animation: pulse 1.2s ease-in-out infinite; }
  @keyframes pulse { 0%,100%{opacity:.55} 50%{opacity:1} }
  .error-text { color:#b91c1c; font-size:12px; font-weight:500; }
  .layout { flex:1; display:grid; grid-template-columns: 320px 1fr 360px; min-height:0; }
  .layout.two-col { grid-template-columns: 320px 1fr; }
  .message-list-pane, .message-detail-pane { display:flex; flex-direction:column; background:#fff; border-right:1px solid #e5e7eb; }
  .message-detail-pane { border-right:none; }
  .compose-wrapper { display:flex; flex-direction:column; flex:1; overflow:hidden; }
  .message-detail-pane { position:relative; overflow:hidden; }
  .message-detail-pane > * { height:100%; }
  .compose-form.in-detail { flex:1; overflow-y:auto; }
  .compose-form.in-detail::-webkit-scrollbar, .detail-wrapper::-webkit-scrollbar { width:8px; }
  .compose-form.in-detail::-webkit-scrollbar-thumb, .detail-wrapper::-webkit-scrollbar-thumb { background:#cbd5e1; border-radius:4px; }
  .compose-form.in-detail::-webkit-scrollbar-thumb:hover, .detail-wrapper::-webkit-scrollbar-thumb:hover { background:#94a3b8; }
  .pane-header.inside { border-bottom:1px solid #e5e7eb; background:#f9fafb; }
  .compose-form.in-detail { flex:1; }
  .pane-header { padding:12px 16px; font-weight:600; font-size:14px; background:#f9fafb; border-bottom:1px solid #e5e7eb; }
  .messages-scroll { flex:1; overflow-y:auto; }
  .message-row { padding:10px 14px; border-bottom:1px solid #f1f5f9; cursor:pointer; transition:background .15s; }
  .message-row:hover { background:#f1f5f9; }
  .message-row.active { background:#e0f2fe; border-left:4px solid #38bdf8; padding-left:10px; }
  .row-top { display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px; }
  .from { font-weight:600; max-width:180px; white-space:nowrap; text-overflow:ellipsis; overflow:hidden; }
  .date { color:#64748b; }
  .subject { font-size:13px; font-weight:500; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .snippet { font-size:12px; color:#64748b; line-height:1.3; height:30px; overflow:hidden; }
  .empty-hint { padding:24px; text-align:center; font-size:13px; color:#6b7280; }
  .placeholder { display:flex; align-items:center; justify-content:center; flex:1; color:#64748b; font-size:14px; }
  .detail-wrapper { padding:24px 32px; overflow-y:auto; height:100%; }
  .detail-subject { font-size:20px; margin:0 0 12px; font-weight:600; line-height:1.2; }
  .meta { font-size:13px; margin-bottom:4px; }
  .body-box { background:#f8fafc; border:1px solid #e2e8f0; padding:16px 18px; border-radius:8px; font-size:14px; margin-top:16px; min-height:120px; white-space:pre-wrap; }
  .compose-form { display:flex; flex-direction:column; gap:12px; padding:16px; flex:1; }
  .compose-form label { display:flex; flex-direction:column; gap:4px; font-size:12px; font-weight:600; color:#475569; }
  .compose-form input, .compose-form textarea { border:1px solid #cbd5e1; border-radius:6px; padding:8px 10px; font:inherit; font-size:13px; background:#fff; resize:vertical; }
  .compose-form textarea { flex:1; min-height:160px; }
  .compose-form .grow { flex:1; }
  .btn { border:none; background:#e2e8f0; color:#1e293b; padding:8px 16px; border-radius:6px; font-size:13px; font-weight:500; cursor:pointer; transition:background .15s, transform .15s; display:inline-flex; align-items:center; gap:6px; }
  .btn:hover { background:#cbd5e1; }
  .btn:active { transform:translateY(1px); }
  .btn.primary { background:#2563eb; color:#fff; }
  .btn.primary:hover { background:#1d4ed8; }
  .btn.ghost { background:transparent; color:#1f2937; }
  .btn.ghost:hover { background:#f1f5f9; }
  .btn.danger { background:#dc2626; color:#fff; }
  .btn.danger:hover { background:#b91c1c; }
  .connect-panel { background:#fff; padding:40px 56px; border-radius:16px; box-shadow:0 4px 24px -6px rgba(0,0,0,.08); max-width:560px; width:100%; text-align:center; }
  .connect-panel h1 { margin:0 0 12px; font-size:28px; font-weight:600; }
  .connect-panel p { margin:0 0 24px; color:#475569; }
  .loader { width:42px; height:42px; border-radius:50%; border:4px solid #e2e8f0; border-top-color:#2563eb; animation:spin .8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .email-root.initializing { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:16px; }
  .skeleton-list { height:100%; background:repeating-linear-gradient( -45deg,#f1f5f9,#f1f5f9 10px,#e2e8f0 10px,#e2e8f0 20px); opacity:.6; }
  @media (max-width: 1200px) { .layout { grid-template-columns: 280px 1fr 320px; } }
  @media (max-width: 980px) { .layout.two-col { grid-template-columns: 260px 1fr; } }
  @media (max-width: 640px) { .layout.two-col { grid-template-columns: 1fr; } .message-list-pane { display:none; } }
  .message-list-pane { position:relative; overflow:hidden; max-height:500px; }
`