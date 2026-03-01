// @TASK P3-S1-T1 - Custom hook for Cytoscape.js instance management
import { useRef, useEffect, useCallback } from 'react';
import cytoscape from 'cytoscape';
import type { Core, ElementDefinition, Stylesheet } from 'cytoscape';
import cytoscapeNavigator from 'cytoscape-navigator';

// Register the navigator extension once at module load time.
// cytoscape-navigator exposes a register(cytoscape) function.
cytoscapeNavigator(cytoscape as unknown as Parameters<typeof cytoscapeNavigator>[0]);

interface UseCytoscapeOptions {
  elements: ElementDefinition[];
  stylesheet: Stylesheet[];
  onNodeClick?: (nodeId: string) => void;
}

interface UseCytoscapeReturn {
  containerRef: React.RefObject<HTMLDivElement | null>;
  cy: React.RefObject<Core | null>;
  zoomIn: () => void;
  zoomOut: () => void;
  fitToScreen: () => void;
  focusNode: (nodeId: string) => void;
  getZoomPercent: () => number;
  /** Attach the cytoscape-navigator minimap to the given DOM element. */
  initNavigator: (container: HTMLElement) => void;
}

export function useCytoscape({
  elements,
  stylesheet,
  onNodeClick,
}: UseCytoscapeOptions): UseCytoscapeReturn {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const onNodeClickRef = useRef(onNodeClick);

  // Keep callback ref current without reinitializing cytoscape
  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);

  // Initialize cytoscape EMPTY — elements are synced in a separate effect
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const cy = cytoscape({
      container,
      style: stylesheet,
      layout: { name: 'preset' },
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.2,
    });

    cy.on('tap', 'node[type = "company"]', (evt) => {
      const nodeId = evt.target.id() as string;
      onNodeClickRef.current?.(nodeId);
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync elements into cytoscape whenever they change
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || elements.length === 0) return;

    cy.batch(() => {
      const incomingIds = new Set(elements.map((el) => el.data.id as string));

      // Remove elements no longer in data
      cy.elements().forEach((el) => {
        if (!incomingIds.has(el.id())) {
          el.remove();
        }
      });

      // Add or update elements
      elements.forEach((el) => {
        const existing = cy.getElementById(el.data.id as string);
        if (existing.length > 0) {
          existing.data(el.data);
          if (el.position) {
            existing.position(el.position);
          }
        } else {
          cy.add(el);
        }
      });
    });

    // Apply preset layout then fit after a frame to ensure container has dimensions
    cy.layout({ name: 'preset' }).run();
    requestAnimationFrame(() => {
      cy.resize();
      cy.fit(undefined, 60);
    });
  }, [elements]);

  const zoomIn = useCallback(() => {
    cyRef.current?.zoom({
      level: (cyRef.current.zoom() * 1.25),
      renderedPosition: {
        x: (cyRef.current.width() / 2),
        y: (cyRef.current.height() / 2),
      },
    });
  }, []);

  const zoomOut = useCallback(() => {
    cyRef.current?.zoom({
      level: (cyRef.current.zoom() * 0.8),
      renderedPosition: {
        x: (cyRef.current.width() / 2),
        y: (cyRef.current.height() / 2),
      },
    });
  }, []);

  const fitToScreen = useCallback(() => {
    cyRef.current?.fit(undefined, 60);
  }, []);

  const focusNode = useCallback((nodeId: string) => {
    const cy = cyRef.current;
    if (!cy) return;

    const node = cy.getElementById(nodeId);
    if (node.length === 0) return;

    cy.animate({
      fit: {
        eles: node,
        padding: 120,
      },
      duration: 600,
      easing: 'ease-in-out-cubic',
    });

    // Flash highlight
    node.addClass('focused');
    setTimeout(() => node.removeClass('focused'), 2000);
  }, []);

  const getZoomPercent = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return 100;
    return Math.round(cy.zoom() * 100);
  }, []);

  const initNavigator = useCallback((container: HTMLElement) => {
    const cy = cyRef.current;
    if (!cy) return;
    // cytoscape-navigator adds .navigator() to the Core prototype after registration.
    // Cast through unknown to avoid TypeScript's strict Core type check.
    (cy as unknown as { navigator: (opts: object) => void }).navigator({
      container,
      viewLiveFramerate: 0,
      rerenderDelay: 100,
      removeCustomContainer: false,
    });
  }, []);

  return { containerRef, cy: cyRef, zoomIn, zoomOut, fitToScreen, focusNode, getZoomPercent, initNavigator };
}
