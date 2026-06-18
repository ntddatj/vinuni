import Cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchGraph, expandNode, getSyncStatus } from '@/api/graph';
import type { GraphNode, GraphEdge } from '@/types/graph';
import { useTranslation } from '@/i18n/useTranslation';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { GraphLegend } from './GraphLegend';
import { NodeDetailCard } from './NodeDetailCard';
import styles from './KnowledgeMapTab.module.css';

// Register fcose once at module level to avoid "already registered" error on HMR
Cytoscape.use(fcose);

// Design tokens hardcoded for Cytoscape (cannot read CSS vars at runtime in cy stylesheet)
const TOKEN = {
  stateSuccess: '#10B981',
  stateWarning: '#F59E0B',
  accentBlue: '#2563EB',
  accentViolet: '#8B5CF6',
  surfaceBase: '#FAF9F6',
  inkPrimary: '#1C1917',
  inkSecondary: '#78716C',
  borderHairline: '#E5E2DC',
} as const;

const CY_STYLE: Cytoscape.StylesheetStyle[] = [
  {
    selector: 'node[label="paper"][state="full_text"]',
    style: {
      shape: 'ellipse',
      'background-color': TOKEN.surfaceBase,
      'border-color': TOKEN.stateSuccess,
      'border-width': 3,
      'border-style': 'solid',
      label: 'data(title)',
      'font-size': 10,
      color: TOKEN.inkPrimary,
      'text-wrap': 'ellipsis',
      'text-max-width': '80px',
      width: '40px',
      height: '40px',
    },
  },
  {
    selector: 'node[label="paper"][state="metadata_only"]',
    style: {
      shape: 'ellipse',
      'background-color': TOKEN.surfaceBase,
      'border-color': TOKEN.stateWarning,
      'border-width': 2,
      'border-style': 'dashed',
      label: 'data(title)',
      'font-size': 10,
      color: TOKEN.inkPrimary,
      'text-wrap': 'ellipsis',
      'text-max-width': '80px',
      width: '40px',
      height: '40px',
    },
  },
  {
    selector: 'node[label="author"]',
    style: {
      shape: 'diamond',
      'background-color': TOKEN.accentViolet,
      'border-width': 0,
      label: 'data(title)',
      'font-size': 9,
      color: TOKEN.inkSecondary,
      'text-wrap': 'ellipsis',
      'text-max-width': '60px',
      width: '24px',
      height: '24px',
    },
  },
  {
    selector: 'edge[type="AUTHORED_BY"]',
    style: {
      'line-color': TOKEN.accentViolet,
      'line-style': 'dashed',
      width: 1.5,
      'target-arrow-shape': 'none',
    },
  },
  {
    selector: 'edge[type="CITES"]',
    style: {
      'line-color': TOKEN.accentBlue,
      'line-style': 'solid',
      width: 1.5,
      'target-arrow-shape': 'triangle',
      'target-arrow-color': TOKEN.accentBlue,
      'curve-style': 'bezier',
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-width': 3,
      'border-color': TOKEN.accentBlue,
    },
  },
];

interface KnowledgeMapTabProps {
  projectId: string | null;
}

