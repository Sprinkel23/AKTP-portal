import React, { createContext, useContext, useEffect, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = sessionStorage.getItem("aktp_user");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = sessionStorage.getItem("aktp_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .get("/api/auth/me")
      .then((res) => {
        setUser(res.data);
        sessionStorage.setItem("aktp_user", JSON.stringify(res.data));
      })
      .catch(() => {
        sessionStorage.removeItem("aktp_token");
        sessionStorage.removeItem("aktp_user");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const loginSuccess = (token, userData) => {
    sessionStorage.setItem("aktp_token", token);
    sessionStorage.setItem("aktp_user", JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    sessionStorage.removeItem("aktp_token");
    sessionStorage.removeItem("aktp_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginSuccess, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
