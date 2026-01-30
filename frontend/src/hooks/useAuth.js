/**
 * Custom React hook for authentication.
 * TODO: Expose { user, token, login, logout, signup, isLoading }. Persist
 *       token (e.g. localStorage). Used by App, Login, Dashboard, protected routes.
 */
export default function useAuth() {
  return {
    user: null,
    token: null,
    login: () => {},
    logout: () => {},
    signup: () => {},
    isLoading: false,
  };
}
