// @TASK P3-S1-T1 - Custom hook for Cytoscape.js instance management
import { useRef, useEffect, useCallback } from 'react';
import cytoscape from 'cytoscape';
import type { Core, ElementDefinition, Stylesheet } from 'cytoscape';

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
}

export function useCytoscape({
  elements,
  stylesheet,
  onNodeClick,
}: UseCytoscapeOptions): UseCytoscapeReturn {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const onNodeClickRef = useRef(onNodeClick);
  const fittedRef = useRef(false);

  // Keep callback ref current without reinitializing cytoscape
  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);

  // Initialize cytoscape once when container mounts
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const cy = cytoscape({
      container,
      elements,
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
    fittedRef.current = false;
    initDoneRef.current = false; // Reset for StrictMode double-mount

    // Diagnostic: log init state
    console.log('[Cytoscape] Init:', {
      elements: elements.length,
      containerW: container.clientWidth,
      containerH: container.clientHeight,
    });

    // Use ResizeObserver to fit when container actually has dimensions
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) {
        cy.resize();
        if (!fittedRef.current) {
          fittedRef.current = true;
          cy.fit(undefined, 60);
          console.log('[Cytoscape] Fit via ResizeObserver:', { width, height, nodes: cy.nodes().length });
        }
      }
    });
    observer.observe(container);

    // Fallback: if ResizeObserver hasn't triggered fit after 500ms, force it
    const fallbackTimer = setTimeout(() => {
      if (!fittedRef.current) {
        cy.resize();
        fittedRef.current = true;
        cy.fit(undefined, 60);
        console.log('[Cytoscape] Fit via fallback timer:', {
          containerW: container.clientWidth,
          containerH: container.clientHeight,
          nodes: cy.nodes().length,
          zoom: cy.zoom(),
        });
      }
    }, 500);

    return () => {
      clearTimeout(fallbackTimer);
      observer.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Track whether the init effect has completed at least once
  const initDoneRef = useRef(false);

  // Update elements when data changes (skip runs where init just created cy with these elements)
  const prevElementsRef = useRef(elements);
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || elements.length === 0) return;

    // Skip if elements haven't actually changed (init already used them)
    if (prevElementsRef.current === elements && initDoneRef.current) {
      return;
    }
    prevElementsRef.current = elements;

    // On the very first run, just mark init as done — init effect already has these elements
    if (!initDoneRef.current) {
      initDoneRef.current = true;
      return;
    }

    cy.batch(() => {
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

      // Remove elements no longer in data
      const incomingIds = new Set(elements.map((el) => el.data.id as string));
      cy.elements().forEach((el) => {
        if (!incomingIds.has(el.id())) {
          el.remove();
        }
      });
    });

    cy.layout({ name: 'preset' }).run();
    cy.fit(undefined, 60);
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

  return { containerRef, cy: cyRef, zoomIn, zoomOut, fitToScreen, focusNode, getZoomPercent };
}
