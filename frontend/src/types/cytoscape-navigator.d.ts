// Type declaration for cytoscape-navigator (no official @types package)
// https://github.com/cytoscape/cytoscape.js-navigator

declare module 'cytoscape-navigator' {
  import type { Core } from 'cytoscape';

  interface NavigatorOptions {
    /** A DOM element or CSS selector string for the minimap container. */
    container?: HTMLElement | string | false;
    /** Frames per second for live view updates. 0 = instant, false = only on drag end. */
    viewLiveFramerate?: number | false;
    /** Milliseconds delay to distinguish double-click from single-click. */
    dblClickDelay?: number;
    /** Whether to destroy the container element when the plugin is destroyed. */
    removeCustomContainer?: boolean;
    /** Milliseconds to throttle rerender updates for performance. */
    rerenderDelay?: number;
  }

  interface NavigatorInstance {
    destroy(): void;
  }

  // Augment the Cytoscape Core type so cy.navigator() is recognised
  interface CytoscapeNavigatorCore extends Core {
    navigator(options?: NavigatorOptions): NavigatorInstance;
  }

  const register: (cytoscape: (ext: string, fn: unknown) => void) => void;
  export = register;
}
