export interface GraphNode {
  id: string;
  label: 'paper' | 'author';
  title: string;
  authors: string[];
  year: number | null;
  abstract: string | null;
  state: 'full_text' | 'metadata_only' | null;
  project_id: string | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'AUTHORED_BY' | 'CITES' | string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  has_more: boolean;
}

export interface SyncStatus {
  syncing: boolean;
}
