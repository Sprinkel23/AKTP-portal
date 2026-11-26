import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle } from "lucide-react";
import api from "../api/client";
import { PucMarksCardSheet } from "../components/MarksCardModal";

export default function VerifyMarksPage() {
  const [params] = useSearchParams();
  const code = params.get("code") || "";
  const exam = params.get("exam") || "";
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code) {
      setError("Missing Student ID in QR verification link.");
      setLoading(false);
      return;
    }
    const qs = new URLSearchParams({ code });
    if (exam) qs.set("exam", exam);
    api
      .get(`/api/public/verify-markscard?${qs.toString()}`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Unable to verify marks card."))
      .finally(() => setLoading(false));
  }, [code, exam]);

  return (
    <div className="min-h-screen bg-[#eef2f7] flex flex-col">
      <header className="bg-[#0A2463] text-white py-4 px-4 shadow border-b-4 border-[#D4AF37]">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-11 h-11 object-contain" />
            <div>
              <div className="font-bold text-lg">AK TUITION</div>
              <div className="text-xs text-blue-200 uppercase tracking-wider">QR Marks Card Verification</div>
            </div>
          </div>
          <div className="flex gap-3">
            <Link to="/results" className="text-xs font-bold text-[#D4AF37] hover:underline">
              Results Portal
            </Link>
            <Link to="/" className="text-xs font-semibold text-white hover:underline">
              Portal Home
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8">
        {loading ? (
          <div className="bg-white rounded-xl p-8 text-center shadow-sm border text-slate-600">
            Verifying AK Tuition Marks Card...
          </div>
        ) : error ? (
          <div className="bg-white rounded-xl p-8 text-center shadow-sm border border-red-200 space-y-3">
            <XCircle className="w-12 h-12 text-red-600 mx-auto" />
            <h2 className="text-xl font-bold text-slate-900">Verification Failed</h2>
            <p className="text-sm text-red-600">{error}</p>
            <Link to="/results" className="inline-block mt-2 px-5 py-2 rounded-lg bg-[#0A2463] text-white text-sm font-semibold">
              Go to Results Portal
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-300 rounded-xl p-4 shadow-sm">
              <CheckCircle2 className="w-7 h-7 text-emerald-600 shrink-0" />
              <div>
                <div className="font-extrabold text-emerald-900 text-sm">QR VERIFIED OFFICIAL MARKS CARD</div>
                <div className="text-xs text-emerald-700">
                  {data.tuition_name} • Digitally Verified by {data.director_name}
                </div>
              </div>
            </div>
            <PucMarksCardSheet result={data} />
          </div>
        )}
      </main>
    </div>
  );
}
