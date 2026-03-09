const API_URL = import.meta.env.VITE_BACKEND_URL || '';

class PushNotificationService {
  constructor() {
    this.registration = null;
    this.subscription = null;
    this.vapidPublicKey = null;
  }

  async init() {
    if (!('serviceWorker' in navigator)) {
      console.log('Service workers not supported');
      return false;
    }

    if (!('PushManager' in window)) {
      console.log('Push notifications not supported');
      return false;
    }

    try {
      this.registration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service worker registered');
      
      if (!this.vapidPublicKey) {
        await this.fetchVapidKey();
      }
      
      return true;
    } catch (error) {
      console.error('Service worker registration failed:', error);
      return false;
    }
  }

  async fetchVapidKey() {
    try {
      const response = await fetch(`${API_URL}/api/push/vapid-key`);
      if (response.ok) {
        const data = await response.json();
        this.vapidPublicKey = data.vapid_public_key;
        console.log('VAPID key fetched from server');
      }
    } catch (error) {
      console.error('Error fetching VAPID key:', error);
    }
  }

  async requestPermission() {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }

  async getSubscription() {
    if (!this.registration) {
      await this.init();
    }

    if (!this.registration) {
      return null;
    }

    try {
      this.subscription = await this.registration.pushManager.getSubscription();
      return this.subscription;
    } catch (error) {
      console.error('Error getting subscription:', error);
      return null;
    }
  }

  async subscribe(token) {
    if (!this.vapidPublicKey) {
      await this.fetchVapidKey();
    }
    
    if (!this.vapidPublicKey) {
      console.error('VAPID public key not available');
      return null;
    }

    if (!this.registration) {
      await this.init();
    }

    if (!this.registration) {
      console.error('Service worker not registered');
      return null;
    }

    try {
      const existingSubscription = await this.registration.pushManager.getSubscription();
      if (existingSubscription) {
        this.subscription = existingSubscription;
      } else {
        const urlBase64ToUint8Array = (base64String) => {
          const padding = '='.repeat((4 - base64String.length % 4) % 4);
          const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
          const rawData = window.atob(base64);
          const outputArray = new Uint8Array(rawData.length);
          for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
          }
          return outputArray;
        };

        this.subscription = await this.registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(this.vapidPublicKey)
        });
      }

      const response = await fetch(`${API_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(this.subscription.toJSON())
      });

      if (!response.ok) {
        throw new Error('Failed to save subscription to server');
      }

      console.log('Push notification subscription saved');
      return this.subscription;
    } catch (error) {
      console.error('Error subscribing to push notifications:', error);
      return null;
    }
  }

  async unsubscribe(token) {
    if (!this.subscription) {
      this.subscription = await this.getSubscription();
    }

    if (!this.subscription) {
      return true;
    }

    try {
      await fetch(`${API_URL}/api/push/unsubscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ endpoint: this.subscription.endpoint })
      });

      await this.subscription.unsubscribe();
      this.subscription = null;
      console.log('Push notification subscription removed');
      return true;
    } catch (error) {
      console.error('Error unsubscribing from push notifications:', error);
      return false;
    }
  }

  isSupported() {
    return 'serviceWorker' in navigator && 
           'PushManager' in window && 
           'Notification' in window;
  }

  async getPermissionState() {
    if (!this.isSupported()) {
      return 'unsupported';
    }
    return Notification.permission;
  }

  async hasActiveSubscription() {
    const subscription = await this.getSubscription();
    return subscription !== null;
  }
}

export const pushNotificationService = new PushNotificationService();
