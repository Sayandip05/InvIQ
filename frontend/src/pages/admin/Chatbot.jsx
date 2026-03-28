import React, { useState, useRef, useEffect } from 'react';
import { chat } from '../../services/api';
import { Send, User, Bot, Loader, History, X, MessageSquare, Mic, Square } from 'lucide-react';

const Chatbot = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I am your inventory assistant. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [sessions, setSessions] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const messagesEndRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Cleanup media recorder on unmount
    useEffect(() => {
        return () => {
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                mediaRecorderRef.current.stop();
            }
        };
    }, []);

    const loadHistory = async () => {
        try {
            const response = await chat.getSessions();
            if (response.data.success) {
                setSessions(response.data.sessions);
            }
        } catch (err) {
            console.error("Failed to load history:", err);
        }
    };

    const loadSession = async (sessionId) => {
        try {
            setIsLoading(true);
            const response = await chat.getHistory(sessionId);
            if (response.data.success) {
                setMessages(response.data.messages);
                setCurrentConversationId(sessionId);
                setShowHistory(false);
            }
        } catch (err) {
            console.error("Failed to load session:", err);
        } finally {
            setIsLoading(false);
        }
    };

    const startNewChat = () => {
        setMessages([
            { role: 'assistant', content: 'Hello! I am your inventory assistant. How can I help you today?' }
        ]);
        setCurrentConversationId(null);
        setShowHistory(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const payload = {
                question: userMessage.content,
                conversation_id: currentConversationId
            };

            const response = await chat.query(payload);
            if (response.data.success) {
                setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
                if (response.data.conversation_id && !currentConversationId) {
                    setCurrentConversationId(response.data.conversation_id);
                }
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error." }]);
            }
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: 'assistant', content: "Network error. Please try again." }]);
        } finally {
            setIsLoading(false);
        }
    };

    // ─── Voice Recording ───────────────────────────────────────
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus'
                    : 'audio/webm',
            });
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Stop all tracks to release the microphone
                stream.getTracks().forEach(track => track.stop());

                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                audioChunksRef.current = [];

                // Send to backend for transcription
                setIsTranscribing(true);
                try {
                    const response = await chat.transcribe(audioBlob);
                    if (response.data.success && response.data.text) {
                        setInput(prev => prev ? `${prev} ${response.data.text}` : response.data.text);
                    } else {
                        console.error("Transcription returned no text");
                    }
                } catch (err) {
                    console.error("Transcription failed:", err);
                    alert("Voice transcription failed. Please check your Sarvam AI API key.");
                } finally {
                    setIsTranscribing(false);
                }
            };

            mediaRecorder.start();
            setIsRecording(true);
        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Please allow microphone access to use voice input.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const handleVoiceClick = () => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    return (
        <div className="flex bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden h-[calc(100vh-8rem)] relative">

            {/* History Sidebar (Mobile/Overlay style) */}
            {showHistory && (
                <div className="absolute inset-0 z-10 flex">
                    <div className="w-64 bg-slate-50 border-r border-slate-200 flex flex-col h-full animate-in slide-in-from-left duration-200">
                        <div className="p-4 border-b border-slate-200 flex justify-between items-center">
                            <h3 className="font-semibold text-slate-700">History</h3>
                            <button onClick={() => setShowHistory(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-3">
                            <button
                                onClick={startNewChat}
                                className="w-full text-left px-3 py-2 rounded-lg bg-blue-100 text-blue-700 font-medium hover:bg-blue-200 mb-4 flex items-center gap-2"
                            >
                                <MessageSquare size={16} />
                                New Chat
                            </button>

                            <div className="space-y-1 overflow-y-auto max-h-[calc(100%-80px)]">
                                {sessions.length === 0 ? (
                                    <p className="text-xs text-slate-400 text-center py-4">No recent history</p>
                                ) : (
                                    sessions.map(session => (
                                        <button
                                            key={session.id}
                                            onClick={() => loadSession(session.id)}
                                            className={`w-full text-left px-3 py-3 rounded-lg text-sm hover:bg-white hover:shadow-sm transition-all border border-transparent hover:border-slate-100 group ${currentConversationId === session.id ? 'bg-white shadow-sm border-slate-100' : ''}`}
                                        >
                                            <p className="font-medium text-slate-700 truncate">{session.preview}</p>
                                            <p className="text-xs text-slate-400 mt-1">{session.message_count} messages</p>
                                        </button>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex-1 bg-black/20 backdrop-blur-sm" onClick={() => setShowHistory(false)} />
                </div>
            )}

            <div className="flex-1 flex flex-col h-full">
                <div className="p-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
                    <div className="flex items-center gap-2">
                        <Bot className="text-blue-500" size={24} />
                        <div>
                            <h2 className="text-lg font-semibold text-slate-800">AI Assistant</h2>
                            <p className="text-xs text-slate-500">Ask about stock levels, reorders, or analytics</p>
                        </div>
                    </div>
                    <button
                        onClick={() => {
                            setShowHistory(true);
                            loadHistory();
                        }}
                        className="p-2 text-slate-500 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
                    >
                        <History size={20} />
                        <span>History</span>
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.map((msg, index) => (
                        <div
                            key={index}
                            className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                        >
                            <div className={`p-2 rounded-full shrink-0 ${msg.role === 'user' ? 'bg-blue-100' : 'bg-slate-100'}`}>
                                {msg.role === 'user' ? <User size={20} className="text-blue-600" /> : <Bot size={20} className="text-slate-600" />}
                            </div>

                            <div
                                className={`max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-tr-none'
                                    : 'bg-slate-100 text-slate-800 rounded-tl-none'
                                    }`}
                            >
                                {msg.content}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex items-center gap-2 text-slate-400 text-sm ml-12">
                            <Loader size={16} className="animate-spin" />
                            Thinking...
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form onSubmit={handleSubmit} className="p-4 border-t border-slate-100 bg-white">
                    {/* Transcribing indicator */}
                    {isTranscribing && (
                        <div className="flex items-center gap-2 text-blue-500 text-xs mb-2 px-1">
                            <Loader size={12} className="animate-spin" />
                            Transcribing your voice...
                        </div>
                    )}
                    {/* Recording indicator */}
                    {isRecording && (
                        <div className="flex items-center gap-2 text-red-500 text-xs mb-2 px-1">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                            </span>
                            Recording... Click the stop button when done.
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder={isTranscribing ? "Transcribing..." : "Type your question..."}
                            className="flex-1 px-4 py-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            disabled={isLoading || isTranscribing}
                        />
                        {/* Voice button */}
                        <button
                            type="button"
                            onClick={handleVoiceClick}
                            disabled={isLoading || isTranscribing}
                            className={`p-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed ${isRecording
                                    ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                }`}
                            title={isRecording ? "Stop recording" : "Start voice input"}
                        >
                            {isRecording ? <Square size={20} /> : <Mic size={20} />}
                        </button>
                        {/* Send button */}
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim() || isTranscribing}
                            className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Send size={20} />
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default Chatbot;
