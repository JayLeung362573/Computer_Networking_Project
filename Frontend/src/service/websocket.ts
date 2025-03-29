import { GameState, MessageHandler } from '../types';

class WebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout = 1000; // 1 second
  private isConnecting = false;
  private isDisconnecting = false;

  constructor() {
    this.connect();
  }

  public onMessage(type: string, handler: MessageHandler) {
    console.log('Registering message handler for type:', type);
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    this.messageHandlers.get(type)!.push(handler);
  }

  public sendMessage(type: string, data: any) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send message: WebSocket is not connected');
      return;
    }

    const message = {
      type,
      ...data
    };

    this.ws.send(JSON.stringify(message));
  }

  private connect() {
    if (this.isConnecting || this.isDisconnecting) {
      console.log('Already attempting to connect or disconnecting, skipping...');
      return;
    }

    this.isConnecting = true;
    console.log('Attempting to connect to WebSocket server...');
    
    try {
      this.ws = new WebSocket('ws://localhost:8765');
      
      this.ws.onopen = () => {
        console.log('WebSocket connection opened');
        this.reconnectAttempts = 0;
        this.isConnecting = false;
        this.isDisconnecting = false;
        window.dispatchEvent(new Event('ws:open'));
      };

      this.ws.onclose = () => {
        console.log('WebSocket connection closed');
        this.isConnecting = false;
        this.isDisconnecting = false;
        window.dispatchEvent(new Event('ws:close'));
        if (!this.isDisconnecting) {
          this.handleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
        this.isDisconnecting = false;
        window.dispatchEvent(new CustomEvent('ws:error', { detail: 'Connection error occurred' }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received message:', data);
          
          if (data.type && this.messageHandlers.has(data.type)) {
            const handlers = this.messageHandlers.get(data.type)!;
            handlers.forEach(handler => handler(data));
          }
        } catch (error) {
          console.error('Error handling message:', error);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      this.isConnecting = false;
      this.isDisconnecting = false;
      window.dispatchEvent(new CustomEvent('ws:error', { detail: 'Failed to create WebSocket connection' }));
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && !this.isDisconnecting) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      setTimeout(() => this.connect(), this.reconnectTimeout * this.reconnectAttempts);
    } else {
      console.log('Max reconnection attempts reached');
      window.dispatchEvent(new CustomEvent('ws:error', { detail: 'Failed to reconnect after maximum attempts' }));
    }
  }

  public disconnect() {
    if (this.ws) {
      this.isDisconnecting = true;
      this.ws.close();
      this.ws = null;
      this.messageHandlers.clear();
      this.reconnectAttempts = 0;
    }
  }
}

export const websocketService = new WebSocketService(); 