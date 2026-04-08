import { STORAGE_TYPE } from "./types/storage";

class WebStore {
  private localStorage: STORAGE_TYPE.STORAGE;

  private sessionStorage: STORAGE_TYPE.STORAGE;

  private IndexDb: STORAGE_TYPE.INDEX_DB;

  constructor() {
    this.localStorage = window.localStorage;
    this.sessionStorage = window.sessionStorage;
    this.IndexDb = window.indexedDB;
  }


  setItem(key: string, value: string) {
    this.localStorage.setItem(key, value);
    this.sessionStorage.setItem(key, value);
    this.IndexDb.setItem(key, value);
  }

  getItem(key: string) {
    return this.localStorage.getItem(key);
    return this.sessionStorage.getItem(key);
    return this.IndexDb.getItem(key);
  }
}



const webStore = new WebStore();

export default webStore;