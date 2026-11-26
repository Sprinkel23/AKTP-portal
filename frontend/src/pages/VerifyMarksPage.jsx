import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle, Award } from "lucide-react";
import api from "../api/client";

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
    <div className="min-h-screen bg-[#f2f5fa] flex flex-col">
      <header className="bg-[#0b1366] text-white py-4 px-4 shadow">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-11 h-11 object-contain" />
            <div>
              <div className="font-bold text-lg">AK TUITION</div>
              <div className="text-xs text-blue-200 uppercase tracking-wider">Official Marks Card Verification</div>
            </div>
          </div>
          <Link to="/" className="text-xs font-semibold text-gold-400 hover:text-white underline">
            Portal Login
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8">
        {loading ? (
          <div className="bg-white rounded-2xl p-8 text-center shadow-sm border text-slate-600">
            Verifying AK Tuition Marks Card...
          </div>
        ) : error ? (
          <div className="bg-white rounded-2xl p-8 text-center shadow-sm border border-red-200 space-y-3">
            <XCircle className="w-12 h-12 text-red-600 mx-auto" />
            <h2 className="text-xl font-bold text-slate-900">Verification Failed</h2>
            <p className="text-sm text-red-600">{error}</p>
            <Link to="/" className="inline-block mt-2 px-5 py-2 rounded-lg bg-[#0b1366] text-white text-sm font-semibold">
              Go to AKTP Portal
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border-2 border-navy-900 space-y-5">
            <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 shrink-0" />
              <div>
                <div className="font-extrabold text-emerald-900">OFFICIALLY VERIFIED MARKS CARD</div>
                <div className="text-xs text-emerald-700">
                  {data.tuition_name} • Authorized by {data.director_name}
                </div>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 bg-blue-50/70 rounded-xl p-4 text-sm">
              <div><strong>Student Name:</strong> {data.student_name}</div>
              <div><strong>Student ID:</strong> <span className="font-mono font-bold text-royal-700">{data.student_code}</span></div>
              <div><strong>Class:</strong> {data.class_name} ({data.section})</div>
              <div><strong>Examination:</strong> {data.examination_name}</div>
            </div>

            <table className="w-full text-sm border">
              <thead className="bg-navy-900 text-white text-xs uppercase">
                <tr>
                  <th className="p-2.5 text-left">Subject</th>
                  <th className="p-2.5 text-center">Obtained / Max</th>
                  <th className="p-2.5 text-center">Grade</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.subjects.map((s, idx) => (
                  <tr key={idx}>
                    <td className="p-2.5 font-medium">{s.subject}</td>
                    <td className="p-2.5 text-center font-bold">{s.marks_obtained} / {s.max_marks}</td>
                    <td className="p-2.5 text-center font-bold text-royal-700">{s.grade}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-amber-50 border border-gold-500 rounded-xl p-4 text-center text-sm">
              <div><div className="text-xs text-slate-500">Total</div><div className="font-bold text-navy-900">{data.total_obtained}/{data.total_max}</div></div>
              <div><div className="text-xs text-slate-500">Percentage</div><div className="font-bold text-royal-700">{data.percentage}%</div></div>
              <div><div className="text-xs text-slate-500">Class Rank</div><div className="font-bold text-navy-900">{data.class_rank ? `#${data.class_rank}/${data.class_total_students}` : "-"}</div></div>
              <div><div className="text-xs text-slate-500">Status</div><div className="font-extrabold text-emerald-700 inline-flex items-center gap-1"><Award className="w-4 h-4" />{data.result_status}</div></div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
