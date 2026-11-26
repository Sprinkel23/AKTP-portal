import React, { useState } from "react";
import { LogOut, Menu, X, KeyRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api/client";

export default function PortalLayout({ title, subtitle, navItems, activeTab, onSelectTab, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [pwdOpen, setPwdOpen] = useState(false);
  const [pwdForm, setPwdForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [pwdMsg, setPwdMsg] = useState("");
  const [pwdErr, setPwdErr] = useState("");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwdMsg("");
    setPwdErr("");
    if (pwdForm.new_password !== pwdForm.confirm_password) {
      setPwdErr("New passwords do not match.");
      return;
    }
    try {
      const res = await api.post("/api/auth/change-password", {
        current_password: pwdForm.current_password,
        new_password: pwdForm.new_password,
      });
      setPwdMsg(res.data.message);
      setPwdForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      setPwdErr(err.response?.data?.detail || "Failed to update password.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col lg:flex-row">
      {/* Mobile Header */}
      <div className="lg:hidden bg-navy-900 text-white px-4 py-3 flex items-center justify-between sticky top-0 z-30 shadow">
        <div className="flex items-center gap-2.5">
          <img src="/ak-tuition-logo.png" alt="AK Tuition" className="w-9 h-9 object-contain" />
          <div>
            <div className="font-bold text-sm leading-tight">AKTP PORTAL</div>
            <div className="text-[11px] text-gold-400">{title}</div>
          </div>
        </div>
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 rounded-lg hover:bg-white/10">
          {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? "block" : "hidden"
        } lg:flex lg:flex-col lg:w-72 bg-navy-900 text-white shrink-0 lg:sticky lg:top-0 lg:h-screen z-20`}
      >
        <div className="p-5 border-b border-white/10 flex items-center gap-3">
          <Link to="/" className="shrink-0">
            <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-12 h-12 object-contain" />
          </Link>
          <div className="min-w-0">
            <div className="font-display font-bold text-base tracking-wide truncate">AK TUITION</div>
            <div className="text-xs text-gold-400 font-medium truncate">Learn • Practise • Achieve</div>
            <div className="text-[11px] text-blue-200 mt-0.5 uppercase tracking-wider">{title}</div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition ${
                  active
                    ? "bg-royal-600 text-white shadow-sm ring-1 ring-gold-400/50"
                    : "text-blue-100 hover:bg-white/10 hover:text-white"
                }`}
              >
                <span className="flex items-center gap-3 truncate">
                  {Icon && <Icon className={`w-4 h-4 shrink-0 ${active ? "text-gold-400" : "text-blue-300"}`} />}
                  <span className="truncate">{item.label}</span>
                </span>
                {item.badge > 0 && (
                  <span className="ml-2 px-2 py-0.5 rounded-full text-[11px] font-bold bg-gold-500 text-navy-950">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10 space-y-2 bg-navy-950/50">
          <div className="text-xs text-blue-200">
            Signed in as <span className="font-semibold text-white block truncate">{user?.full_name}</span>
            <span className="text-gold-400 uppercase text-[10px] tracking-wider">
              {user?.role} • {user?.student_code || user?.teacher_code || user?.username}
            </span>
          </div>
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => setPwdOpen(true)}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium transition"
            >
              <KeyRound className="w-3.5 h-3.5" /> Password
            </button>
            <button
              onClick={handleLogout}
              className="flex-1 inline-flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-red-600/90 hover:bg-red-600 text-xs font-semibold transition"
            >
              <LogOut className="w-3.5 h-3.5" /> Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 min-w-0">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-navy-900">{title}</h1>
            {subtitle && <p className="text-xs sm:text-sm text-slate-500">{subtitle}</p>}
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/website"
              className="text-xs font-semibold text-royal-600 hover:text-navy-900 px-3 py-1.5 rounded-lg bg-blue-50"
            >
              Public Website
            </Link>
          </div>
        </header>
        <div className="p-4 sm:p-6 max-w-7xl mx-auto">{children}</div>
      </main>

      {/* Change Password Modal */}
      {pwdOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-navy-900">Change Account Password</h3>
              <button onClick={() => setPwdOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleChangePassword} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Current Password</label>
                <input
                  type="password"
                  required
                  value={pwdForm.current_password}
                  onChange={(e) => setPwdForm({ ...pwdForm, current_password: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">New Password (min 6 chars)</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={pwdForm.new_password}
                  onChange={(e) => setPwdForm({ ...pwdForm, new_password: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Confirm New Password</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={pwdForm.confirm_password}
                  onChange={(e) => setPwdForm({ ...pwdForm, confirm_password: e.target.value })}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </div>
              {pwdErr && <div className="text-xs text-red-600 bg-red-50 p-2 rounded">{pwdErr}</div>}
              {pwdMsg && <div className="text-xs text-emerald-700 bg-emerald-50 p-2 rounded">{pwdMsg}</div>}
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setPwdOpen(false)} className="px-4 py-2 text-sm rounded-lg border">
                  Close
                </button>
                <button type="submit" className="px-4 py-2 text-sm rounded-lg bg-navy-900 text-white font-semibold">
                  Update Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
