import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Shield, GraduationCap, BookOpenCheck, Users, ArrowLeft, KeyRound } from "lucide-react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const PORTAL_META = {
  admin: {
    label: "Administrator Portal",
    icon: Shield,
    placeholder: "Enter Admin Username",
    accent: "bg-navy-900 text-gold-400",
    hint: "Complete system, student, teacher, fee, exam & result approval control.",
  },
  teacher: {
    label: "Teacher Portal",
    icon: BookOpenCheck,
    placeholder: "Enter Teacher Username",
    accent: "bg-royal-600 text-white",
    hint: "Daily attendance, marks entry, question papers & practice test evaluation.",
  },
  student: {
    label: "Student Portal",
    icon: GraduationCap,
    placeholder: "Student ID (e.g. AK001) or Username",
    accent: "bg-emerald-700 text-white",
    hint: "View timetable, take practice tests, check attendance & download marks cards.",
  },
  parent: {
    label: "Parent Portal",
    icon: Users,
    placeholder: "Enter Parent Username",
    accent: "bg-amber-600 text-white",
    hint: "Monitor your child's attendance, absent dates, fees, exams & published results.",
  },
};

export default function LoginPage() {
  const { role } = useParams();
  const navigate = useNavigate();
  const { user, loginSuccess } = useAuth();

  const initialRole = PORTAL_META[role?.toLowerCase()] ? role.toLowerCase() : "student";
  const [selectedRole, setSelectedRole] = useState(initialRole);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [mode, setMode] = useState("login"); // login, forgot, reset
  const [resetIdentifier, setResetIdentifier] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [infoMsg, setInfoMsg] = useState("");

  useEffect(() => {
    if (role && PORTAL_META[role.toLowerCase()]) {
      setSelectedRole(role.toLowerCase());
    }
  }, [role]);

  useEffect(() => {
    if (user?.role) {
      navigate(`/${user.role}`, { replace: true });
    }
  }, [user, navigate]);

  const meta = PORTAL_META[selectedRole];
  const Icon = meta.icon;

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.post("/api/auth/login", {
        identifier: identifier.trim(),
        password,
        portal_role: selectedRole,
      });
      loginSuccess(res.data.access_token, res.data.user);
      navigate(`/${res.data.user.role}`, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Please verify your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgot = async (e) => {
    e.preventDefault();
    setError("");
    setInfoMsg("");
    try {
      const res = await api.post("/api/auth/forgot-password", { identifier: resetIdentifier });
      setResetToken(res.data.reset_token);
      setInfoMsg(`${res.data.message} Token: ${res.data.reset_token}`);
      setMode("reset");
    } catch (err) {
      setError(err.response?.data?.detail || "Account not found.");
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setError("");
    setInfoMsg("");
    try {
      const res = await api.post("/api/auth/reset-password", { token: resetToken, new_password: newPassword });
      setInfoMsg(res.data.message);
      setMode("login");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not reset password.");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-950 via-navy-900 to-royal-700 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg mb-4 flex items-center justify-between text-white">
        <Link to="/" className="inline-flex items-center gap-2.5 hover:opacity-90 transition">
          <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-11 h-11 object-contain" />
          <div>
            <div className="font-display font-extrabold text-base leading-tight">AK TUITION</div>
            <div className="text-[11px] text-gold-400 font-medium">Learn • Practise • Achieve</div>
          </div>
        </Link>
        <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-blue-200 hover:text-gold-400 font-medium">
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
      </div>

      <div className="max-w-lg w-full bg-white rounded-3xl shadow-2xl p-6 sm:p-8">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-6">
          {Object.entries(PORTAL_META).map(([key, item]) => {
            const TabIcon = item.icon;
            const active = selectedRole === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setSelectedRole(key);
                  setError("");
                  setMode("login");
                }}
                className={`flex flex-col items-center gap-1 py-2.5 px-2 rounded-xl text-xs font-bold border transition ${
                  active
                    ? "bg-navy-900 text-white border-navy-900 shadow"
                    : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-blue-50"
                }`}
              >
                <TabIcon className={`w-4 h-4 ${active ? "text-gold-400" : "text-royal-600"}`} />
                <span className="capitalize">{key}</span>
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-3 mb-5">
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${meta.accent}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-display font-bold text-xl text-navy-900">{meta.label}</h2>
            <p className="text-xs text-slate-500">{meta.hint}</p>
          </div>
        </div>

        {error && <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">{error}</div>}
        {infoMsg && <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium break-all">{infoMsg}</div>}

        {mode === "login" && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                {selectedRole === "student" ? "Student ID or Username" : "Username or Email"}
              </label>
              <input
                required
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:ring-2 focus:ring-royal-500 outline-none"
                placeholder={meta.placeholder}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:ring-2 focus:ring-royal-500 outline-none"
                placeholder="Enter your password"
              />
            </div>
            <div className="flex items-center justify-between text-xs">
              <button
                type="button"
                onClick={() => {
                  setMode("forgot");
                  setError("");
                  setInfoMsg("");
                }}
                className="text-royal-600 hover:underline font-semibold inline-flex items-center gap-1"
              >
                <KeyRound className="w-3.5 h-3.5" /> Forgot Password?
              </button>
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 rounded-xl bg-navy-900 hover:bg-royal-600 text-white font-bold text-sm transition shadow-md disabled:opacity-60"
            >
              {submitting ? "Signing in..." : `Sign in to ${meta.label}`}
            </button>
          </form>
        )}

        {mode === "forgot" && (
          <form onSubmit={handleForgot} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                Enter your Username, Student ID, or Email
              </label>
              <input
                required
                value={resetIdentifier}
                onChange={(e) => setResetIdentifier(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
                placeholder="Username, Student ID, or Email"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="px-5 py-2.5 rounded-xl bg-navy-900 text-white text-sm font-bold">
                Generate Reset Token
              </button>
              <button type="button" onClick={() => setMode("login")} className="px-4 py-2.5 rounded-xl border text-sm">
                Back to Login
              </button>
            </div>
          </form>
        )}

        {mode === "reset" && (
          <form onSubmit={handleReset} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Reset Token</label>
              <input
                required
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">New Password (min 6 chars)</label>
              <input
                type="password"
                required
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="px-5 py-2.5 rounded-xl bg-royal-600 text-white text-sm font-bold">
                Reset Password
              </button>
              <button type="button" onClick={() => setMode("login")} className="px-4 py-2.5 rounded-xl border text-sm">
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
