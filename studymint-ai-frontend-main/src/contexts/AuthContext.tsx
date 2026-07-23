import { createContext, useContext, useEffect, useMemo, useReducer } from "react";
import type { ReactNode } from "react";
import type { User } from "../types";
import * as authApi from "../services/authApi";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
}

type AuthAction =
  | { type: "START" }
  | { type: "SET_SESSION"; user: User; token: string }
  | { type: "SET_USER"; user: User }
  | { type: "LOGOUT" };

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (payload: { full_name: string; email: string; password: string }) => Promise<authApi.RegistrationResponse>;
  verifyEmail: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "START":
      return { ...state, isLoading: true };
    case "SET_SESSION":
      return { user: action.user, token: action.token, isLoading: false };
    case "SET_USER":
      return { ...state, user: action.user, isLoading: false };
    case "LOGOUT":
      return { user: null, token: null, isLoading: false };
    default:
      return state;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    token: localStorage.getItem("studymint_token"),
    isLoading: true
  });

  useEffect(() => {
    const token = localStorage.getItem("studymint_token");
    if (!token) {
      dispatch({ type: "LOGOUT" });
      return;
    }

    authApi
      .getMe()
      .then((user) => dispatch({ type: "SET_USER", user }))
      .catch(() => {
        localStorage.removeItem("studymint_token");
        dispatch({ type: "LOGOUT" });
      });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      async login(email, password) {
        dispatch({ type: "START" });
        try {
          const session = await authApi.login(email, password);
          localStorage.setItem("studymint_token", session.access_token);
          dispatch({ type: "SET_SESSION", user: session.user, token: session.access_token });
        } catch (err) {
          localStorage.removeItem("studymint_token");
          dispatch({ type: "LOGOUT" });
          throw err;
        }
      },
      async register(payload) {
        dispatch({ type: "START" });
        try {
          const result = await authApi.register(payload);
          localStorage.removeItem("studymint_token");
          dispatch({ type: "LOGOUT" });
          return result;
        } catch (err) {
          dispatch({ type: "LOGOUT" });
          throw err;
        }
      },
      async verifyEmail(token) {
        dispatch({ type: "START" });
        try {
          const session = await authApi.verifyEmail(token);
          localStorage.setItem("studymint_token", session.access_token);
          dispatch({ type: "SET_SESSION", user: session.user, token: session.access_token });
        } catch (err) {
          localStorage.removeItem("studymint_token");
          dispatch({ type: "LOGOUT" });
          throw err;
        }
      },
      logout() {
        localStorage.removeItem("studymint_token");
        dispatch({ type: "LOGOUT" });
      }
    }),
    [state]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
