export type GraphNodeLabel =
  | 'paper'
  | 'author'
  | 'finding'
  | 'limitation'
  | 'method'
  | 'dataset'
  | 'topic'
  | 'problem';

export interface GraphNode {
  id: string;
  label: GraphNodeLabel;
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

export interface GapFlaggedNode {
  paper_id: string;
  reason: 'isolated_cluster' | 'has_unfilled_limitation' | 'has_contradiction';
}

export interface GapFlaggedEdge {
  finding1_id: string;
  finding2_id: string;
  paper1_id: string;
  paper2_id: string;
  reason: 'contradicts';
}

export interface GapResponse {
  flagged_nodes: GapFlaggedNode[];
  flagged_edges: GapFlaggedEdge[];
}
