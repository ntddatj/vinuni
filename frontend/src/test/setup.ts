import '@testing-library/jest-dom';

// jsdom không implement scrollIntoView — polyfill để component dùng nó (vd ChatbotPanel
// auto-scroll) không ném lỗi trong test.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