export function KnowledgeMapTab({ projectId }: KnowledgeMapTabProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Cytoscape.Core | null>(null);
  const activeTab = useWorkspaceStore((s) => s.activeTab);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [showAuthors, setShowAuthors] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [cyReady, setCyReady] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);

  // Giữ showAuthors mới nhất để áp lại sau khi load/expand mà không cần đưa vào deps.
  const showAuthorsRef = useRef(showAuthors);
  const lastSyncingRef = useRef(false);
  showAuthorsRef.current = showAuthors;

  const applyAuthorVisibility = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (showAuthorsRef.current) {
      cy.elements('[label="author"]').style('display', 'element');
      cy.edges('[type="AUTHORED_BY"]').style('display', 'element');
    } else {
      cy.elements('[label="author"]').style('display', 'none');
      cy.edges('[type="AUTHORED_BY"]').style('display', 'none');
    }
  }, []);

  // Build cy elements from node/edge lists
  const toCyElements = useCallback(
    (nodes: GraphNode[], edges: GraphEdge[]): Cytoscape.ElementDefinition[] => {
      const nodeEls: Cytoscape.ElementDefinition[] = nodes.map((n) => ({
        group: 'nodes' as const,
        data: {
          id: n.id,
          label: n.label,
          title: n.title,
          state: n.state ?? '',
          year: n.year,
          abstract: n.abstract,
          authors: n.authors,
          project_id: n.project_id,
        },
      }));
      const edgeEls: Cytoscape.ElementDefinition[] = edges.map((e) => ({
        group: 'edges' as const,
        data: { id: e.id, source: e.source, target: e.target, type: e.type },
      }));
      return [...nodeEls, ...edgeEls];
    },
    [],
  );

  // Init Cytoscape once (when container mounts)
  useEffect(() => {
    if (!containerRef.current) return;
    const cy = Cytoscape({
      container: containerRef.current,
      elements: [],
      style: CY_STYLE,
      layout: { name: 'preset' },
      userZoomingEnabled: true,
      userPanningEnabled: true,
    });
    cyRef.current = cy;
    setCyReady(true);

    // Single-click → select node for detail card
    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data();
      setSelectedNode({
        id: nodeData.id,
        label: nodeData.label,
        title: nodeData.title,
        authors: nodeData.authors ?? [],
        year: nodeData.year ?? null,
        abstract: nodeData.abstract ?? null,
        state: nodeData.state || null,
        project_id: nodeData.project_id ?? null,
      });
    });

    // Click canvas background → close card
    cy.on('tap', (evt) => {
      if (evt.target === cy) setSelectedNode(null);
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
      setCyReady(false);
    };
  }, []);

  const loadGraph = useCallback(
    async (targetProjectId: string, isCancelled: () => boolean = () => false) => {
      const cy = cyRef.current;
      if (!cy) return;

      setLoading(true);
      setError(false);
      setSelectedNode(null);

      try {
        const data = await fetchGraph(targetProjectId);
        if (isCancelled() || !cyRef.current) return;
        cy.elements().remove();
        const elements = toCyElements(data.nodes, data.edges);
        cy.add(elements);
        cy.layout({ name: 'fcose', animate: false } as Parameters<typeof cy.layout>[0]).run();
        applyAuthorVisibility();
        setHasMore(data.has_more);
        setGraphNodes(data.nodes);
        setGraphEdges(data.edges);
      } catch {
        if (isCancelled()) return;
        setError(true);
        setGraphNodes([]);
        setGraphEdges([]);
        cyRef.current?.elements().remove();
      } finally {
        if (!isCancelled()) setLoading(false);
      }
    },
    [toCyElements, applyAuthorVisibility],
  );

  // Load graph after Cytoscape exists and the graph tab is visible.
  useEffect(() => {
    if (!projectId) {
      cyRef.current?.elements().remove();
      setGraphNodes([]);
      setGraphEdges([]);
      setHasMore(false);
      setError(false);
      setSelectedNode(null);
      return;
    }

    if (!cyReady || activeTab !== 'graph') return;

    let cancelled = false;
    void loadGraph(projectId, () => cancelled);

    return () => {
      cancelled = true;
    };
  }, [projectId, cyReady, activeTab, loadGraph]);

  // Author toggle
  useEffect(() => {
    applyAuthorVisibility();
  }, [showAuthors, applyAuthorVisibility]);

  // Sync-status polling (10s interval, chỉ khi tab Bản đồ Tri thức đang active — AC#18)
  useEffect(() => {
    if (!projectId || activeTab !== 'graph' || !cyReady) {
      setSyncing(false);
      lastSyncingRef.current = false;
      return;
    }
    let cancelled = false;

    const poll = () => {
      getSyncStatus(projectId)
        .then((s) => {
          if (cancelled) return;
          setSyncing(s.syncing);
          if (lastSyncingRef.current && !s.syncing && cyReady) {
            void loadGraph(projectId, () => cancelled);
          }
          lastSyncingRef.current = s.syncing;
        })
        .catch(() => { if (!cancelled) setSyncing(false); });
    };

    poll();
    const interval = setInterval(poll, 10_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [projectId, activeTab, cyReady, loadGraph]);

  // Khi tab Bản đồ Tri thức trở nên active: container vừa từ display:none → visible nên
  // Cytoscape (init lúc còn ẩn) đang giữ kích thước 0×0 → cần resize + fit lại, nếu không
  // canvas sẽ trắng trơn dù đã có dữ liệu.
  useEffect(() => {
    if (activeTab !== 'graph') return;
    const cy = cyRef.current;
    if (!cy) return;
    cy.resize();
    if (cy.elements().length > 0) cy.fit(undefined, 30);
  }, [activeTab, graphNodes]);

  // Double-click expand
  const handleExpand = useCallback(
    async (nodeId: string) => {
      if (!projectId || !cyRef.current) return;
      const cy = cyRef.current;
      const existingIds = cy.nodes().map((n) => n.id());
      try {
        const data = await expandNode(projectId, nodeId, existingIds);
        if (!cyRef.current) return;
        if (data.nodes.length === 0) return;
        const newElements = toCyElements(data.nodes, data.edges);
        // Lock existing node positions before adding new elements
        cy.nodes().lock();
        cy.add(newElements);
        cy.nodes().unlock();
        // Layout only new nodes
        const newNodeIds = new Set(data.nodes.map((n) => n.id));
        cy.nodes().filter((n) => newNodeIds.has(n.id())).layout({
          name: 'fcose',
          animate: true,
        } as Parameters<typeof cy.layout>[0]).run();
        // Áp lại trạng thái ẩn/hiện author cho node/edge vừa thêm.
        applyAuthorVisibility();
        setGraphNodes((prev) => [...prev, ...data.nodes]);
        setGraphEdges((prev) => [...prev, ...data.edges]);
      } catch {
        // ignore expand errors
      }
    },
    [projectId, toCyElements, applyAuthorVisibility],
  );

  // Attach dblclick expand
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const handler = (evt: Cytoscape.EventObject) => {
      const nodeData = evt.target.data();
      if (nodeData.label === 'paper') handleExpand(evt.target.id());
    };
    cy.on('dblclick', 'node', handler);
    return () => { cy.off('dblclick', 'node', handler); };
  }, [handleExpand]);

  const resetView = () => {
    cyRef.current?.fit();
  };

  // QUAN TRỌNG: KHÔNG return sớm khi !projectId. Container Cytoscape phải luôn được
  // render để init effect (deps []) khởi tạo cy ngay lúc mount. Nếu return sớm lúc
  // projectId còn null (trang vừa load, projectStore chưa fetch xong), container không
  // tồn tại → init bỏ qua → cyReady kẹt false → graph không bao giờ load dù projectId
  // có sau đó. Trạng thái "chọn dự án" hiển thị bằng overlay thay vì thay thế cây DOM.
  return (
    <div className={styles.container}>
      <div className={styles.toolbar}>
        <label className={styles.toolbarToggle}>
          <input
            type="checkbox"
            checked={showAuthors}
            onChange={(e) => setShowAuthors(e.target.checked)}
          />
          {t('graph.showAuthors')}
        </label>
        <button className={styles.resetBtn} onClick={resetView} type="button">
          {t('graph.resetView')}
        </button>
      </div>

      <div className={styles.canvasWrapper}>
        {!projectId && (
          <div className={styles.emptyOverlay}>{t('graph.selectProject')}</div>
        )}
        {projectId && loading && (
          <div className={styles.loadingOverlay}>{t('graph.loading')}</div>
        )}
        {projectId && error && !loading && (
          <div className={styles.emptyOverlay}>{t('graph.error')}</div>
        )}
        {projectId && !loading && !error && graphNodes.length === 0 && (
          <div className={styles.emptyOverlay}>{t('graph.emptyGraph')}</div>
        )}
        {syncing && !loading && (
          <div className={styles.syncBadge}>{t('graph.syncing')}</div>
        )}
        {hasMore && !loading && (
          <div className={styles.hasMoreBanner}>{t('graph.hasMore')}</div>
        )}

        <div ref={containerRef} className={styles.canvas} />

        <GraphLegend />

        {selectedNode && (
          <NodeDetailCard
            node={selectedNode}
            allNodes={graphNodes}
            allEdges={graphEdges}
            onClose={() => setSelectedNode(null)}
            onExpand={selectedNode.label === 'paper' ? () => handleExpand(selectedNode.id) : undefined}
          />
        )}
      </div>
    </div>
  );
}
