import React, { useState } from "react";
import { Download, Printer, X, Award, ShieldCheck } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { downloadAuthorizedFile, resolveAssetUrl, API_BASE_URL } from "../api/client";

const ONES = [
  "ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE",
  "TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN",
  "SEVENTEEN", "EIGHTEEN", "NINETEEN",
];
const TENS = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"];

function intToWords(n) {
  const num = Math.max(0, Math.floor(Number(n) || 0));
  if (num < 20) return ONES[num];
  if (num < 100) return TENS[Math.floor(num / 10)] + (num % 10 ? ` ${ONES[num % 10]}` : "");
  if (num < 1000) return `${ONES[Math.floor(num / 100)]} HUNDRED${num % 100 ? ` ${intToWords(num % 100)}` : ""}`;
  return String(num);
}

function marksInWords(val) {
  const num = Number(val || 0);
  const whole = Math.floor(num);
  const dec = Math.round((num - whole) * 10);
  return dec > 0 ? `${intToWords(whole)} POINT ${ONES[dec]}` : intToWords(whole);
}

function getPucClassification(pct, anyFail) {
  if (anyFail || pct < 35) return "FAIL";
  if (pct >= 85) return "DISTINCTION";
  if (pct >= 60) return "FIRST CLASS";
  if (pct >= 50) return "SECOND CLASS";
  return "PASS CLASS";
}

