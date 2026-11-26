import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { RefreshCw, Download, Printer, FileCheck2, ArrowLeft } from "lucide-react";
import api, { API_BASE_URL } from "../api/client";
import { PucMarksCardSheet } from "../components/MarksCardModal";

export default function ResultPortalPage() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState("register_no"); // register_no | otp
  const [registerNo, setRegisterNo] = useState(params.get("code") || "");
  const [phone, setPhone] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpSent, setOtpSent] = useState(false);

  const [captchaToken, setCaptchaToken] = useState("");
  const [captchaSvg, setCaptchaSvg] = useState("");
  const [captchaAnswer, setCaptchaAnswer] = useState("");

  const [availableExams, setAvailableExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState(params.get("exam") || "");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [infoMsg, setInfoMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const loadCaptcha = async () => {
    try {
      const res = await api.get("/api/public/result-captcha");
      setCaptchaToken(res.data.captcha_token);
      setCaptchaSvg(res.data.svg);
      setCaptchaAnswer("");
    } catch {
      setError("Could not load verification CAPTCHA.");
    }
  };

  useEffect(() => {
    loadCaptcha();
  }, []);

  const handleLookup = async (e, overrideExamId = null) => {
    if (e) e.preventDefault();
    setError("");
    setInfoMsg("");
    setLoading(true);
    try {
      const res = await api.post("/api/public/results/lookup", {
        mode,
        register_no: registerNo.trim(),
        phone: phone.trim(),
        otp_code: otpCode.trim(),
        examination_id: overrideExamId || (selectedExamId ? Number(selectedExamId) : null),
        captcha_token: captchaToken,
        captcha_answer: captchaAnswer.trim(),
      });
      setAvailableExams(res.data.available_examinations || []);
      setResult(res.data.result);
      setSelectedExamId(String(res.data.result.examination_id));
      loadCaptcha();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to fetch examination result. Verify Register No. & CAPTCHA.");
      loadCaptcha();
    } finally {
      setLoading(false);
    }
  };

  const handleSendOtp = async () => {
    setError("");
    setInfoMsg("");
    try {
      const res = await api.post("/api/public/results/request-otp", { phone: phone.trim() });
      setOtpSent(true);
      setInfoMsg(res.data.otp_preview ? `${res.data.message} OTP: ${res.data.otp_preview}` : res.data.message);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not generate OTP.");
    }
  };

  return (
    <div className="min-h-screen bg-[#f1f4f9] flex flex-col">
      {/* Official VTU-Style Top Header */}
      <div className="bg-[#7C1D24] text-amber-100 text-[11px] font-semibold py-1.5 px-4 text-center tracking-wide no-print">
        AK TUITION ACADEMIC EXAMINATION SYSTEM • KARNATAKA PUC BOARD MARKS CARD PORTAL • DIRECTOR: G. AKASH, B.E.
      </div>
      <header className="bg-[#0A2463] text-white shadow-md border-b-4 border-[#D4AF37] no-print">
        <div className="max-w-5xl mx-auto px-4 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-14 h-14 object-contain shrink-0" />
            <div>
              <h1 className="font-display font-extrabold text-xl sm:text-2xl tracking-wide">
                AK TUITION — PROVISIONAL RESULTS PORTAL
              </h1>
              <p className="text-xs text-blue-200 uppercase tracking-wider">
                Check Published Marks Cards via Register No. (e.g. AK001A) or Registered Mobile OTP + CAPTCHA
              </p>
            </div>
          </div>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-bold text-[#D4AF37] border border-[#D4AF37]/50"
          >
            <ArrowLeft className="w-4 h-4" /> Portal Login Home
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-6">
        {/* Lookup Card */}
        <div className="no-print bg-white rounded-xl shadow-md border-t-4 border-[#0A2463] p-6 sm:p-8 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
            <div className="flex items-center gap-2.5">
              <FileCheck2 className="w-6 h-6 text-[#7C1D24]" />
              <div>
                <h2 className="text-lg sm:text-xl font-bold text-[#0A2463]">
                  Examination Result Lookup (No Full Login Required)
                </h2>
                <p className="text-xs text-slate-500">
                  Instant access to digitally signed &amp; QR-verified PUC pattern Marks Cards.
                </p>
              </div>
            </div>
            <div className="inline-flex rounded-lg border p-1 bg-slate-50 text-xs font-bold">
              <button
                type="button"
                onClick={() => { setMode("register_no"); setError(""); }}
                className={`px-3 py-1.5 rounded-md ${mode === "register_no" ? "bg-[#0A2463] text-white" : "text-slate-600"}`}
              >
                Register No. + Captcha
              </button>
              <button
                type="button"
                onClick={() => { setMode("otp"); setError(""); }}
                className={`px-3 py-1.5 rounded-md ${mode === "otp" ? "bg-[#0A2463] text-white" : "text-slate-600"}`}
              >
                Mobile OTP + Captcha
              </button>
            </div>
          </div>

          {error && <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 font-semibold">{error}</div>}
          {infoMsg && <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-semibold">{infoMsg}</div>}

          <form onSubmit={(e) => handleLookup(e)} className="grid sm:grid-cols-12 gap-4 items-end">
            {mode === "register_no" ? (
              <div className="sm:col-span-5">
                <label className="block text-xs font-bold text-slate-700 mb-1.5 uppercase">
                  Enter Register No. / AK ID *
                </label>
                <input
                  required
                  value={registerNo}
                  onChange={(e) => setRegisterNo(e.target.value)}
                  placeholder="e.g. AK001 or AK001A"
                  className="w-full rounded-lg border-2 border-slate-300 px-3.5 py-2.5 text-sm font-mono uppercase focus:border-[#0A2463] outline-none"
                />
              </div>
            ) : (
              <>
                <div className="sm:col-span-3">
                  <label className="block text-xs font-bold text-slate-700 mb-1.5 uppercase">
                    Registered Mobile *
                  </label>
                  <div className="flex gap-1.5">
                    <input
                      required
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="10-digit number"
                      className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-sm focus:border-[#0A2463] outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      className="px-3 py-2 rounded-lg bg-[#7C1D24] text-white text-xs font-bold shrink-0"
                    >
                      {otpSent ? "Resend" : "OTP"}
                    </button>
                  </div>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1.5 uppercase">Enter OTP *</label>
                  <input
                    required
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    placeholder="6-digit OTP"
                    className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-sm font-mono focus:border-[#0A2463] outline-none"
                  />
                </div>
              </>
            )}

            <div className="sm:col-span-5 flex flex-wrap items-end gap-2">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 uppercase">Captcha Code</label>
                <div className="flex items-center gap-1.5">
                  <div
                    className="border rounded-lg overflow-hidden bg-blue-50"
                    dangerouslySetInnerHTML={{ __html: captchaSvg }}
                  />
                  <button
                    type="button"
                    onClick={loadCaptcha}
                    className="p-2 rounded-lg border bg-slate-50 hover:bg-slate-100 text-slate-700"
                    title="Refresh CAPTCHA"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="flex-1 min-w-[110px]">
                <label className="block text-xs font-bold text-slate-700 mb-1 uppercase">Type Captcha *</label>
                <input
                  required
                  value={captchaAnswer}
                  onChange={(e) => setCaptchaAnswer(e.target.value.toUpperCase())}
                  placeholder="Enter code"
                  className="w-full rounded-lg border-2 border-slate-300 px-3 py-2.5 text-sm font-mono uppercase focus:border-[#0A2463] outline-none"
                />
              </div>
            </div>

            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-lg bg-[#0A2463] hover:bg-[#1E40AF] text-white font-bold text-sm shadow transition disabled:opacity-60"
              >
                {loading ? "Checking..." : "SUBMIT"}
              </button>
            </div>
          </form>
        </div>

        {/* Displayed PUC Marks Card */}
        {result && (
          <div className="bg-white rounded-xl shadow-lg border p-5 sm:p-8 space-y-4">
            <div className="no-print flex flex-wrap items-center justify-between gap-3 border-b pb-4">
              {availableExams.length > 1 ? (
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-bold text-[#0A2463]">Examination:</span>
                  <select
                    value={selectedExamId}
                    onChange={(e) => {
                      setSelectedExamId(e.target.value);
                    }}
                    className="rounded-lg border px-3 py-1.5 font-semibold"
                  >
                    {availableExams.map((ex) => (
                      <option key={ex.id} value={ex.id}>{ex.name}</option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="text-sm font-bold text-emerald-800">
                  Official Result Ready — Signed &amp; Verified by {result.director_name}
                </div>
              )}

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-slate-300 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  <Printer className="w-4 h-4" /> Print Result
                </button>
                <a
                  href={`${API_BASE_URL}/api/public/results/pdf?token=${encodeURIComponent(result.download_token)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#0A2463] text-white text-xs font-bold shadow"
                >
                  <Download className="w-4 h-4 text-[#D4AF37]" /> Download Signed PUC PDF
                </a>
              </div>
            </div>

            <PucMarksCardSheet result={result} />
          </div>
        )}
      </main>
    </div>
  );
}
