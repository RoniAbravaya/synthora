/**
 * Test Utilities
 * 
 * Helper functions and wrappers for testing React components.
 */

import React, { ReactElement, ReactNode } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AuthContext, AuthContextType } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { User } from '@/types';

// =============================================================================
// Mock Data
// =============================================================================

export const mockUser: User = {
  id: 'test-user-id',
  firebase_uid: 'firebase-test-uid',
  email: 'test@example.com',
  display_name: 'Test User',
  photo_url: null,
  role: 'free',
  is_active: true,
  created_at: new Date().toISOString(),
  last_login_at: new Date().toISOString(),
};

export const mockPremiumUser: User = {
  ...mockUser,
  id: 'premium-user-id',
  role: 'premium',
  display_name: 'Premium User',
};

export const mockAdminUser: User = {
  ...mockUser,
  id: 'admin-user-id',
  role: 'admin',
  display_name: 'Admin User',
};

// =============================================================================
// Test Query Client
// =============================================================================

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// =============================================================================
// Mock Auth Context
// =============================================================================

export const mockAuthContext: AuthContextType = {
  currentUser: null,
  firebaseUser: null,
  isLoading: false,
  isAuthenticated: false,
  login: async () => {},
  logout: async () => {},
  refreshUser: async () => {},
};

export const mockAuthenticatedContext: AuthContextType = {
  ...mockAuthContext,
  currentUser: mockUser,
  isAuthenticated: true,
};

export const mockPremiumAuthContext: AuthContextType = {
  ...mockAuthContext,
  currentUser: mockPremiumUser,
  isAuthenticated: true,
};

export const mockAdminAuthContext: AuthContextType = {
  ...mockAuthContext,
  currentUser: mockAdminUser,
  isAuthenticated: true,
};

// =============================================================================
// Provider Wrapper
// =============================================================================

interface WrapperProps {
  children: ReactNode;
  authContext?: AuthContextType;
  queryClient?: QueryClient;
}

function AllProviders({
  children,
  authContext = mockAuthContext,
  queryClient,
}: WrapperProps): ReactElement {
  const client = queryClient || createTestQueryClient();

  return (
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={authContext}>
        <ThemeProvider>
          <BrowserRouter>{children}</BrowserRouter>
        </ThemeProvider>
      </AuthContext.Provider>
    </QueryClientProvider>
  );
}

// =============================================================================
// Custom Render Function
// =============================================================================

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  authContext?: AuthContextType;
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
): RenderResult {
  const { authContext, queryClient, ...renderOptions } = options;

  return render(ui, {
    wrapper: ({ children }) => (
      <AllProviders authContext={authContext} queryClient={queryClient}>
        {children}
      </AllProviders>
    ),
    ...renderOptions,
  });
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Wait for a condition to be true
 */
export async function waitForCondition(
  condition: () => boolean,
  timeout = 5000,
  interval = 100
): Promise<void> {
  const startTime = Date.now();
  
  while (!condition()) {
    if (Date.now() - startTime > timeout) {
      throw new Error('Timeout waiting for condition');
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }
}

/**
 * Create a mock API response
 */
export function mockApiResponse<T>(data: T, status = 200) {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {},
  };
}

/**
 * Create a mock API error
 */
export function mockApiError(message: string, status = 400) {
  const error = new Error(message) as any;
  error.response = {
    data: { detail: message },
    status,
    statusText: 'Bad Request',
  };
  return error;
}

// =============================================================================
// Re-export testing library utilities
// =============================================================================

export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';

