/**
 * DiaIntel — WebSocket Service
 * Manages WebSocket connection for live updates.
 */

class WebSocketService {
    constructor() {
        this.ws = null;
        this.listeners = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live-updates`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.emit('connected', {});
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.emit(data.type, data.data);
                } catch (e) {
                    console.error('WebSocket message parse error:', e);
                }
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.emit('disconnected', {});
                this.attemptReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... attempt ${this.reconnectAttempts}`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event).filter((cb) => cb !== callback);
            this.listeners.set(event, callbacks);
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach((callback) => callback(data));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Singleton
const wsService = new WebSocketService();
export default wsService;
