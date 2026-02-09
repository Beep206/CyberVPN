/**
 * MSW server instance for Node.js test environment.
 *
 * This sets up MSW to intercept HTTP requests made by axios/fetch
 * during Vitest test runs. The handlers provide realistic mock
 * responses matching the CyberVPN backend API contract.
 *
 * Usage in tests:
 *   - The server is started/stopped automatically via test/setup.ts.
 *   - To override a handler in a specific test, use:
 *       server.use(http.get('/api/v1/auth/me', () => HttpResponse.json(...)))
 *     The override is automatically reset after each test via resetHandlers().
 */
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