export function PucMarksCardSheet({ result }) {
  if (!result) return null;
  const anyFail = (result.subjects || []).some(
    (s) => Number(s.marks_obtained) < (s.min_marks || Math.round(Number(s.max_marks) * 0.35))
  );
  const pucClass = getPucClassification(Number(result.percentage || 0), anyFail);
  const certId = result.certificate_id || `AKTP-DSIG-${result.student_code}-EX${result.examination_id}`;

  return (
    <div className="border-4 border-[#0A2463] p-1.5 rounded-sm bg-[#FFFDF7]">
      <div className="border-2 border-[#7C1D24] p-5 sm:p-8 bg-[#FFFDF7] relative overflow-hidden">
        {/* Header (Karnataka PUC Board Pattern) */}
        <div className="flex flex-col sm:flex-row items-center gap-4 pb-5 border-b-2 border-[#D4AF37]">
          <img
            src="/ak-tuition-logo.png"
            alt="AK Tuition Official Circular Logo"
            className="w-20 h-20 object-contain shrink-0"
          />
          <div className="flex-1 text-center sm:text-left">
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#7C1D24]">
              Department of Academic Examinations • PUC Board Pattern
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-wide text-[#0A2463]">
              AK TUITION
            </h2>
            <p className="text-xs font-semibold uppercase tracking-widest text-[#1E40AF]">
              Learn • Practise • Achieve  |  Director: {result.director_name || "G. Akash, B.E."}
            </p>
            <div className="mt-2 inline-block bg-[#0A2463] text-[#D4AF37] px-4 py-1 rounded text-xs font-bold tracking-wider uppercase">
              Provisional Statement of Marks
            </div>
          </div>
          <div className="text-center sm:text-right text-xs text-slate-700 space-y-0.5">
            <div className="font-bold text-[#0A2463] text-sm">{result.examination_name}</div>
            <div>Academic Year: {result.academic_year || "2026-2027"}</div>
            <div className="font-mono text-[11px] text-slate-500">Cert: {certId}</div>
            <span className="mt-1 inline-block px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">
              DIGITALLY VERIFIED
            </span>
          </div>
        </div>

        {/* Candidate Details */}
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white border border-[#0A2463]/40 rounded-lg p-4 text-sm">
          <div>
            <span className="font-semibold text-[#0A2463]">Candidate Name: </span>
            <span className="text-slate-900 font-bold uppercase">{result.student_name}</span>
          </div>
          <div>
            <span className="font-semibold text-[#0A2463]">Register No. (AK ID): </span>
            <span className="font-mono font-bold text-[#7C1D24]">{result.register_number || `${result.student_code}${result.section || ""}`}</span>
          </div>
          <div>
            <span className="font-semibold text-[#0A2463]">Class &amp; Batch: </span>
            <span>{result.class_name} — Section {result.section}</span>
          </div>
          <div>
            <span className="font-semibold text-[#0A2463]">Examination Date: </span>
            <span>{result.exam_date}</span>
          </div>
        </div>

        {/* PUC Subject Marks Table */}
        <div className="mt-6 overflow-x-auto">
          <table className="w-full border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="bg-[#0A2463] text-white">
                <th className="py-2 px-2 text-center border border-[#0A2463]">Sl.</th>
                <th className="py-2 px-3 text-left border border-[#0A2463]">Subject</th>
                <th className="py-2 px-2 text-center border border-[#0A2463]">Max</th>
                <th className="py-2 px-2 text-center border border-[#0A2463]">Min</th>
                <th className="py-2 px-2 text-center border border-[#0A2463]">Obtained</th>
                <th className="py-2 px-3 text-left border border-[#0A2463]">Marks in Words</th>
                <th className="py-2 px-2 text-center border border-[#0A2463]">Result</th>
                <th className="py-2 px-2 text-center border border-[#0A2463]">Grade</th>
              </tr>
            </thead>
            <tbody>
              {(result.subjects || []).map((sub, idx) => {
                const minM = sub.min_marks || Math.round(Number(sub.max_marks) * 0.35);
                const subRes = sub.subject_result || (Number(sub.marks_obtained) >= minM ? "PASS" : "FAIL");
                return (
                  <tr key={idx} className={idx % 2 === 1 ? "bg-blue-50/50" : "bg-white"}>
                    <td className="py-2 px-2 text-center border border-slate-300">{idx + 1}</td>
                    <td className="py-2 px-3 font-semibold text-slate-900 border border-slate-300">{sub.subject}</td>
                    <td className="py-2 px-2 text-center border border-slate-300">{sub.max_marks}</td>
                    <td className="py-2 px-2 text-center border border-slate-300 text-slate-500">{minM}</td>
                    <td className="py-2 px-2 text-center font-bold text-[#0A2463] border border-slate-300">{sub.marks_obtained}</td>
                    <td className="py-2 px-3 text-xs font-medium text-slate-700 border border-slate-300">
                      {sub.marks_in_words || marksInWords(sub.marks_obtained)}
                    </td>
                    <td className={`py-2 px-2 text-center font-bold border border-slate-300 ${subRes === "PASS" ? "text-emerald-700" : "text-red-700"}`}>
                      {subRes}
                    </td>
                    <td className="py-2 px-2 text-center font-bold text-[#1E40AF] border border-slate-300">{sub.grade}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Summary */}
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 gap-4 bg-[#FEF9E7] border-2 border-[#7C1D24]/60 rounded-lg p-4 text-sm">
          <div>
            <div className="text-xs text-slate-500 uppercase">Grand Total</div>
            <div className="text-base sm:text-lg font-bold text-[#0A2463]">
              {result.total_obtained} / {result.total_max}
            </div>
            <div className="text-[11px] font-semibold text-slate-600">
              ({result.total_in_words || marksInWords(result.total_obtained)})
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 uppercase">Percentage &amp; Class Rank</div>
            <div className="text-base sm:text-lg font-bold text-[#1E40AF]">
              {result.percentage}% {result.class_rank ? `• Rank #${result.class_rank}/${result.class_total_students}` : ""}
            </div>
            <div className="text-[11px] text-slate-600">Grade: {result.overall_grade}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 uppercase">PUC Result Classification</div>
            <div className={`text-base sm:text-lg font-extrabold ${pucClass !== "FAIL" ? "text-emerald-700" : "text-red-700"}`}>
              {pucClass}
            </div>
            <div className="text-[11px] text-slate-600">{result.teacher_remarks}</div>
          </div>
        </div>

        {/* Seal, QR Code & Digital Verification Signature by G. Akash, B.E. */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-6 pt-4">
          <div className="flex items-center gap-4">
            <div className="w-24 h-24 rounded-full border-2 border-[#0A2463] p-1 flex items-center justify-center">
              <div className="w-full h-full rounded-full border border-[#D4AF37] flex flex-col items-center justify-center text-center px-1">
                <span className="text-[9px] font-extrabold text-[#0A2463] leading-tight">AK TUITION</span>
                <span className="text-[8px] font-bold text-[#7C1D24] leading-tight mt-0.5">OFFICIAL SEAL</span>
                <span className="text-[7px] text-[#1E40AF] leading-tight mt-0.5">VERIFIED</span>
              </div>
            </div>
            <div className="text-xs text-slate-500">
              <div>Issued via AKTP PORTAL</div>
              <div>Karnataka Academic Pattern</div>
            </div>
          </div>

          {/* Scannable QR Verification Code */}
          <div className="flex flex-col items-center p-2.5 rounded-xl border border-[#D4AF37] bg-white shadow-sm">
            <QRCodeSVG
              value={`https://aktp-portal.netlify.app/results?code=${result.student_code}&exam=${result.examination_id}`}
              size={84}
              level="M"
              fgColor="#0A2463"
            />
            <span className="mt-1 text-[9px] font-bold tracking-wider uppercase text-[#0A2463]">
              Scan QR to Verify Result
            </span>
          </div>

          {/* Digital Signature & Verification Box */}
          <div className="text-center min-w-[235px] bg-emerald-50/80 border border-emerald-600 rounded-xl p-3">
            <div className="inline-flex items-center gap-1 text-[10px] font-extrabold text-emerald-800 uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5" /> Digitally Signed &amp; Verified
            </div>
            {result.director_signature_path ? (
              <img
                src={resolveAssetUrl(result.director_signature_path)}
                alt="Director Digital Signature"
                className="h-12 mx-auto object-contain my-1"
              />
            ) : (
              <div className="font-serif italic font-bold text-lg text-[#0A2463] my-1">
                {result.director_name || "G. Akash, B.E."}
              </div>
            )}
            <div className="border-t border-[#0A2463] pt-1">
              <div className="font-bold text-[#0A2463] text-xs">{result.director_name || "G. Akash, B.E."}</div>
              <div className="text-[11px] text-slate-600">{result.director_designation || "Director, AK Tuition"}</div>
              <div className="text-[9px] font-mono text-emerald-700 mt-0.5">Ref: {certId}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MarksCardModal({ result, pdfUrl, publicPdfToken, onClose }) {
  const [downloading, setDownloading] = useState(false);

  if (!result) return null;

  const handleDownload = async () => {
    if (publicPdfToken) {
      window.open(`${API_BASE_URL}/api/public/results/pdf?token=${encodeURIComponent(publicPdfToken)}`, "_blank");
      return;
    }
    if (!pdfUrl) return;
    setDownloading(true);
    try {
      await downloadAuthorizedFile(
        pdfUrl,
        `AK_PUC_MarksCard_${result.student_code}_Exam${result.examination_id}.pdf`
      );
    } catch (e) {
      alert(e.response?.data?.detail || "Unable to download marks card PDF.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full my-6 overflow-hidden">
        <div className="no-print flex flex-wrap items-center justify-between gap-3 px-6 py-4 bg-[#0A2463] text-white border-b border-[#D4AF37]">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-[#D4AF37]" />
            <span className="font-semibold">AK Tuition — Official PUC Pattern Marks Card</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm font-medium transition"
            >
              <Printer className="w-4 h-4" /> Print Marks Card
            </button>
            {(pdfUrl || publicPdfToken) && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#D4AF37] hover:bg-amber-400 text-[#0A2463] text-sm font-bold transition disabled:opacity-60"
              >
                <Download className="w-4 h-4" />
                {downloading ? "Generating PDF..." : "Download Signed PDF"}
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/10 text-slate-200"
              aria-label="Close marks card"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="p-5 sm:p-8 bg-white">
          <PucMarksCardSheet result={result} />
        </div>
      </div>
    </div>
  );
}
