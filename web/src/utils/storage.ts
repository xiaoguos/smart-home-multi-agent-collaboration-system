import type { STORAGE_TYPE } from './types/storage';

class WebStore {
  private localStorage: STORAGE_TYPE.STORAGE;

  private sessionStorage: STORAGE_TYPE.STORAGE;

  constructor() {
    this.localStorage = window.localStorage;
    this.sessionStorage = window.sessionStorage;
  }

  setItem(key: string, value: string): void {
    this.localStorage.setItem(key, value);
    this.sessionStorage.setItem(key, value);
  }

  getItem(key: string): string | null {
    return (
      this.localStorage.getItem(key) ?? this.sessionStorage.getItem(key)
    );
  }
}

const webStore = new WebStore();

export default webStore;
