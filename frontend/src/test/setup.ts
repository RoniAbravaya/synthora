/**
 * Vitest Global Setup
 * 
 * This file runs before all tests to set up the testing environment.
 */

import '@testing-library/jest-dom';
import { vi } from 'vitest';

// =============================================================================
// Mock Browser APIs
// =============================================================================

// Mock window.matchMedia for responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
});

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: MockResizeObserver,
});

// Mock scrollTo
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: vi.fn(),
});

// =============================================================================
// Mock localStorage
// =============================================================================

const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// =============================================================================
// Mock Firebase
// =============================================================================

vi.mock('@/lib/firebase', () => ({
  auth: {
    currentUser: null,
    onAuthStateChanged: vi.fn((callback) => {
      callback(null);
      return vi.fn(); // unsubscribe function
    }),
    signInWithPopup: vi.fn(),
    signOut: vi.fn(),
  },
}));

// =============================================================================
// Mock React Router
// =============================================================================

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: '/', search: '', hash: '', state: null }),
    useParams: () => ({}),
  };
});

// =============================================================================
// Console Error Suppression for Known Issues
// =============================================================================

const originalError = console.error;
console.error = (...args) => {
  // Suppress React Router future flags warning in tests
  if (args[0]?.includes?.('React Router Future Flag Warning')) {
    return;
  }
  // Suppress act() warnings that are sometimes unavoidable
  if (args[0]?.includes?.('Warning: An update to')) {
    return;
  }
  originalError.call(console, ...args);
};

// =============================================================================
// Global Test Utilities
// =============================================================================

// Add custom matchers or global utilities here if needed

