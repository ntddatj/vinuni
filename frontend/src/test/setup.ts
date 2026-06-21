import '@testing-library/jest-dom';

// jsdom không implement scrollIntoView — polyfill để component dùng nó (vd ConversationColumn
// auto-scroll) không ném lỗi trong test.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

// jsdom không implement ResizeObserver — polyfill cho KnowledgeMapTab và các component khác.
if (typeof ResizeObserver === 'undefined') {
  (globalThis as unknown as Record<string, unknown>).ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
