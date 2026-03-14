/**
 * DiaIntel — Custom Hooks
 * Reusable React hooks for data fetching and state management.
 */

import { useState, useEffect, useCallback } from 'react';
import wsService from '../services/websocket';

/**
 * useApi — Generic data fetching hook with loading/error states.
 */
export function useApi(fetchFn, deps = []) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await fetchFn();
            setData(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Failed to fetch data');
        } finally {
            setLoading(false);
        }
    }, deps);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    return { data, loading, error, refetch: fetchData };
}

/**
 * useWebSocket — WebSocket connection hook.
 */
export function useWebSocket() {
    const [isConnected, setIsConnected] = useState(false);
    const [lastUpdate, setLastUpdate] = useState(null);

    useEffect(() => {
        const handleConnect = () => setIsConnected(true);
        const handleDisconnect = () => setIsConnected(false);
        const handleUpdate = (data) => setLastUpdate(data);

        wsService.on('connected', handleConnect);
        wsService.on('disconnected', handleDisconnect);
        wsService.on('signal_count', handleUpdate);
        wsService.on('processing_progress', handleUpdate);

        wsService.connect();

        return () => {
            wsService.off('connected', handleConnect);
            wsService.off('disconnected', handleDisconnect);
            wsService.off('signal_count', handleUpdate);
            wsService.off('processing_progress', handleUpdate);
        };
    }, []);

    return { isConnected, lastUpdate };
}

/**
 * useToast — Toast notification hook.
 */
export function useToast() {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', duration = 4000) => {
        const id = Date.now();
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, duration);
    }, []);

    return { toasts, addToast };
}
