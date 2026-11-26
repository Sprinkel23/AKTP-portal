import React, { useState } from "react";
import { Download, Printer, X, Award } from "lucide-react";
import { downloadAuthorizedFile, resolveAssetUrl } from "../api/client";

export default function MarksCardModal({ result, pdfUrl, onClose }) {
  const [downloading, setDownloading] = useState(false);

  if (!result) return null;

  const handleDownload = async () => {
    if (!pdfUrl) return;
    setDownloading(true);
    try {
      await downloadAuthorizedFile(
        pdfUrl,
        `AK_MarksCard_${result.student_code}_Exam${result.examination_id}.pdf`
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
        {/* Toolbar */}
        <div className="no-print flex flex-wrap items-center justify-between gap-3 px-6 py-4 bg-navy-900 text-white border-b border-gold-500">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-gold-400" />
            <span className="font-semibold">Official AK Tuition Marks Card</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm font-medium transition"
            >
              <Printer className="w-4 h-4" /> Print Marks Card
            </button>
            {pdfUrl && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950 text-sm font-bold transition disabled:opacity-60"
              >
                <Download className="w-4 h-4" />
                {downloading ? "Generating PDF..." : "Download PDF"}
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

        {/* Certificate Sheet */}
        <div className="p-5 sm:p-8 bg-white">
          <div className="border-4 border-navy-900 p-1.5 rounded-sm">
            <div className="border-2 border-gold-500 p-5 sm:p-8 bg-white">
              {/* Header */}
              <div className="flex flex-col sm:flex-row items-center gap-4 pb-5 border-b-2 border-gold-500">
                <img
                  src="/ak-tuition-logo.png"
                  alt="AK Tuition Official Circular Logo"
                  className="w-20 h-20 object-contain shrink-0"
                />
                <div className="flex-1 text-center sm:text-left">
                  <h2 className="text-2xl sm:text-3xl font-extrabold tracking-wide text-navy-900">
                    AK TUITION
                  </h2>
                  <p className="text-xs font-semibold uppercase tracking-widest text-royal-600">
                    Learn • Practise • Achieve
                  </p>
                  <div className="mt-2 inline-block bg-navy-900 text-gold-400 px-4 py-1 rounded text-xs sm:text-sm font-bold tracking-wider uppercase">
                    Official Examination Marks Card
                  </div>
                </div>
                <div className="text-center sm:text-right text-xs text-slate-600">
                  <div className="font-bold text-navy-900 text-sm">{result.examination_name}</div>
                  <div>Academic Year: {result.academic_year || "2026-2027"}</div>
                  <span className="mt-1 inline-block px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold">
                    OFFICIAL PUBLISHED
                  </span>
                </div>
              </div>

              {/* Student Details */}
              <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3 bg-blue-50/70 border border-royal-500/30 rounded-lg p-4 text-sm">
                <div>
                  <span className="font-semibold text-navy-900">Student Name: </span>
                  <span className="text-slate-900 font-medium">{result.student_name}</span>
                </div>
                <div>
                  <span className="font-semibold text-navy-900">Student ID: </span>
                  <span className="font-mono font-bold text-royal-700">{result.student_code}</span>
                </div>
                <div>
                  <span className="font-semibold text-navy-900">Class & Section: </span>
                  <span>
                    {result.class_name} — Section {result.section}
                  </span>
                </div>
                <div>
                  <span className="font-semibold text-navy-900">Examination Date: </span>
                  <span>{result.exam_date}</span>
                </div>
              </div>

              {/* Subject Marks Table */}
              <div className="mt-6 overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="bg-navy-900 text-white">
                      <th className="py-2.5 px-3 text-center border border-navy-900">Sl. No.</th>
                      <th className="py-2.5 px-3 text-left border border-navy-900">Subject</th>
                      <th className="py-2.5 px-3 text-center border border-navy-900">Max Marks</th>
                      <th className="py-2.5 px-3 text-center border border-navy-900">Marks Obtained</th>
                      <th className="py-2.5 px-3 text-center border border-navy-900">Grade</th>
                      <th className="py-2.5 px-3 text-left border border-navy-900">Remarks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.subjects.map((sub, idx) => (
                      <tr key={idx} className={idx % 2 === 1 ? "bg-blue-50/50" : "bg-white"}>
                        <td className="py-2.5 px-3 text-center border border-slate-300">{idx + 1}</td>
                        <td className="py-2.5 px-3 font-medium text-slate-900 border border-slate-300">{sub.subject}</td>
                        <td className="py-2.5 px-3 text-center border border-slate-300">{sub.max_marks}</td>
                        <td className="py-2.5 px-3 text-center font-bold text-navy-900 border border-slate-300">
                          {sub.marks_obtained}
                        </td>
                        <td className="py-2.5 px-3 text-center font-bold text-royal-700 border border-slate-300">
                          {sub.grade}
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 border border-slate-300">{sub.remarks}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Final Summary */}
              <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 gap-4 bg-amber-50/70 border border-gold-500 rounded-lg p-4 text-sm">
                <div>
                  <div className="text-xs text-slate-500 uppercase">Total Max Marks</div>
                  <div className="text-lg font-bold text-navy-900">{result.total_max}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase">Total Obtained</div>
                  <div className="text-lg font-bold text-navy-900">{result.total_obtained}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase">Overall Percentage</div>
                  <div className="text-lg font-bold text-royal-700">{result.percentage}%</div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase">Overall Grade &amp; Class Rank</div>
                  <div className="text-base font-bold text-navy-900">
                    {result.overall_grade}
                    {result.class_rank ? `  •  Rank #${result.class_rank} of ${result.class_total_students}` : ""}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase">Result Status</div>
                  <div
                    className={`text-base font-extrabold ${
                      result.result_status === "PASS" ? "text-emerald-700" : "text-red-700"
                    }`}
                  >
                    {result.result_status}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 uppercase">Teacher Remarks</div>
                  <div className="font-semibold text-slate-800">{result.teacher_remarks}</div>
                </div>
              </div>

              {/* Seal & Director Signature */}
              <div className="mt-10 flex flex-col sm:flex-row items-center justify-between gap-6 pt-4">
                {/* Official Institutional Seal */}
                <div className="flex items-center gap-4">
                  <div className="w-24 h-24 rounded-full border-2 border-navy-900 p-1 flex items-center justify-center">
                    <div className="w-full h-full rounded-full border border-gold-500 flex flex-col items-center justify-center text-center px-1">
                      <span className="text-[9px] font-extrabold text-navy-900 leading-tight">AK TUITION</span>
                      <span className="text-[8px] font-bold text-gold-600 leading-tight mt-0.5">OFFICIAL SEAL</span>
                      <span className="text-[7px] text-royal-600 leading-tight mt-0.5">VERIFIED</span>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">
                    <div>Issued via AKTP PORTAL</div>
                    <div>Digitally Verified Record</div>
                  </div>
                </div>

                {/* Director Signature (never fabricated) */}
                <div className="text-center min-w-[220px]">
                  {result.director_signature_path ? (
                    <img
                      src={resolveAssetUrl(result.director_signature_path)}
                      alt="Authorized Director Signature"
                      className="h-14 mx-auto object-contain mb-1"
                    />
                  ) : (
                    <div className="h-14 flex items-end justify-center pb-2 border-b border-dashed border-slate-400">
                      <span className="text-xs italic text-slate-400">Authorized Signature</span>
                    </div>
                  )}
                  <div className="border-t border-navy-900 pt-1.5 mt-1">
                    <div className="font-bold text-navy-900 text-sm">
                      {result.director_name || "G. Akash, B.E."}
                    </div>
                    <div className="text-xs text-slate-600">
                      {result.director_designation || "Director, AK Tuition"}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
