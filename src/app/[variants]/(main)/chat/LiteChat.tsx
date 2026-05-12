'use client';

import { ChangeEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';

type Message = {
  content: string;
  role: 'assistant' | 'user';
};

const createSessionId = () => `toki-${crypto.randomUUID()}`;

const shortSession = (sessionId: string) =>
  sessionId.length > 16 ? `${sessionId.slice(0, 8)}...${sessionId.slice(-4)}` : sessionId;

const quickActions = [
  { label: 'Remember this', prompt: 'Remember this safely: ' },
  { label: 'Recall memory', prompt: 'Retrieve and summarize relevant safe memory context.' },
  { label: 'Forget', prompt: 'Forget or mark inactive this memory/preference if supported: ' },
  { label: 'Summarize', prompt: 'Summarize this clearly and concisely: ' },
  { label: 'Draft', prompt: 'Draft a polished message for this: ' },
];

const LiteChat = () => {
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [uploadedContext, setUploadedContext] = useState('');
  const [uploadedName, setUploadedName] = useState('');
  const [memoryText, setMemoryText] = useState('');
  const [forgetText, setForgetText] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const canSend = input.trim().length > 0 && !loading;
  const statusSession = useMemo(() => shortSession(sessionId), [sessionId]);

  useEffect(() => {
    setSessionId(createSessionId());
  }, []);

  const scrollToBottom = () => {
    window.requestAnimationFrame(() => {
      listRef.current?.scrollTo({ behavior: 'smooth', top: listRef.current.scrollHeight });
    });
  };

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    const activeSessionId = sessionId || createSessionId();

    if (!sessionId) setSessionId(activeSessionId);

    const nextMessages: Message[] = [...messages, { content: trimmed, role: 'user' }];
    setMessages([...nextMessages, { content: '', role: 'assistant' }]);
    setInput('');
    setLoading(true);
    scrollToBottom();

    try {
      const response = await fetch('/api/toki/chat', {
        body: JSON.stringify({
          context: uploadedContext,
          message: trimmed,
          messages,
          sessionId: activeSessionId,
        }),
        headers: { 'content-type': 'application/json' },
        method: 'POST',
      });

      if (!response.ok || !response.body) {
        const body = await response.json().catch(() => undefined);
        throw new Error(body?.error?.message || 'AgentCore request failed.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        assistantText += decoder.decode(value, { stream: true });
        setMessages([...nextMessages, { content: assistantText, role: 'assistant' }]);
        scrollToBottom();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to reach AgentCore.';
      setMessages([...nextMessages, { content: message, role: 'assistant' }]);
    } finally {
      setLoading(false);
      setUploadedContext('');
      setUploadedName('');
      scrollToBottom();
    }
  };

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const text = await file.text();
    setUploadedContext(text.slice(0, 12_000));
    setUploadedName(`${file.name} (${Math.ceil(file.size / 1024)} KB)`);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (canSend) sendMessage(input);
    }
  };

  const newChat = () => {
    setSessionId(createSessionId());
    setMessages([]);
    setInput('');
    setUploadedContext('');
    setUploadedName('');
  };

  return (
    <main className="toki-shell">
      <aside className="toki-sidebar">
        <div className="toki-brand">
          <img alt="TOKAICOM Mitra Indonesia" height={30} src="/tokaicom-mark.svg" width={122} />
          <span>Toki-chan</span>
        </div>

        <button className="toki-primary" onClick={newChat} type="button">
          New Chat
        </button>
        <button className="toki-button" onClick={() => setMessages([])} type="button">
          Clear Chat
        </button>

        <section className="toki-section">
          <label>Upload Context</label>
          <input
            accept=".txt,.md,.csv,.json,.py,.log"
            className="toki-file"
            onChange={handleFile}
            type="file"
          />
          {uploadedName && <small>{uploadedName}</small>}
        </section>

        <section className="toki-section">
          <label>Memory</label>
          <button
            className="toki-button"
            onClick={() => sendMessage('Retrieve and summarize relevant safe memory context.')}
            type="button"
          >
            What do you remember?
          </button>
          <textarea
            onChange={(e) => setMemoryText(e.target.value)}
            placeholder="Preference to remember"
            rows={3}
            value={memoryText}
          />
          <button
            className="toki-button"
            disabled={!memoryText.trim()}
            onClick={() =>
              sendMessage(
                `Store this as safe reusable memory if appropriate. Do not store secrets or confidential data: ${memoryText}`,
              )
            }
            type="button"
          >
            Remember
          </button>
          <textarea
            onChange={(e) => setForgetText(e.target.value)}
            placeholder="Preference to forget"
            rows={3}
            value={forgetText}
          />
          <button
            className="toki-button"
            disabled={!forgetText.trim()}
            onClick={() =>
              sendMessage(
                `Forget or mark inactive this memory/preference if supported: ${forgetText}`,
              )
            }
            type="button"
          >
            Forget / Mark inactive
          </button>
        </section>

        <details className="toki-debug">
          <summary>Debug</summary>
          <small>Session: {sessionId}</small>
          <small>Runtime: AgentCore Harness</small>
        </details>
      </aside>

      <section className="toki-main">
        <header className="toki-header">
          <div>
            <h1>Toki-chan</h1>
            <p>Memory-aware personal AI assistant</p>
          </div>
          <div className="toki-pills">
            <span>AgentCore Connected</span>
            <span>Session: {statusSession}</span>
          </div>
        </header>

        <div className="toki-messages" ref={listRef}>
          {messages.length === 0 ? (
            <div className="toki-empty">
              <h2>Ask Toki-chan anything</h2>
              <p>Start a conversation or use a memory action.</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div className={`toki-message ${message.role}`} key={`${message.role}-${index}`}>
                <div>{message.content || 'Thinking...'}</div>
              </div>
            ))
          )}
        </div>

        <footer className="toki-composer">
          <div className="toki-actions">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() =>
                  action.label === 'Recall memory'
                    ? sendMessage(action.prompt)
                    : setInput((current) => action.prompt + current)
                }
                type="button"
              >
                {action.label}
              </button>
            ))}
          </div>
          <div className="toki-input-wrap">
            <textarea
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything or tell Toki-chan what to remember..."
              rows={1}
              value={input}
            />
            <button disabled={!canSend} onClick={() => sendMessage(input)} type="button">
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </footer>
      </section>

      <style jsx global>{`
        html,
        body {
          overflow: hidden;
          background: #f8fafc;
        }

        .toki-shell {
          display: grid;
          grid-template-columns: 280px minmax(0, 1fr);
          height: 100dvh;
          color: #0f172a;
          background:
            radial-gradient(circle at 70% 8%, rgba(167, 139, 250, 0.2), transparent 32%),
            radial-gradient(circle at 34% 100%, rgba(37, 99, 235, 0.12), transparent 34%), #f8fafc;
        }

        .toki-sidebar {
          display: flex;
          flex-direction: column;
          gap: 12px;
          min-height: 0;
          padding: 18px;
          border-right: 1px solid #e2e8f0;
          background: rgba(255, 255, 255, 0.88);
          backdrop-filter: blur(16px);
        }

        .toki-brand {
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-bottom: 8px;
          font-weight: 700;
        }

        .toki-section {
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding-top: 12px;
          border-top: 1px solid #e2e8f0;
        }

        .toki-section label {
          font-size: 12px;
          font-weight: 700;
          color: #64748b;
          text-transform: uppercase;
        }

        .toki-button,
        .toki-primary,
        .toki-actions button,
        .toki-input-wrap button {
          cursor: pointer;
          border: 1px solid #dbe4f0;
          border-radius: 14px;
          background: #fff;
          color: #0f172a;
          font-weight: 650;
          transition:
            transform 0.16s ease,
            border-color 0.16s ease,
            box-shadow 0.16s ease;
        }

        .toki-button,
        .toki-primary {
          min-height: 38px;
          padding: 9px 12px;
        }

        .toki-primary,
        .toki-input-wrap button {
          border-color: #2563eb;
          background: #2563eb;
          color: #fff;
        }

        .toki-button:hover,
        .toki-primary:hover,
        .toki-actions button:hover,
        .toki-input-wrap button:hover {
          transform: translateY(-1px);
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        }

        .toki-button:disabled,
        .toki-input-wrap button:disabled {
          cursor: not-allowed;
          opacity: 0.45;
          transform: none;
          box-shadow: none;
        }

        .toki-sidebar textarea,
        .toki-file {
          width: 100%;
          border: 1px solid #dbe4f0;
          border-radius: 14px;
          background: #fff;
          color: #0f172a;
          font: inherit;
        }

        .toki-sidebar textarea {
          resize: none;
          padding: 10px;
        }

        .toki-file {
          padding: 9px;
          font-size: 12px;
        }

        .toki-section small,
        .toki-debug small {
          display: block;
          overflow-wrap: anywhere;
          color: #64748b;
          font-size: 12px;
        }

        .toki-debug {
          margin-top: auto;
          color: #64748b;
        }

        .toki-main {
          display: flex;
          flex-direction: column;
          min-width: 0;
          min-height: 0;
        }

        .toki-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 20px 28px;
          border-bottom: 1px solid rgba(226, 232, 240, 0.9);
          background: rgba(248, 250, 252, 0.72);
          backdrop-filter: blur(18px);
        }

        .toki-header h1 {
          margin: 0;
          font-size: 22px;
          line-height: 1.2;
        }

        .toki-header p {
          margin: 4px 0 0;
          color: #64748b;
        }

        .toki-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: flex-end;
        }

        .toki-pills span {
          border: 1px solid #bfdbfe;
          border-radius: 999px;
          padding: 7px 10px;
          background: #eff6ff;
          color: #1d4ed8;
          font-size: 12px;
          font-weight: 700;
        }

        .toki-messages {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          padding: 28px;
        }

        .toki-empty {
          display: grid;
          height: 100%;
          place-content: center;
          text-align: center;
        }

        .toki-empty h2 {
          margin: 0;
          font-size: clamp(28px, 4vw, 44px);
        }

        .toki-empty p {
          margin: 10px 0 0;
          color: #64748b;
        }

        .toki-message {
          display: flex;
          margin-bottom: 14px;
        }

        .toki-message > div {
          max-width: min(760px, 78%);
          white-space: pre-wrap;
          border: 1px solid #e2e8f0;
          border-radius: 18px;
          padding: 13px 15px;
          line-height: 1.65;
          box-shadow: 0 16px 40px rgba(15, 23, 42, 0.05);
        }

        .toki-message.user {
          justify-content: flex-end;
        }

        .toki-message.user > div {
          border-color: #bfdbfe;
          background: #eff6ff;
        }

        .toki-message.assistant > div {
          background: #fff;
        }

        .toki-composer {
          position: sticky;
          bottom: 0;
          padding: 14px 28px 20px;
          border-top: 1px solid rgba(226, 232, 240, 0.9);
          background: linear-gradient(to top, #f8fafc 82%, rgba(248, 250, 252, 0));
        }

        .toki-actions {
          display: flex;
          gap: 8px;
          max-width: 860px;
          margin: 0 auto 10px;
          overflow-x: auto;
          padding-bottom: 2px;
        }

        .toki-actions button {
          flex: none;
          padding: 8px 12px;
          font-size: 13px;
        }

        .toki-input-wrap {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 10px;
          max-width: 860px;
          margin: 0 auto;
          border: 1px solid #cbd5e1;
          border-radius: 20px;
          padding: 10px;
          background: #fff;
          box-shadow: 0 18px 48px rgba(37, 99, 235, 0.12);
        }

        .toki-input-wrap textarea {
          resize: none;
          min-height: 42px;
          max-height: 140px;
          border: 0;
          outline: none;
          background: transparent;
          color: #0f172a;
          font: inherit;
          line-height: 1.5;
          padding: 10px 8px;
        }

        .toki-input-wrap button {
          min-width: 76px;
          padding: 0 16px;
        }

        @media (max-width: 760px) {
          .toki-shell {
            grid-template-columns: 1fr;
          }

          .toki-sidebar {
            display: none;
          }

          .toki-header,
          .toki-messages,
          .toki-composer {
            padding-inline: 16px;
          }

          .toki-message > div {
            max-width: 92%;
          }
        }
      `}</style>
    </main>
  );
};

export default LiteChat;
