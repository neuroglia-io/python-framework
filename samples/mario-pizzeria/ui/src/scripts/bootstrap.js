/**
 * Bootstrap JS components import file
 * Import only the components we need to reduce bundle size
 */

// Import only specific components we need instead of the entire library
// These imports are using the direct paths to minimize bundle size further
import Modal from 'bootstrap/js/dist/modal';
import Toast from 'bootstrap/js/dist/toast';
import Collapse from 'bootstrap/js/dist/collapse';
import Dropdown from 'bootstrap/js/dist/dropdown';

// Make components available globally with the same structure expected in the code
const bootstrap = {
  Modal,
  Toast,
  Collapse,
  Dropdown
};

// Expose to window for global access (maintains compatibility with existing code)
window.bootstrap = bootstrap;

// Export as default
export default bootstrap;
