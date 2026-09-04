"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Search,
  Mic,
  ArrowUp,
  Sparkles,
  Bot,
  User,
  History,
  Plus,
  Trash2,
  X,
  Loader2,
  Clock,
  ChevronRight,
  MessageSquare,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { chat } from "../../services/api";
import { useGuest } from "../../context/GuestContext";
import { useAuth } from "../../context/AuthContext";

export function AIAssistantInterface({ onQuerySubmit, isPreview = false }) {
  const { isGuest, showAuthModal } = useGuest();
  const { user } = useAuth();
  const isPreviewMode = isPreview || isGuest;

  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Load chat sessions when opening history
  const loadSessions = async () => {
    if (isPreviewMode) return;
    setSessionsLoading(true);
    try {
      const res = await chat.getSessions();
      if (res?.data?.success && Array.isArray(res.data.sessions)) {
        setSessions(res.data.sessions);
      }
    } catch {
      // silent fail
    } finally {
      setSessionsLoading(false);
    }
  };

  const toggleHistory = () => {
    const nextState = !isHistoryOpen;
    setIsHistoryOpen(nextState);
    if (nextState) {
      loadSessions();
    }
  };

  const handleStartNewChat = () => {
    setConversationId(null);
    setMessages([]);
    setIsHistoryOpen(false);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleSelectSession = async (sessionId) => {
    if (sessionId === conversationId) {
      setIsHistoryOpen(false);
      return;
    }
    setIsLoading(true);
    setIsHistoryOpen(false);
    try {
      const res = await chat.getHistory(sessionId);
      if (res?.data?.success && Array.isArray(res.data.messages)) {
        setConversationId(sessionId);
        setMessages(res.data.messages);
      }
    } catch {
      // silent fail
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await chat.deleteHistory(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (conversationId === sessionId) {
        handleStartNewChat();
      }
    } catch {
      // silent fail
    }
  };

  const handleInputClick = () => {
    if (isPreviewMode) {
      showAuthModal("Sign in as Admin to interact with InvIQ AI Assistant.");
    }
  };

  const handleSendMessage = async (textToSend) => {
    if (isPreviewMode) {
      showAuthModal("Sign in as Admin to interact with InvIQ AI Assistant.");
      return;
    }

    const query = (textToSend || inputValue).trim();
    if (!query || isLoading) return;

    const userMsg = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    if (onQuerySubmit) {
      onQuerySubmit(query);
    }

    try {
      const res = await chat.query({
        question: query,
        conversation_id: conversationId,
      });

      if (res?.data?.success) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.data.response },
        ]);
        if (res.data.conversation_id && !conversationId) {
          setConversationId(res.data.conversation_id);
        }
      } else {
        const errDetail = res?.data?.detail || res?.data?.error?.message || "Sorry, I could not process your query.";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: errDetail },
        ]);
      }
    } catch (err) {
      const errMsg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "I couldn't reach the AI service right now. Please verify that your question is about pharmacy inventory.";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: errMsg },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (isPreviewMode) {
      e.preventDefault();
      showAuthModal("Sign in to interact with InvIQ AI Assistant.");
      return;
    }

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const adminName = user?.full_name || user?.username || "Store Admin";
  const pharmacyName = user?.organization_name || "your pharmacy store";

  return (
    <div className="relative w-full h-full flex flex-col justify-between bg-card p-4 sm:p-6 font-sans overflow-hidden border border-border rounded-none text-foreground">
      
      {/* ── Top Header with History Button in Top Right ── */}
      <div className="shrink-0 flex items-center justify-between border-b border-border pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary text-[#F26A4B] flex items-center justify-center rounded-none font-bold">
            <Sparkles size={16} />
          </div>
          <div>
            <h2 className="text-sm font-sans font-bold text-foreground tracking-tight">
              InvIQ Intelligence Copilot
            </h2>
            <p className="text-[11px] text-muted-foreground">
              Personalized for {adminName} • {pharmacyName}
            </p>
          </div>
        </div>

        {/* History Toggle Button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleStartNewChat}
            title="Start New Chat"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-card border border-border text-foreground text-xs font-semibold rounded-none hover:bg-accent transition cursor-pointer"
          >
            <Plus size={13} />
            <span className="hidden sm:inline">New Chat</span>
          </button>
          <button
            type="button"
            onClick={toggleHistory}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border rounded-none transition cursor-pointer ${
              isHistoryOpen
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-accent/50 text-foreground border-border hover:bg-accent"
            }`}
          >
            <History size={13} />
            <span>History</span>
          </button>
        </div>
      </div>

      {/* ── Slide-over History Drawer ── */}
      <AnimatePresence>
        {isHistoryOpen && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.2 }}
            className="absolute top-0 right-0 w-80 max-w-full h-full bg-card border-l border-border z-40 flex flex-col shadow-xl"
          >
            <div className="p-4 border-b border-border flex items-center justify-between bg-accent/30">
              <div className="flex items-center gap-2">
                <Clock size={15} className="text-foreground" />
                <span className="text-xs font-bold text-foreground uppercase tracking-wider">
                  Chat History
                </span>
              </div>
              <button
                onClick={() => setIsHistoryOpen(false)}
                className="p-1 text-muted-foreground hover:text-foreground rounded-none cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-3 border-b border-border bg-card">
              <button
                onClick={handleStartNewChat}
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 bg-primary text-primary-foreground text-xs font-bold rounded-none hover:bg-black transition cursor-pointer"
              >
                <Plus size={14} />
                <span>+ Start Fresh Conversation</span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1 divide-y divide-border/50">
              {sessionsLoading ? (
                <div className="flex items-center justify-center py-8 text-xs text-muted-foreground gap-2">
                  <Loader2 size={14} className="animate-spin text-[#F26A4B]" />
                  <span>Loading conversations…</span>
                </div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-10 px-4 text-muted-foreground text-xs">
                  <MessageSquare size={24} className="mx-auto mb-2 opacity-40" />
                  <p>No past chat sessions found.</p>
                  <p className="text-[11px] text-muted-foreground mt-1">Start chatting to build your memory.</p>
                </div>
              ) : (
                sessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => handleSelectSession(s.id)}
                    className={`group w-full p-2.5 text-left text-xs cursor-pointer border rounded-none transition flex items-start justify-between gap-2 ${
                      conversationId === s.id
                        ? "bg-accent border-primary border-l-4"
                        : "bg-card border-transparent hover:bg-accent/40 hover:border-border"
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-foreground truncate">
                        {s.preview || "Chat Session"}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {s.message_count} messages
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      title="Delete chat"
                      className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive p-1 transition cursor-pointer"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main Chat Stream or Hero Greeting ── */}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4 my-auto">
          <div className="w-14 h-14 bg-primary text-[#F26A4B] flex items-center justify-center rounded-none font-bold mb-4 shadow-xs">
            <Bot size={28} />
          </div>
          <h1 className="text-xl sm:text-2xl font-sans font-bold text-foreground tracking-tight mb-2">
            Welcome to InvIQ, {adminName}!
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground max-w-lg leading-relaxed mb-6 font-normal">
            I am your personal inventory intelligence assistant for <span className="font-bold text-foreground">{pharmacyName}</span>.
            Ask about medicine stock levels, batch expiries, reorder recommendations, or cold-chain compliance.
          </p>

          {/* Quick Action Suggestion Pills */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-md w-full">
            {[
              "What is my current inventory status?",
              "Are there any near-expiry batches?",
              "Do I have any critical stock alerts?",
              "How do I upload supplier invoices?",
            ].map((q) => (
              <button
                key={q}
                onClick={() => handleSendMessage(q)}
                className="p-2.5 text-left text-xs bg-accent/30 hover:bg-accent border border-border text-foreground rounded-none transition flex items-center justify-between group cursor-pointer"
              >
                <span className="truncate">{q}</span>
                <ChevronRight size={13} className="text-muted-foreground group-hover:text-foreground shrink-0 ml-1" />
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto p-4 bg-background border border-border space-y-4 mb-4 rounded-none">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-3 ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {m.role === "user" ? (
                <>
                  <div className="py-2.5 px-4 text-xs sm:text-sm leading-relaxed max-w-[85%] rounded-none whitespace-pre-wrap bg-card text-foreground border border-border font-medium text-right sm:text-left shadow-2xs">
                    {m.content}
                  </div>
                  <div className="w-7 h-7 bg-accent border border-border flex items-center justify-center text-foreground shrink-0 rounded-none mt-0.5">
                    <User size={14} />
                  </div>
                </>
              ) : (
                <>
                  <div className="w-7 h-7 bg-primary flex items-center justify-center text-[#F26A4B] shrink-0 rounded-none mt-0.5">
                    <Bot size={14} />
                  </div>
                  <div className="p-3.5 text-xs sm:text-sm leading-relaxed max-w-[85%] rounded-none whitespace-pre-wrap bg-card text-foreground border border-border font-normal shadow-2xs">
                    {m.content}
                  </div>
                </>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex gap-2.5 items-center text-xs text-muted-foreground italic pl-1">
              <Loader2 size={14} className="animate-spin text-[#F26A4B]" />
              <span>InvIQ is analyzing {pharmacyName} inventory data…</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* ── Bottom Input Area (Warm Parchment Theme) ── */}
      <div 
        onClick={handleInputClick}
        className="shrink-0 w-full bg-card border border-border rounded-none shadow-none overflow-hidden"
      >
        <div className="p-3 relative flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || isPreviewMode}
            placeholder={`Ask InvIQ about ${pharmacyName} stock, expiries, or reorders…`}
            className="w-full bg-transparent text-xs sm:text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />

          <button
            type="button"
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || isLoading || isPreviewMode}
            className="p-2 bg-primary hover:bg-black text-primary-foreground rounded-none disabled:opacity-30 disabled:pointer-events-none transition shrink-0 cursor-pointer"
            title="Send Message"
          >
            {isLoading ? (
              <Loader2 size={16} className="animate-spin text-[#F26A4B]" />
            ) : (
              <ArrowUp size={16} />
            )}
          </button>
        </div>
      </div>

    </div>
  );
}

export default AIAssistantInterface;
