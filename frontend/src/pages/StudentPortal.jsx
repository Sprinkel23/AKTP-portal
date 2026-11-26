import React, { useEffect, useState } from "react";
import {
  LayoutDashboard,
  User,
  Calendar,
  Award,
  ClipboardCheck,
  IndianRupee,
  Laptop,
  Download,
  Clock,
} from "lucide-react";
import PortalLayout from "../components/PortalLayout";
import MarksCardModal from "../components/MarksCardModal";
import api, { downloadAuthorizedFile, resolveAssetUrl } from "../api/client";

export default function StudentPortal() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [attendance, setAttendance] = useState(null);
  const [exams, setExams] = useState([]);
  const [results, setResults] = useState([]);
  const [fees, setFees] = useState(null);
  const [tests, setTests] = useState([]);
  const [activeMarksCard, setActiveMarksCard] = useState(null);

  // Online Test Runner state
  const [activeTest, setActiveTest] = useState(null);
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [answersMap, setAnswersMap] = useState({});
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [testResult, setTestResult] = useState(null);
  const [toast, setToast] = useState("");

  const loadAll = async () => {
    try {
      const [d, a, e, r, f, t] = await Promise.all([
        api.get("/api/student/dashboard"),
        api.get("/api/student/attendance"),
        api.get("/api/student/examinations"),
        api.get("/api/student/results"),
        api.get("/api/student/fees"),
        api.get("/api/student/tests"),
      ]);
      setDash(d.data);
      setAttendance(a.data);
      setExams(e.data);
      setResults(r.data);
      setFees(f.data);
      setTests(t.data);
    } catch {}
  };

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (!activeTest || secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((s) => (s > 0 ? s - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [activeTest, secondsLeft]);

  const startTest = async (paperId) => {
    try {
      const res = await api.post(`/api/student/tests/${paperId}/start`);
      setActiveTest(res.data);
      setCurrentQIdx(0);
      setAnswersMap({});
      setSecondsLeft(res.data.duration_minutes * 60);
      setTestResult(null);
    } catch (err) {
      setToast(err.response?.data?.detail || "Could not start test.");
    }
  };

  const submitTest = async () => {
    if (!activeTest) return;
    try {
      const answers = activeTest.questions.map((q) => ({
        question_id: q.id,
        selected_option_id: answersMap[q.id]?.selected_option_id || null,
        answer_text: answersMap[q.id]?.answer_text || null,
      }));
      const res = await api.post(`/api/student/tests/attempts/${activeTest.attempt_id}/submit`, { answers });
      setToast(res.data.message);
      setActiveTest(null);
      loadAll();
    } catch (err) {
      setToast(err.response?.data?.detail || "Submission failed.");
    }
  };

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "profile", label: "My Profile", icon: User },
    { id: "exams", label: "Exam Timetable", icon: Calendar },
    { id: "tests", label: "Practice Tests", icon: Laptop },
    { id: "results", label: "Published Results", icon: Award },
    { id: "attendance", label: "Attendance & Absent Dates", icon: ClipboardCheck },
    { id: "fees", label: "Fee & Payment History", icon: IndianRupee },
  ];

  const p = dash?.profile;

  return (
    <PortalLayout
      title="Student Portal"
      subtitle={p ? `${p.student_name} (${p.student_code}) • ${p.class_name} (${p.section})` : "AKTP Student Workspace"}
      navItems={navItems}
      activeTab={tab}
      onSelectTab={setTab}
    >
      {toast && <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 font-medium">{toast}</div>}

      {/* DASHBOARD */}
      {tab === "dashboard" && dash && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-navy-900 to-royal-700 rounded-2xl p-6 text-white flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {p.photo_path ? (
                <img src={resolveAssetUrl(p.photo_path)} alt={p.student_name} className="w-16 h-16 rounded-full object-cover border-2 border-gold-400" />
              ) : (
                <div className="w-16 h-16 rounded-full bg-gold-500 text-navy-950 font-extrabold text-xl flex items-center justify-center">
                  {p.student_name.slice(0, 2).toUpperCase()}
                </div>
              )}
              <div>
                <div className="text-xs font-bold text-gold-400 uppercase">{p.student_code} • {p.class_name} ({p.section})</div>
                <h2 className="text-2xl font-bold">{p.student_name}</h2>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="bg-white/10 rounded-xl px-4 py-2">
                <div className="text-xs text-blue-200">Attendance</div>
                <div className="text-xl font-extrabold text-gold-300">{dash.attendance_summary.attendance_percentage}%</div>
              </div>
              <div className="bg-white/10 rounded-xl px-4 py-2">
                <div className="text-xs text-blue-200">Upcoming Exams</div>
                <div className="text-xl font-extrabold">{dash.upcoming_examinations.length}</div>
              </div>
              <div className="bg-white/10 rounded-xl px-4 py-2">
                <div className="text-xs text-blue-200">Pending Fees</div>
                <div className="text-xl font-extrabold text-amber-300">₹{dash.fee_summary.pending_amount.toLocaleString("en-IN")}</div>
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl p-5 shadow-sm border">
              <h3 className="font-bold text-navy-900 mb-3">Recent Published Results</h3>
              {dash.recent_published_results.length === 0 ? (
                <p className="text-sm text-slate-500">No published results yet.</p>
              ) : (
                <div className="space-y-2 text-sm">
                  {dash.recent_published_results.map((r) => (
                    <div key={r.id} className="p-3 rounded-xl bg-blue-50/70 flex justify-between">
                      <span>{r.examination_name} — <strong>{r.subject_name}</strong></span>
                      <span className="font-bold text-navy-900">{r.marks_obtained}/{r.max_marks} ({r.grade})</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border">
              <h3 className="font-bold text-navy-900 mb-3">Latest Announcements</h3>
              <div className="space-y-2 text-sm">
                {dash.announcements.map((a) => (
                  <div key={a.id} className="p-3 rounded-xl bg-slate-50 border">
                    <div className="font-bold text-navy-900">{a.title}</div>
                    <div className="text-xs text-slate-600 mt-0.5">{a.content}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PROFILE */}
      {tab === "profile" && p && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border max-w-2xl space-y-3 text-sm">
          <h3 className="font-bold text-lg text-navy-900">Student Profile</h3>
          <div className="grid sm:grid-cols-2 gap-3">
            <div><strong>Student ID:</strong> {p.student_code}</div>
            <div><strong>Full Name:</strong> {p.student_name}</div>
            <div><strong>Class & Section:</strong> {p.class_name} ({p.section})</div>
            <div><strong>Date of Birth:</strong> {p.date_of_birth || "-"}</div>
            <div><strong>Parent Name:</strong> {p.parent_name}</div>
            <div><strong>Parent Phone:</strong> {p.parent_phone}</div>
            <div className="sm:col-span-2"><strong>Address:</strong> {p.address || "-"}</div>
          </div>
        </div>
      )}

      {/* EXAMS */}
      {tab === "exams" && (
        <div className="space-y-4">
          {exams.map((ex) => (
            <div key={ex.id} className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
              <div className="flex flex-wrap justify-between items-center gap-2">
                <div>
                  <h4 className="font-bold text-navy-900 text-lg">{ex.name}</h4>
                  <div className="text-xs text-slate-500">{ex.start_date} to {ex.end_date}</div>
                </div>
                <button
                  onClick={() => downloadAuthorizedFile(`/api/student/examinations/${ex.id}/timetable-pdf`, `AK_Timetable_${ex.id}.pdf`)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy-900 text-white text-xs font-semibold"
                >
                  <Download className="w-4 h-4" /> Download Timetable PDF
                </button>
              </div>
              <div className="grid sm:grid-cols-3 gap-2 text-xs">
                {ex.subjects.map((s, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-blue-50/70 border border-blue-100">
                    <div className="font-bold text-navy-900">{s.subject_name}</div>
                    <div>{s.exam_date} • {s.start_time}</div>
                    <div>Max Marks: {s.max_marks} ({s.duration_minutes} mins)</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ONLINE PRACTICE TESTS */}
      {tab === "tests" && (
        <div className="space-y-6">
          {activeTest ? (
            <div className="bg-white rounded-2xl p-6 shadow-md border space-y-5">
              <div className="flex flex-wrap justify-between items-center gap-3 pb-4 border-b">
                <div>
                  <h3 className="font-bold text-navy-900 text-lg">{activeTest.title}</h3>
                  <p className="text-xs text-slate-500">{activeTest.instructions}</p>
                </div>
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-navy-900 text-gold-400 font-mono font-bold text-sm">
                  <Clock className="w-4 h-4" />
                  {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, "0")}
                </div>
              </div>

              {/* Question Navigation Pills */}
              <div className="flex flex-wrap gap-2">
                {activeTest.questions.map((q, idx) => (
                  <button
                    key={q.id}
                    onClick={() => setCurrentQIdx(idx)}
                    className={`w-9 h-9 rounded-lg text-xs font-bold border ${
                      currentQIdx === idx
                        ? "bg-royal-600 text-white"
                        : answersMap[q.id]
                        ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                        : "bg-slate-50"
                    }`}
                  >
                    Q{idx + 1}
                  </button>
                ))}
              </div>

              {activeTest.questions[currentQIdx] && (() => {
                const q = activeTest.questions[currentQIdx];
                return (
                  <div className="p-5 rounded-2xl bg-blue-50/50 border space-y-4">
                    <div className="flex justify-between text-xs font-bold text-royal-700">
                      <span>Question {currentQIdx + 1} of {activeTest.questions.length} ({q.question_type})</span>
                      <span>{q.marks} Marks</span>
                    </div>
                    <div className="font-semibold text-navy-900 text-base">{q.question_text}</div>

                    {q.question_type === "MCQ" ? (
                      <div className="space-y-2">
                        {q.options.map((opt) => (
                          <label
                            key={opt.id}
                            className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer bg-white ${
                              answersMap[q.id]?.selected_option_id === opt.id ? "border-royal-600 ring-2 ring-royal-500/20" : ""
                            }`}
                          >
                            <input
                              type="radio"
                              name={`q-${q.id}`}
                              checked={answersMap[q.id]?.selected_option_id === opt.id}
                              onChange={() =>
                                setAnswersMap({ ...answersMap, [q.id]: { selected_option_id: opt.id, answer_text: opt.option_label } })
                              }
                            />
                            <span className="text-sm">({opt.option_label}) {opt.option_text}</span>
                          </label>
                        ))}
                      </div>
                    ) : (
                      <textarea
                        rows={4}
                        value={answersMap[q.id]?.answer_text || ""}
                        onChange={(e) => setAnswersMap({ ...answersMap, [q.id]: { answer_text: e.target.value } })}
                        placeholder="Type your answer here..."
                        className="w-full rounded-xl border p-3 text-sm bg-white"
                      />
                    )}
                  </div>
                );
              })()}

              <div className="flex justify-between">
                <button
                  disabled={currentQIdx === 0}
                  onClick={() => setCurrentQIdx((i) => Math.max(0, i - 1))}
                  className="px-4 py-2 rounded-xl border text-sm font-semibold disabled:opacity-40"
                >
                  Previous
                </button>
                <div className="flex gap-2">
                  {currentQIdx < activeTest.questions.length - 1 && (
                    <button
                      onClick={() => setCurrentQIdx((i) => i + 1)}
                      className="px-4 py-2 rounded-xl bg-royal-600 text-white text-sm font-semibold"
                    >
                      Next
                    </button>
                  )}
                  <button onClick={submitTest} className="px-6 py-2 rounded-xl bg-emerald-700 text-white text-sm font-bold">
                    Submit Test
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {tests.map((t) => (
                <div key={t.id} className="bg-white rounded-2xl p-5 shadow-sm border flex flex-col justify-between gap-3">
                  <div>
                    <span className="text-xs font-bold text-royal-600">{t.subject_name}</span>
                    <h4 className="font-bold text-navy-900 text-lg mt-0.5">{t.title}</h4>
                    <p className="text-xs text-slate-500 mt-1">{t.question_count} Questions • {t.total_marks} Marks • {t.duration_minutes} mins</p>
                    {t.instructions && <p className="text-xs text-slate-600 mt-2">{t.instructions}</p>}
                  </div>
                  <div className="flex flex-wrap gap-2 pt-2">
                    <button onClick={() => startTest(t.id)} className="px-4 py-2 rounded-xl bg-navy-900 text-white text-xs font-bold">
                      Start Practice Test
                    </button>
                    {t.latest_attempt && t.latest_attempt.status === "EVALUATED" && t.allow_result_view && (
                      <button
                        onClick={async () => {
                          const res = await api.get(`/api/student/tests/attempts/${t.latest_attempt.id}/result`);
                          setTestResult(res.data);
                        }}
                        className="px-4 py-2 rounded-xl bg-blue-50 text-royal-700 text-xs font-bold"
                      >
                        View Score ({t.latest_attempt.total_score}/{t.latest_attempt.max_score})
                      </button>
                    )}
                    {t.latest_attempt && t.latest_attempt.status === "SUBMITTED" && (
                      <span className="px-3 py-2 rounded-xl bg-amber-50 text-amber-800 text-xs font-semibold">
                        Submitted • Awaiting Teacher Review
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {testResult && (
            <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
              <h4 className="font-bold text-navy-900">Test Evaluation — {testResult.title} ({testResult.total_score}/{testResult.max_score})</h4>
              <div className="space-y-2 text-xs">
                {testResult.answers.map((a, i) => (
                  <div key={i} className="p-3 rounded-xl bg-slate-50 border">
                    <div className="font-bold">{a.question_text}</div>
                    <div>Your Answer: {a.answer_text || "-"} | Awarded: <strong>{a.marks_awarded ?? "Pending"} / {a.max_marks}</strong></div>
                    {a.correct_answer && <div className="text-emerald-700">Correct Answer: {a.correct_answer}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* PUBLISHED RESULTS & OFFICIAL MARKS CARD */}
      {tab === "results" && (
        <div className="space-y-4">
          {results.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border">
              No published examination results available yet. Results appear here once approved by the Administrator.
            </div>
          ) : (
            results.map((res) => (
              <div key={res.examination_id} className="bg-white rounded-2xl p-5 shadow-sm border flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h4 className="font-bold text-navy-900 text-lg">{res.examination_name}</h4>
                  <p className="text-xs text-slate-600">
                    Total: {res.total_obtained} / {res.total_max} ({res.percentage}%) • Grade: <strong>{res.overall_grade}</strong>
                    {res.class_rank ? <> • Class Rank: <strong className="text-royal-700">#{res.class_rank} / {res.class_total_students}</strong></> : null}
                    {" "}• Status: <strong className="text-emerald-700">{res.result_status}</strong>
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveMarksCard(res)}
                    className="px-4 py-2 rounded-xl bg-navy-900 text-gold-400 text-xs font-bold"
                  >
                    View Official Marks Card
                  </button>
                  <button
                    onClick={() => downloadAuthorizedFile(`/api/student/results/${res.examination_id}/marks-card-pdf`, `AK_MarksCard_${res.student_code}_Exam${res.examination_id}.pdf`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-royal-600 text-white text-xs font-bold"
                  >
                    <Download className="w-4 h-4" /> Download PDF
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ATTENDANCE & DEDICATED ABSENT DATES */}
      {tab === "attendance" && attendance && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl p-4 border-l-4 border-navy-900">
              <div className="text-xs text-slate-500 uppercase font-semibold">Total Working Days</div>
              <div className="text-2xl font-extrabold text-navy-900 mt-1">{attendance.total_working_days}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-emerald-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Present Days</div>
              <div className="text-2xl font-extrabold text-emerald-700 mt-1">{attendance.present_days}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-red-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Absent Days</div>
              <div className="text-2xl font-extrabold text-red-600 mt-1">{attendance.absent_days}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-royal-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Overall Attendance %</div>
              <div className="text-2xl font-extrabold text-royal-700 mt-1">{attendance.attendance_percentage}%</div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-5 shadow-sm border">
            <h3 className="font-bold text-navy-900 mb-3">Absent Details</h3>
            {attendance.absent_details.length === 0 ? (
              <p className="text-sm text-emerald-700 font-medium">100% Attendance — No absent dates recorded.</p>
            ) : (
              <table className="w-full max-w-md text-sm border">
                <thead className="bg-navy-900 text-white text-xs uppercase">
                  <tr>
                    <th className="p-2.5 text-left">Absent Date</th>
                    <th className="p-2.5 text-center">Attendance Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {attendance.absent_details.map((row, idx) => (
                    <tr key={idx}>
                      <td className="p-2.5 font-medium">{row.absent_date}</td>
                      <td className="p-2.5 text-center">
                        <span className="px-2.5 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-bold">
                          {row.attendance_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* FEES & PAYMENT HISTORY */}
      {tab === "fees" && fees && (
        <div className="space-y-6">
          <div className="grid sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-2xl p-4 border-l-4 border-navy-900">
              <div className="text-xs text-slate-500 uppercase font-semibold">Total Tuition Fees</div>
              <div className="text-2xl font-extrabold text-navy-900 mt-1">₹{fees.total_fees.toLocaleString("en-IN")}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-emerald-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Paid Amount</div>
              <div className="text-2xl font-extrabold text-emerald-700 mt-1">₹{fees.paid_amount.toLocaleString("en-IN")}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-amber-500">
              <div className="text-xs text-slate-500 uppercase font-semibold">Pending Amount</div>
              <div className="text-2xl font-extrabold text-amber-700 mt-1">₹{fees.pending_amount.toLocaleString("en-IN")}</div>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
            <div className="p-4 border-b font-bold text-navy-900">Payment History</div>
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-xs uppercase">
                <tr>
                  <th className="p-3 text-left">Receipt No</th>
                  <th className="p-3 text-left">Date</th>
                  <th className="p-3 text-left">Mode</th>
                  <th className="p-3 text-right">Amount</th>
                  <th className="p-3 text-right">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {fees.payments.map((pay) => (
                  <tr key={pay.id}>
                    <td className="p-3 font-mono font-bold">{pay.receipt_number}</td>
                    <td className="p-3">{pay.payment_date}</td>
                    <td className="p-3">{pay.payment_mode}</td>
                    <td className="p-3 text-right font-bold">₹{pay.amount.toLocaleString("en-IN")}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => downloadAuthorizedFile(`/api/student/payments/${pay.id}/receipt-pdf`, `AK_Receipt_${pay.receipt_number}.pdf`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-blue-50 text-royal-700 text-xs font-semibold"
                      >
                        <Download className="w-3.5 h-3.5" /> PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <MarksCardModal
        result={activeMarksCard}
        pdfUrl={activeMarksCard ? `/api/student/results/${activeMarksCard.examination_id}/marks-card-pdf` : null}
        onClose={() => setActiveMarksCard(null)}
      />
    </PortalLayout>
  );
}
