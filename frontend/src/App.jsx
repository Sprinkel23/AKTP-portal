import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import HomePage from "./pages/HomePage";
import PortalHomePage from "./pages/PortalHomePage";
import AdminPortal from "./pages/AdminPortal";
import TeacherPortal from "./pages/TeacherPortal";
import StudentPortal from "./pages/StudentPortal";
import ParentPortal from "./pages/ParentPortal";
import VerifyMarksPage from "./pages/VerifyMarksPage";

function ProtectedRoute({ allowedRole, children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-navy-900 font-semibold">
        Loading AKTP PORTAL...
      </div>
    );
  }
  if (!user) {
    return <Navigate to={`/login/${allowedRole}`} replace />;
  }
  if (user.role !== allowedRole) {
    return <Navigate to={`/${user.role}`} replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PortalHomePage />} />
          <Route path="/website" element={<HomePage />} />
          <Route path="/verify" element={<VerifyMarksPage />} />
          <Route path="/login" element={<PortalHomePage />} />
          <Route path="/login/:role" element={<PortalHomePage />} />
          <Route
            path="/admin/*"
            element={
              <ProtectedRoute allowedRole="admin">
                <AdminPortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/teacher/*"
            element={
              <ProtectedRoute allowedRole="teacher">
                <TeacherPortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/*"
            element={
              <ProtectedRoute allowedRole="student">
                <StudentPortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/parent/*"
            element={
              <ProtectedRoute allowedRole="parent">
                <ParentPortal />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
