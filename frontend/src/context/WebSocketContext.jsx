import { useEffect, useState, createContext, useContext, useRef } from 'react';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

/**
 * Derives the WebSocket base URL from the Vite API URL env variable.
 * e.g. "http://localhost:8000/api" → "ws://localhost:8000"
 *      "https://api.example.com/api" → "wss://api.example.com"
 */
function getWsBaseUrl() {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    try {
        const parsed = new URL(apiUrl);
        const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${wsProtocol}//${parsed.host}`;
    } catch {
        // Fallback for relative URLs or parse failures
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${wsProtocol}//${window.location.host}`;
    }
}

export function WebSocketProvider({ children }) {
    const [alerts, setAlerts] = useState([]);
    const { user } = useAuth();
    const reconnectTimeoutRef = useRef(null);

    useEffect(() => {
        if (!user) return;

        // Guard against calling connect() after the component has unmounted
        let isMounted = true;
        let ws = null;

        const connect = () => {
            if (!isMounted) return;

            // Retrieve the token fresh on every (re)connect attempt
            const token = localStorage.getItem('access_token');
            if (!token) {
                console.warn('WebSocket: no access_token found, skipping connect');
                return;
            }

            const wsBase = getWsBaseUrl();
            const wsUrl = `${wsBase}/ws/alerts?token=${encodeURIComponent(token)}`;

            try {
                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    if (!isMounted) { ws.close(); return; }
                    console.log('[WS] Connected to alerts stream');
                };

                ws.onmessage = (event) => {
                    if (!isMounted) return;
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'low_stock_alert') {
                            setAlerts(prev => [data, ...prev].slice(0, 10));
                        }
                        // Ignore pong frames silently
                    } catch (err) {
                        console.error('[WS] Failed to parse message', err);
                    }
                };

                ws.onclose = (event) => {
                    if (!isMounted) return;
                    // Code 4001 = authentication failure — do not reconnect
                    if (event.code === 4001) {
                        console.warn('[WS] Authentication rejected — not reconnecting:', event.reason);
                        return;
                    }
                    console.log('[WS] Disconnected, reconnecting in 3s...');
                    // Cancel any pending reconnect before scheduling a new one
                    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
                    reconnectTimeoutRef.current = setTimeout(connect, 3000);
                };

                ws.onerror = (err) => {
                    console.error('[WS] Connection error', err);
                };
            } catch (err) {
                console.error('[WS] Failed to instantiate WebSocket', err);
            }
        };

        connect();

        return () => {
            isMounted = false;
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
            if (ws) {
                ws.onclose = null; // Prevent reconnect loop on intentional close
                ws.close();
            }
        };
    }, [user]);

    const clearAlert = (index) => {
        setAlerts(prev => prev.filter((_, i) => i !== index));
    };

    const clearAllAlerts = () => {
        setAlerts([]);
    };

    return (
        <WebSocketContext.Provider value={{ alerts, clearAlert, clearAllAlerts }}>
            {children}
        </WebSocketContext.Provider>
    );
}

export function useWebSocketAlerts() {
    const context = useContext(WebSocketContext);
    if (!context) {
        return { alerts: [], clearAlert: () => {}, clearAllAlerts: () => {} };
    }
    return context;
}