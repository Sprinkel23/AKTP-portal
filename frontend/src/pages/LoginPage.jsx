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
    accent: "bg-[#081B4B] text-gold-400",
    hint: "Institutional governance, faculty payroll, fee verification & result publication.",
  },
  teacher: {
    label: "Faculty Portal",
    icon: BookOpenCheck,
    placeholder: "Enter Teacher Username",
    accent: "bg-[#0A2463] text-white",
    hint: "Attendance register, subject-wise marks entry, fee collection & salary slips.",
  },
  student: {
    label: "Student Portal",
    icon: GraduationCap,
    placeholder: "Student ID (e.g. AK001) or Username",
    accent: "bg-[#0A2463] text-white",
    hint: "Examination schedules, practice tests, attendance & verified marks cards.",
  },
  parent: {
    label: "Parent Portal",
    icon: Users,
    placeholder: "Enter Parent Username or Mobile",
    accent: "bg-[#0A2463] text-white",
    hint: "Student attendance monitoring, verified receipts & published results.",
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
    <div className="min-h-screen bg-[#eef2f6] flex flex-col">
      <div className="bg-[#081B4B] text-white border-b-2 border-[#C9A227]">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="inline-flex items-center gap-3 hover:opacity-90 transition">
            <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-10 h-10 object-contain" />
            <div>
              <div className="font-bold text-base tracking-wide leading-tight">AK TUITION — INSTITUTIONAL PORTAL</div>
              <div className="text-[11px] text-gold-400 uppercase tracking-widest">Authorized Personnel &amp; Student Access</div>
            </div>
          </Link>
          <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-slate-200 hover:text-gold-400 font-semibold border border-white/20 px-3 py-1.5 rounded">
            <ArrowLeft className="w-3.5 h-3.5" /> Portal Home
          </Link>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white rounded-lg border border-slate-300 border-t-4 border-t-[#0A2463] shadow-lg p-6 sm:p-8">
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
                  className={`flex flex-col items-center gap-1 py-2.5 px-2 rounded text-xs font-bold border transition ${
                    active
                      ? "bg-[#0A2463] text-white border-[#0A2463]"
                      : "bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100"
                  }`}
                >
                  <TabIcon className={`w-4 h-4 ${active ? "text-gold-400" : "text-[#0A2463]"}`} />
                  <span className="capitalize">{key}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-slate-200">
            <div className={`w-10 h-10 rounded flex items-center justify-center shrink-0 ${meta.accent}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-lg text-[#0A2463]">{meta.label}</h2>
              <p className="text-xs text-slate-500">{meta.hint}</p>
            </div>
          </div>

          {error && <div className="mb-4 p-3 rounded bg-red-50 border border-red-200 text-xs text-red-700 font-medium">{error}</div>}
          {infoMsg && <div className="mb-4 p-3 rounded bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium break-all">{infoMsg}</div>}

          {mode === "login" && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                  {selectedRole === "student" ? "Student ID or Username" : "Username or Email"}
                </label>
                <input
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3.5 py-2.5 text-sm focus:border-[#0A2463] outline-none"
                  placeholder={meta.placeholder}
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3.5 py-2.5 text-sm focus:border-[#0A2463] outline-none"
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
                  className="text-[#0A2463] hover:underline font-semibold inline-flex items-center gap-1"
                >
                  <KeyRound className="w-3.5 h-3.5" /> Forgot Password?
                </button>
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2.5 rounded bg-[#0A2463] hover:bg-[#102F7A] text-white font-bold text-sm transition disabled:opacity-60"
              >
                {submitting ? "Verifying Credentials..." : `Sign in to ${meta.label}`}
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
                  className="w-full rounded border border-slate-300 px-3.5 py-2.5 text-sm"
                  placeholder="Username, Student ID, or Email"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="px-5 py-2.5 rounded bg-[#0A2463] text-white text-sm font-bold">
                  Generate Reset Token
                </button>
                <button type="button" onClick={() => setMode("login")} className="px-4 py-2.5 rounded border text-sm">
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
                  className="w-full rounded border border-slate-300 px-3.5 py-2.5 text-sm font-mono"
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
                  className="w-full rounded border border-slate-300 px-3.5 py-2.5 text-sm"
                />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="px-5 py-2.5 rounded bg-[#0A2463] text-white text-sm font-bold">
                  Reset Password
                </button>
                <button type="button" onClick={() => setMode("login")} className="px-4 py-2.5 rounded border text-sm">
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
