import { httpClient } from '@/utils';

export interface KBDocument {
  doc_id: string;
  title: string;
  category: string;
  source: string;
  total_chunks: number;
  preview: string;
}

export interface KBChunk {
  text: string;
  title: string;
  category: string;
  source: string;
  doc_id: string;
  chunk_index: number;
  score: number;
}

export interface KBStats {
  total_chunks: number;
  total_documents: number;
  categories: Record<string, number>;
  chroma_dir: string;
}

export interface AddDocumentRequest {
  title: string;
  content: string;
  category?: string;
  source?: string;
}

export interface QueryRequest {
  query: string;
  top_k?: number;
  category?: string;
}

export const listDocuments = async (): Promise<{ total: number; documents: KBDocument[] }> =>
  httpClient.get('/api/v1/knowledge-base/documents');

export const addDocument = async (data: AddDocumentRequest): Promise<{ doc_id: string; message: string }> =>
  httpClient.post('/api/v1/knowledge-base/documents', data);

export const deleteDocument = async (docId: string): Promise<{ deleted_chunks: number }> =>
  httpClient.delete(`/api/v1/knowledge-base/documents/${docId}`);

export const queryKnowledgeBase = async (data: QueryRequest): Promise<{ results: KBChunk[] }> =>
  httpClient.post('/api/v1/knowledge-base/query', data);

export const getKBStats = async (): Promise<KBStats> =>
  httpClient.get('/api/v1/knowledge-base/stats');

export const uploadKBFile = async (
  file: File,
  category = '通用',
): Promise<{ doc_id: string; filename: string; message: string }> => {
  const form = new FormData();
  form.append('file', file);
  form.append('category', category);
  return httpClient.post('/api/v1/knowledge-base/upload', form);
};
