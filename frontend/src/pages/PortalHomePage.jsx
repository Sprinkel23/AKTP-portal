import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const TABS = [
  { id: "student", label: "Student Portal" },
  { id: "parent", label: "Parent Portal" },
  { id: "teacher", label: "Teacher Portal" },
  { id: "admin", label: "Admin Portal" },
];

export default function PortalHomePage() {
  const { role } = useParams();
  const navigate = useNavigate();
  const { user, loginSuccess } = useAuth();

  const initialTab = TABS.some((t) => t.id === role?.toLowerCase()) ? role.toLowerCase() : "student";
  const [activeTab, setActiveTab] = useState(initialTab);

  const [studentId, setStudentId] = useState("");
  const [studentPassword, setStudentPassword] = useState("");
  const [studentMode, setStudentMode] = useState("login"); // login | signup
  const [publicClasses, setPublicClasses] = useState([]);
  const [signupForm, setSignupForm] = useState({
    student_name: "",
    class_id: "",
    student_phone: "",
    parent_name: "",
    parent_phone: "",
  });
  const [signupCreds, setSignupCreds] = useState(null);

  const [parentPhoneOrUser, setParentPhoneOrUser] = useState("");

  const [teacherUser, setTeacherUser] = useState("");
  const [teacherKey, setTeacherKey] = useState("");
  const [showTeacherKey, setShowTeacherKey] = useState(false);
  const [teacherAuthMode, setTeacherAuthMode] = useState("password"); // password | otp
  const [teacherPhone, setTeacherPhone] = useState("");
  const [teacherOtp, setTeacherOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);

  const [adminUser, setAdminUser] = useState("");
  const [adminPassword, setAdminPassword] = useState("");

  const [error, setError] = useState("");
  const [infoMsg, setInfoMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [resetMode, setResetMode] = useState(null); // null | "forgot" | "reset"
  const [resetIdent, setResetIdent] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (role && TABS.some((t) => t.id === role.toLowerCase())) {
      setActiveTab(role.toLowerCase());
    }
  }, [role]);

  useEffect(() => {
    api
      .get("/api/public/classes")
      .then((res) => {
        const list = res.data || [];
        setPublicClasses(list);
        if (list.length) {
          setSignupForm((prev) => (prev.class_id ? prev : { ...prev, class_id: String(list[0].id) }));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (user?.role) {
      navigate(`/${user.role}`, { replace: true });
    }
  }, [user, navigate]);

  const formatAuthError = (err, fallback) => {
    if (!err?.response) {
      return "Cannot reach the AKTP backend server. Ensure FastAPI (uvicorn) and PostgreSQL are running.";
    }
    if (err.response.status >= 500) {
      return "Backend server error or proxy unreachable. Ensure FastAPI and PostgreSQL are running.";
    }
    return err.response?.data?.detail || fallback;
  };

  const doLogin = async (identifier, password, portalRole) => {
    setError("");
    setInfoMsg("");
    setSubmitting(true);
    try {
      const res = await api.post("/api/auth/login", {
        identifier: identifier.trim(),
        password,
        portal_role: portalRole,
      });
      if (!res.data?.access_token || !res.data?.user?.role) {
        setError("Backend API is not connected yet. Set VITE_API_BASE_URL to your live FastAPI URL (or run uvicorn locally).");
        return;
      }
      loginSuccess(res.data.access_token, res.data.user);
      navigate(`/${res.data.user.role}`, { replace: true });
    } catch (err) {
      setError(formatAuthError(err, "Invalid credentials. Please verify and try again."));
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgot = async (e) => {
    e.preventDefault();
    setError("");
    setInfoMsg("");
    try {
      const res = await api.post("/api/auth/forgot-password", { identifier: resetIdent });
      setResetToken(res.data.reset_token);
      setInfoMsg(`${res.data.message} Token: ${res.data.reset_token}`);
      setResetMode("reset");
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
      setResetMode(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not reset password.");
    }
  };

  return (
    <div className="min-h-screen bg-[#f4f7fb] flex flex-col">
      {/* JAMS-Inspired Clean Institutional Masthead */}
      <header className="bg-white border-b-4 border-[#0A2463] shadow-sm">
        <div className="bg-[#0A2463] text-white text-[11px] font-semibold py-1.5 px-4">
          <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-2">
            <span>AK TUITION (AKTP) • OFFICIAL ACADEMIC &amp; EXAMINATION PORTAL</span>
            <span className="text-[#D4AF37]">Director: G. Akash, B.E.</span>
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <img
              src="/ak-tuition-logo.png"
              alt="AK Tuition Logo"
              className="w-12 h-12 sm:w-14 sm:h-14 object-contain shrink-0"
            />
            <div>
              <h1 className="font-display font-extrabold text-xl sm:text-2xl text-[#0A2463] tracking-wide leading-tight">
                AK TUITION — AKTP PORTAL
              </h1>
              <p className="text-[11px] sm:text-xs tracking-wider uppercase text-slate-600 font-semibold">
                Learn • Practise • Achieve | Student, Parent, Teacher &amp; Admin System
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <Link
              to="/results"
              className="px-4 py-2 rounded-lg bg-[#0A2463] hover:bg-[#1E40AF] text-white text-xs font-extrabold tracking-wide shadow transition"
            >
              Exam Results (Captcha)
            </Link>
            <Link
              to="/website"
              className="px-3.5 py-2 rounded-lg border border-slate-300 hover:bg-slate-50 text-xs font-semibold text-[#0A2463] transition"
            >
              About Tuition
            </Link>
          </div>
        </div>
      </header>

      {/* Official Result Announcement Bar */}
      <div className="bg-amber-50 border-b border-amber-200 py-2 px-4">
        <div className="max-w-4xl mx-auto flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-[#7C1D24] font-semibold">
            <span className="px-2 py-0.5 rounded bg-[#7C1D24] text-white text-[10px] font-extrabold uppercase">NOTICE</span>
            <span>Check Declared Examination Results via AK Register No. (e.g. AK001A) or Mobile OTP + Captcha.</span>
          </div>
          <Link to="/results" className="font-extrabold text-[#0A2463] underline hover:text-[#7C1D24] shrink-0">
            Open Shareable Results Link →
          </Link>
        </div>
      </div>

      {/* Main Centered Container */}
      <main className="flex-1 flex flex-col items-center justify-start pt-6 sm:pt-8 pb-12 px-4">
        <div className="w-full max-w-4xl">
          {/* Direct Shareable Result Card */}
          <div className="mb-5 bg-white rounded-xl border border-slate-200 border-l-4 border-l-[#0A2463] shadow-sm p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-[#1E40AF]">
                Shareable Results Portal
              </div>
              <div className="text-sm font-bold text-[#0A2463]">
                View &amp; Download Digitally Signed Statement of Marks Without Full Login
              </div>
            </div>
            <Link
              to="/results"
              className="px-4 py-2 rounded-lg bg-[#0A2463] hover:bg-[#1E40AF] text-white text-xs font-bold shadow transition"
            >
              Check Result with AK ID / OTP + Captcha →
            </Link>
          </div>

          {/* Portal Switcher Tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {TABS.map((t) => {
              const active = activeTab === t.id && !resetMode;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    setActiveTab(t.id);
                    setResetMode(null);
                    setError("");
                    setInfoMsg("");
                  }}
                  className={`px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold border transition ${
                    active
                      ? "bg-[#0A2463] text-white border-[#0A2463] shadow-sm"
                      : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  {t.label}
                </button>
              );
            })}
          </div>

          {/* JAMS-Style Login Card */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 border-t-4 border-t-[#0A2463] p-6 sm:p-9">
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
                {error}
              </div>
            )}
            {infoMsg && (
              <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium break-all">
                {infoMsg}
              </div>
            )}

            {/* FORGOT / RESET PASSWORD */}
            {resetMode === "forgot" && (
              <form onSubmit={handleForgot} className="space-y-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Reset Portal Password</h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Enter your registered Student ID, Username, or Email to generate a reset token.
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Student ID, Username, or Email
                  </label>
                  <input
                    required
                    value={resetIdent}
                    onChange={(e) => setResetIdent(e.target.value)}
                    placeholder="Enter Student ID, username, or email"
                    className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366]"
                  />
                </div>
                <div className="flex gap-3">
                  <button type="submit" className="px-6 py-2.5 rounded-lg bg-[#0b1366] text-white text-sm font-semibold">
                    Generate Reset Token
                  </button>
                  <button type="button" onClick={() => setResetMode(null)} className="px-4 py-2.5 rounded-lg border text-sm">
                    Back to Sign In
                  </button>
                </div>
              </form>
            )}

            {resetMode === "reset" && (
              <form onSubmit={handleReset} className="space-y-4">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">Set New Password</h2>
                  <p className="text-xs text-slate-500 mt-1">Enter your reset token and choose a new password.</p>
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">Reset Token</label>
                    <input
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">New Password (min 6 chars)</label>
                    <input
                      type="password"
                      required
                      minLength={6}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm"
                    />
                  </div>
                </div>
                <div className="flex gap-3">
                  <button type="submit" className="px-6 py-2.5 rounded-lg bg-[#0b1366] text-white text-sm font-semibold">
                    Update Password
                  </button>
                  <button type="button" onClick={() => setResetMode(null)} className="px-4 py-2.5 rounded-lg border text-sm">
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {/* 1. STUDENT PORTAL TAB */}
            {!resetMode && activeTab === "student" && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">
                      {studentMode === "login" ? "Student Login" : "Student Quick Sign Up"}
                    </h2>
                    <p className="text-xs sm:text-sm text-slate-500 mt-1">
                      {studentMode === "login"
                        ? "Enter your Student ID and password to view marks cards, QR verification, attendance, and quizzes."
                        : "Sign up with your name, class, and mobile number — your Student ID and unique login password will be created automatically."}
                    </p>
                  </div>
                  <div className="inline-flex rounded-lg border border-slate-200 p-1 bg-slate-50 text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => {
                        setStudentMode("login");
                        setError("");
                        setInfoMsg("");
                      }}
                      className={`px-3 py-1.5 rounded-md transition ${
                        studentMode === "login" ? "bg-[#0b1366] text-white" : "text-slate-600"
                      }`}
                    >
                      Student Login
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setStudentMode("signup");
                        setError("");
                        setInfoMsg("");
                      }}
                      className={`px-3 py-1.5 rounded-md transition ${
                        studentMode === "signup" ? "bg-[#0b1366] text-white" : "text-slate-600"
                      }`}
                    >
                      New Student Sign Up
                    </button>
                  </div>
                </div>

                {signupCreds && (
                  <div className="p-5 rounded-xl bg-emerald-50 border-2 border-emerald-500 space-y-3">
                    <div className="font-bold text-emerald-900 text-sm">
                      Automatic Student Login Credentials Created!
                    </div>
                    <div className="grid sm:grid-cols-2 gap-2 text-xs text-slate-800">
                      <div>Student Name: <strong>{signupCreds.creds.student_name}</strong></div>
                      <div>Class: <strong>{signupCreds.creds.class_name}</strong></div>
                      <div>Student ID / Username: <strong className="font-mono text-sm text-[#0b1366]">{signupCreds.creds.student_username}</strong></div>
                      <div>Auto Password: <strong className="font-mono text-sm text-emerald-700">{signupCreds.creds.student_password}</strong></div>
                      <div>Registered Mobile: <strong className="font-mono">{signupCreds.creds.student_phone}</strong></div>
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          const txt = `AK TUITION STUDENT LOGIN\nName: ${signupCreds.creds.student_name}\nClass: ${signupCreds.creds.class_name}\nStudent ID: ${signupCreds.creds.student_username}\nPassword: ${signupCreds.creds.student_password}\nPortal: https://aktp-portal.netlify.app`;
                          navigator.clipboard?.writeText(txt);
                          setInfoMsg("Credentials copied! Save them before entering the portal.");
                        }}
                        className="px-4 py-2 rounded-lg border border-emerald-700 text-emerald-900 text-xs font-bold bg-white"
                      >
                        Copy Login Details
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          loginSuccess(signupCreds.access_token, signupCreds.user);
                          navigate(`/${signupCreds.user.role}`, { replace: true });
                        }}
                        className="px-5 py-2 rounded-lg bg-[#0b1366] text-white text-xs font-bold"
                      >
                        Continue to Student Portal →
                      </button>
                    </div>
                  </div>
                )}

                {studentMode === "login" ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      doLogin(studentId, studentPassword, "student");
                    }}
                    className="space-y-5"
                  >
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Student ID / Roll Number
                        </label>
                        <input
                          required
                          value={studentId}
                          onChange={(e) => setStudentId(e.target.value)}
                          placeholder="Enter Student ID (e.g. AK001)"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Password
                        </label>
                        <input
                          type="password"
                          required
                          value={studentPassword}
                          onChange={(e) => setStudentPassword(e.target.value)}
                          placeholder="Enter your password"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-3 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition disabled:opacity-60"
                    >
                      {submitting ? "Signing in..." : "Login to Student Portal"}
                    </button>

                    <div className="flex justify-between items-center text-xs text-slate-500">
                      <button type="button" onClick={() => setResetMode("forgot")} className="text-[#0b1366] hover:underline font-medium">
                        Forgot Password?
                      </button>
                      <Link to="/website" className="sm:hidden text-[#0b1366] hover:underline font-medium">
                        About AK Tuition
                      </Link>
                    </div>
                  </form>
                ) : (
                  <form
                    onSubmit={async (e) => {
                      e.preventDefault();
                      setError("");
                      setInfoMsg("");
                      setSubmitting(true);
                      try {
                        const res = await api.post("/api/auth/student/signup", {
                          student_name: signupForm.student_name.trim(),
                          class_id: Number(signupForm.class_id),
                          student_phone: signupForm.student_phone.trim(),
                          parent_name: signupForm.parent_name.trim() || null,
                          parent_phone: signupForm.parent_phone.trim() || null,
                        });
                        setSignupCreds({
                          access_token: res.data.access_token,
                          user: res.data.user,
                          creds: res.data.generated_credentials,
                        });
                      } catch (err) {
                        setError(formatAuthError(err, "Unable to complete sign up."));
                      } finally {
                        setSubmitting(false);
                      }
                    }}
                    className="space-y-4"
                  >
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Student Full Name *
                        </label>
                        <input
                          required
                          value={signupForm.student_name}
                          onChange={(e) => setSignupForm({ ...signupForm, student_name: e.target.value })}
                          placeholder="Enter your full name"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Select Class *
                        </label>
                        <select
                          required
                          value={signupForm.class_id}
                          onChange={(e) => setSignupForm({ ...signupForm, class_id: e.target.value })}
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366]"
                        >
                          <option value="">Choose Class</option>
                          {publicClasses.map((c) => (
                            <option key={c.id} value={c.id}>{c.name} ({c.section})</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Your Mobile Number *
                        </label>
                        <input
                          required
                          value={signupForm.student_phone}
                          onChange={(e) => setSignupForm({ ...signupForm, student_phone: e.target.value })}
                          placeholder="Enter 10-digit mobile number"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Parent Phone Number (optional)
                        </label>
                        <input
                          value={signupForm.parent_phone}
                          onChange={(e) => setSignupForm({ ...signupForm, parent_phone: e.target.value })}
                          placeholder="Same as your number if blank"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366]"
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-3 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition disabled:opacity-60"
                    >
                      {submitting ? "Creating Student ID..." : "Sign Up & Generate Login Credentials"}
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* 2. PARENT / GUARDIAN PORTAL TAB */}
            {!resetMode && activeTab === "parent" && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  setError("");
                  setInfoMsg("");
                  setSubmitting(true);
                  try {
                    const res = await api.post("/api/auth/parent/phone-login", {
                      phone: parentPhoneOrUser.trim(),
                    });
                    if (!res.data?.access_token || !res.data?.user?.role) {
                      setError("Backend API is not connected yet. Set VITE_API_BASE_URL to your live FastAPI URL.");
                      return;
                    }
                    loginSuccess(res.data.access_token, res.data.user);
                    navigate(`/${res.data.user.role}`, { replace: true });
                  } catch (err) {
                    setError(formatAuthError(err, "Registered phone number not found."));
                  } finally {
                    setSubmitting(false);
                  }
                }}
                className="space-y-5"
              >
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Parent / Guardian Portal</h2>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    Enter the parent phone number registered by your teacher. This shows the linked child&apos;s academic progress.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Registered parent phone number
                  </label>
                  <div className="grid sm:grid-cols-12 gap-3">
                    <input
                      required
                      value={parentPhoneOrUser}
                      onChange={(e) => setParentPhoneOrUser(e.target.value)}
                      placeholder="Enter phone number"
                      className="sm:col-span-6 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                    />
                    <button
                      type="submit"
                      disabled={submitting}
                      className="sm:col-span-6 py-2.5 px-4 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition disabled:opacity-60"
                    >
                      {submitting ? "Loading..." : "View Child Progress"}
                    </button>
                  </div>
                </div>
              </form>
            )}

            {/* 3. TEACHER PORTAL TAB */}
            {!resetMode && activeTab === "teacher" && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Teacher Portal</h2>
                    <p className="text-xs sm:text-sm text-slate-500 mt-1">
                      Manage student profiles, marks, daily attendance, question papers and quiz evaluation.
                    </p>
                  </div>
                  <div className="inline-flex rounded-lg border border-slate-200 p-1 bg-slate-50 text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => {
                        setTeacherAuthMode("password");
                        setError("");
                        setInfoMsg("");
                      }}
                      className={`px-3 py-1.5 rounded-md transition ${
                        teacherAuthMode === "password" ? "bg-[#0b1366] text-white" : "text-slate-600"
                      }`}
                    >
                      Access Key
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setTeacherAuthMode("otp");
                        setError("");
                        setInfoMsg("");
                      }}
                      className={`px-3 py-1.5 rounded-md transition ${
                        teacherAuthMode === "otp" ? "bg-[#0b1366] text-white" : "text-slate-600"
                      }`}
                    >
                      Mobile + OTP
                    </button>
                  </div>
                </div>

                {teacherAuthMode === "password" ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      doLogin(teacherUser, teacherKey, "teacher");
                    }}
                    className="space-y-4"
                  >
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Teacher username
                        </label>
                        <input
                          required
                          value={teacherUser}
                          onChange={(e) => setTeacherUser(e.target.value)}
                          placeholder="Enter teacher username"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Teacher access key / password
                        </label>
                        <div className="grid sm:grid-cols-12 gap-3">
                          <input
                            type={showTeacherKey ? "text" : "password"}
                            required
                            value={teacherKey}
                            onChange={(e) => setTeacherKey(e.target.value)}
                            placeholder="Enter teacher access key"
                            className="sm:col-span-7 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                          />
                          <button
                            type="button"
                            onClick={() => setShowTeacherKey((v) => !v)}
                            className="sm:col-span-5 py-2.5 px-4 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition"
                          >
                            {showTeacherKey ? "Hide key" : "Show key"}
                          </button>
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-3 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition disabled:opacity-60"
                    >
                      {submitting ? "Signing in..." : "Sign in"}
                    </button>

                    <div className="text-xs">
                      <button type="button" onClick={() => setResetMode("forgot")} className="text-[#0b1366] hover:underline font-medium">
                        Forgot Password?
                      </button>
                    </div>
                  </form>
                ) : (
                  <form
                    onSubmit={async (e) => {
                      e.preventDefault();
                      setError("");
                      setInfoMsg("");
                      if (!otpSent) {
                        setSubmitting(true);
                        try {
                          const res = await api.post("/api/auth/teacher/request-otp", { phone: teacherPhone });
                          setOtpSent(true);
                          setInfoMsg(
                            res.data.demo_otp
                              ? `${res.data.message} OTP: ${res.data.demo_otp}`
                              : res.data.message
                          );
                        } catch (err) {
                          setError(err.response?.data?.detail || "Could not send OTP.");
                        } finally {
                          setSubmitting(false);
                        }
                      } else {
                        setSubmitting(true);
                        try {
                          const res = await api.post("/api/auth/teacher/verify-otp", {
                            phone: teacherPhone,
                            otp_code: teacherOtp,
                          });
                          loginSuccess(res.data.access_token, res.data.user);
                          navigate(`/${res.data.user.role}`, { replace: true });
                        } catch (err) {
                          setError(err.response?.data?.detail || "Invalid or expired OTP.");
                        } finally {
                          setSubmitting(false);
                        }
                      }
                    }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                        Registered Teacher Mobile Number
                      </label>
                      <div className="grid sm:grid-cols-12 gap-3">
                        <input
                          required
                          value={teacherPhone}
                          onChange={(e) => setTeacherPhone(e.target.value)}
                          placeholder="Enter registered 10-digit mobile number"
                          className="sm:col-span-8 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366]"
                        />
                        <button
                          type="button"
                          onClick={async () => {
                            setError("");
                            setInfoMsg("");
                            try {
                              const res = await api.post("/api/auth/teacher/request-otp", { phone: teacherPhone });
                              setOtpSent(true);
                              setInfoMsg(
                                res.data.demo_otp
                                  ? `${res.data.message} OTP: ${res.data.demo_otp}`
                                  : res.data.message
                              );
                            } catch (err) {
                              setError(err.response?.data?.detail || "Could not send OTP.");
                            }
                          }}
                          className="sm:col-span-4 py-2.5 px-4 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition"
                        >
                          {otpSent ? "Resend OTP" : "Get OTP"}
                        </button>
                      </div>
                    </div>

                    {otpSent && (
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                          Enter 6-Digit OTP
                        </label>
                        <input
                          required
                          value={teacherOtp}
                          onChange={(e) => setTeacherOtp(e.target.value)}
                          placeholder="Enter OTP code"
                          className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm font-mono tracking-widest outline-none focus:border-[#0b1366]"
                        />
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={submitting}
                      className="w-full py-3 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition disabled:opacity-60"
                    >
                      {submitting ? "Verifying..." : otpSent ? "Verify OTP & Sign in" : "Send OTP"}
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* 4. ADMIN PORTAL TAB */}
            {!resetMode && activeTab === "admin" && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  doLogin(adminUser, adminPassword, "admin");
                }}
                className="space-y-5"
              >
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Administrator Portal</h2>
                  <p className="text-xs sm:text-sm text-slate-500 mt-1">
                    Full system control: student admissions, teachers, exam timetables, official result approvals and academic reports.
                  </p>
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                      Administrator Username
                    </label>
                    <input
                      required
                      value={adminUser}
                      onChange={(e) => setAdminUser(e.target.value)}
                      placeholder="Enter admin username"
                      className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                      Password
                    </label>
                    <input
                      type="password"
                      required
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      placeholder="Enter admin password"
                      className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-[#0b1366] focus:ring-2 focus:ring-[#0b1366]/10"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full py-3 rounded-lg bg-[#0b1366] hover:bg-[#14208c] text-white font-semibold text-sm transition disabled:opacity-60"
                >
                  {submitting ? "Signing in..." : "Sign in to Administrator Portal"}
                </button>
              </form>
            )}
          </div>

          {/* Footer Note */}
          <p className="text-center text-xs text-slate-500 mt-6">
            AK Tuition • Academic progress portal • Keep student and parent details private.
          </p>
        </div>
      </main>
    </div>
  );
}
