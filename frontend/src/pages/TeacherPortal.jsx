import React, { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  FileEdit,
  FilePlus2,
  CheckCircle,
  Download,
  Plus,
  Trash2,
  KeyRound,
  Copy,
  X,
} from "lucide-react";
import PortalLayout from "../components/PortalLayout";
import api, { downloadAuthorizedFile } from "../api/client";

const QUESTION_TYPES = [
  { value: "MCQ", label: "Multiple Choice Question (MCQ)" },
  { value: "FILL_IN_BLANK", label: "Fill in the Blanks" },
  { value: "MATCH_FOLLOWING", label: "Match the Following" },
  { value: "ONE_MARK", label: "One-Mark Question" },
  { value: "TWO_MARK", label: "Two-Mark Question" },
  { value: "THREE_MARK", label: "Three-Mark Question" },
  { value: "FOUR_MARK", label: "Four-Mark Question" },
  { value: "FIVE_MARK", label: "Five-Mark Question" },
  { value: "SIX_PLUS_MARK", label: "Six-Mark & Above Question" },
];

export default function TeacherPortal() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [students, setStudents] = useState([]);
  const [exams, setExams] = useState([]);
  const [papers, setPapers] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [attHistory, setAttHistory] = useState([]);
  const [toast, setToast] = useState({ type: "", text: "" });

  // Attendance state
  const [attClassId, setAttClassId] = useState("");
  const [attDate, setAttDate] = useState(new Date().toISOString().slice(0, 10));
  const [attRows, setAttRows] = useState([]);

  // Marks state
  const [selectedExamSubjId, setSelectedExamSubjId] = useState("");
  const [marksSheet, setMarksSheet] = useState(null);

  // Question Paper state
  const [qpForm, setQpForm] = useState({
    title: "",
    class_id: "",
    subject_id: "",
    examination_id: "",
    duration_minutes: 60,
    total_marks: 10,
    evaluation_scheme: "Stepwise marking as per AK Tuition rubric.",
    instructions: "Answer all questions neatly.",
    is_online_test: true,
    is_published: true,
    auto_evaluate_mcq: true,
    allow_result_view: true,
    questions: [
      {
        question_type: "MCQ",
        question_text: "",
        marks: 2,
        correct_answer: "A",
        match_pairs: [{ left: "", right: "" }],
        options: [
          { option_label: "A", option_text: "", is_correct: true },
          { option_label: "B", option_text: "", is_correct: false },
          { option_label: "C", option_text: "", is_correct: false },
          { option_label: "D", option_text: "", is_correct: false },
        ],
      },
    ],
  });

  // Attempt evaluation state
  const [evalMap, setEvalMap] = useState({});

  // Add Student + Generated Credentials state
  const [studentModal, setStudentModal] = useState(false);
  const [studentForm, setStudentForm] = useState({
    student_name: "",
    gender: "Male",
    class_id: "",
    section: "A",
    student_phone: "",
    parent_name: "",
    parent_phone: "",
    address: "",
    student_password: "",
    parent_password: "",
  });
  const [credsModal, setCredsModal] = useState(null);

  const notify = (text, type = "success") => {
    setToast({ type, text });
    setTimeout(() => setToast({ type: "", text: "" }), 5000);
  };

  const loadAll = async () => {
    try {
      const [dRes, sRes, exRes, qpRes, attHistRes, atmpRes] = await Promise.all([
        api.get("/api/teacher/dashboard"),
        api.get("/api/teacher/students"),
        api.get("/api/teacher/examinations"),
        api.get("/api/teacher/question-papers"),
        api.get("/api/teacher/attendance/history"),
        api.get("/api/teacher/test-attempts"),
      ]);
      setDash(dRes.data);
      setStudents(sRes.data);
      setExams(exRes.data);
      setPapers(qpRes.data);
      setAttHistory(attHistRes.data);
      setAttempts(atmpRes.data);
      if (!attClassId && dRes.data.assignments?.length) {
        setAttClassId(String(dRes.data.assignments[0].class_id));
      }
    } catch (err) {
      notify(err.response?.data?.detail || "Error loading teacher portal.", "error");
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const uniqueClasses = Array.from(
    new Map((dash?.assignments || []).map((a) => [a.class_id, { id: a.class_id, name: a.class_name }])).values()
  );

  const loadAttendanceSheet = async () => {
    if (!attClassId || !attDate) return;
    try {
      const res = await api.get(`/api/teacher/attendance?class_id=${attClassId}&attendance_date=${attDate}`);
      setAttRows(res.data.students);
    } catch (err) {
      notify(err.response?.data?.detail || "Could not load attendance sheet.", "error");
    }
  };

  useEffect(() => {
    if (tab === "attendance" && attClassId) {
      loadAttendanceSheet();
    }
  }, [tab, attClassId, attDate]);

  const loadMarksSheet = async (examSubjId) => {
    setSelectedExamSubjId(examSubjId);
    if (!examSubjId) {
      setMarksSheet(null);
      return;
    }
    try {
      const res = await api.get(`/api/teacher/marks/${examSubjId}`);
      setMarksSheet(res.data);
    } catch (err) {
      notify(err.response?.data?.detail || "Failed to load marks sheet.", "error");
    }
  };

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "students", label: "Assigned Students", icon: Users },
    { id: "attendance", label: "Daily Attendance", icon: ClipboardCheck },
    { id: "marks", label: "Marks Entry", icon: FileEdit },
    { id: "papers", label: "Question Papers", icon: FilePlus2 },
    { id: "evaluate", label: "Test Evaluation", icon: CheckCircle },
  ];

  const sumQuestionMarks = qpForm.questions.reduce((acc, q) => acc + Number(q.marks || 0), 0);

  return (
    <PortalLayout
      title="Teacher Portal"
      subtitle={dash ? `${dash.teacher.teacher_name} (${dash.teacher.teacher_code})` : "Academic Workspace"}
      navItems={navItems}
      activeTab={tab}
      onSelectTab={setTab}
    >
      {toast.text && (
        <div className={`mb-4 px-4 py-3 rounded-xl text-sm font-medium border ${toast.type === "error" ? "bg-red-50 text-red-700 border-red-200" : "bg-emerald-50 text-emerald-800 border-emerald-200"}`}>
          {toast.text}
        </div>
      )}

      {/* DASHBOARD */}
      {tab === "dashboard" && dash && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: "Assigned Classes", val: dash.cards.assigned_classes },
              { label: "Assigned Students", val: dash.cards.assigned_students },
              { label: "Assigned Subjects", val: dash.cards.assigned_subjects },
              { label: "Today's Attendance", val: `${dash.cards.today_attendance_present}/${dash.cards.today_attendance_total}` },
              { label: "Upcoming Exams", val: dash.cards.upcoming_examinations },
              { label: "Pending Mark Submissions", val: dash.cards.pending_mark_submissions },
              { label: "Practice Tests Created", val: dash.cards.practice_tests },
            ].map((c) => (
              <div key={c.label} className="bg-white rounded-2xl p-4 shadow-sm border-l-4 border-royal-600">
                <div className="text-xs font-semibold text-slate-500 uppercase">{c.label}</div>
                <div className="text-2xl font-extrabold text-navy-900 mt-1">{c.val}</div>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl p-5 shadow-sm border">
              <h3 className="font-bold text-navy-900 mb-3">My Class & Subject Assignments</h3>
              <div className="space-y-2 text-sm">
                {dash.assignments.map((a) => (
                  <div key={a.id} className="p-3 rounded-xl bg-blue-50/70 border border-blue-100 flex justify-between">
                    <span className="font-semibold text-navy-900">{a.class_name} — {a.subject_name}</span>
                    {a.is_class_teacher && <span className="px-2 py-0.5 rounded bg-navy-900 text-gold-400 text-xs font-bold">Class Teacher</span>}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border">
              <h3 className="font-bold text-navy-900 mb-3">Upcoming Examinations</h3>
              <div className="space-y-2 text-sm">
                {dash.upcoming_examinations.length === 0 ? (
                  <p className="text-slate-500 text-xs">No upcoming exams for your assigned classes.</p>
                ) : (
                  dash.upcoming_examinations.map((ex) => (
                    <div key={ex.id} className="p-3 rounded-xl bg-slate-50 border">
                      <div className="font-bold text-navy-900">{ex.name}</div>
                      <div className="text-xs text-slate-600">{ex.class_name} • {ex.start_date} to {ex.end_date}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ASSIGNED STUDENTS (No Financial Data) */}
      {tab === "students" && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-4 shadow-sm border flex flex-wrap items-center justify-between gap-3">
            <div className="font-bold text-navy-900">Assigned Students &amp; Academic Summary</div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => downloadAuthorizedFile("/api/teacher/results-pdf", "AK_Teacher_Overall_Results.pdf")}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-royal-600 text-white text-xs font-bold"
              >
                <Download className="w-4 h-4" /> Print Overall Student Result PDF
              </button>
              <button
                onClick={() => {
                  setStudentForm({
                    student_name: "",
                    gender: "Male",
                    class_id: uniqueClasses[0]?.id ? String(uniqueClasses[0].id) : "",
                    section: "A",
                    student_phone: "",
                    parent_name: "",
                    parent_phone: "",
                    address: "",
                    student_password: "",
                    parent_password: "",
                  });
                  setStudentModal(true);
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy-900 text-white text-xs font-bold"
              >
                <Plus className="w-4 h-4" /> Add Student &amp; Generate Login
              </button>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-navy-900 text-white text-xs uppercase">
                <tr>
                  <th className="p-3 text-left">Student ID</th>
                  <th className="p-3 text-left">Name</th>
                  <th className="p-3 text-left">Class</th>
                  <th className="p-3 text-center">Attendance %</th>
                  <th className="p-3 text-left">Recent Marks</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {students.map((s) => (
                  <tr key={s.id}>
                    <td className="p-3 font-mono font-bold text-royal-700">{s.student_code}</td>
                    <td className="p-3 font-semibold">{s.student_name}</td>
                    <td className="p-3">{s.class_name} ({s.section})</td>
                    <td className="p-3 text-center font-bold">{s.attendance_percentage}% ({s.present_days}/{s.working_days})</td>
                    <td className="p-3 text-xs space-y-1">
                      {s.recent_marks.map((m, idx) => (
                        <div key={idx}>{m.exam} • {m.subject}: <strong>{m.marks_obtained}/{m.max_marks}</strong> ({m.status})</div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* DAILY ATTENDANCE */}
      {tab === "attendance" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-4">
            <div className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Select Class</label>
                <select value={attClassId} onChange={(e) => setAttClassId(e.target.value)} className="rounded-lg border px-3 py-2 text-sm">
                  {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Attendance Date</label>
                <input type="date" value={attDate} onChange={(e) => setAttDate(e.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
              </div>
              <button onClick={loadAttendanceSheet} className="px-4 py-2 rounded-lg bg-blue-50 text-royal-700 text-sm font-semibold">Refresh List</button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm border">
                <thead className="bg-navy-900 text-white text-xs uppercase">
                  <tr>
                    <th className="p-2.5 text-left">Student ID</th>
                    <th className="p-2.5 text-left">Student Name</th>
                    <th className="p-2.5 text-center">Status</th>
                    <th className="p-2.5 text-left">Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {attRows.map((row, idx) => (
                    <tr key={row.student_id}>
                      <td className="p-2.5 font-mono font-bold text-royal-700">{row.student_code}</td>
                      <td className="p-2.5 font-medium">{row.student_name}</td>
                      <td className="p-2.5 text-center space-x-2">
                        {["PRESENT", "ABSENT"].map((opt) => (
                          <button
                            key={opt}
                            type="button"
                            onClick={() => {
                              const next = [...attRows];
                              next[idx].status = opt;
                              setAttRows(next);
                            }}
                            className={`px-3 py-1 rounded-lg text-xs font-bold ${
                              row.status === opt
                                ? opt === "PRESENT" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {opt}
                          </button>
                        ))}
                      </td>
                      <td className="p-2.5">
                        <input
                          value={row.remarks || ""}
                          onChange={(e) => {
                            const next = [...attRows];
                            next[idx].remarks = e.target.value;
                            setAttRows(next);
                          }}
                          placeholder="Optional note"
                          className="w-full rounded border px-2.5 py-1 text-xs"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={async () => {
                try {
                  const res = await api.post("/api/teacher/attendance", {
                    class_id: Number(attClassId),
                    attendance_date: attDate,
                    entries: attRows.map((r) => ({ student_id: r.student_id, status: r.status, remarks: r.remarks })),
                  });
                  notify(res.data.message);
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Failed to save attendance.", "error");
                }
              }}
              className="px-6 py-2.5 rounded-xl bg-navy-900 text-white text-sm font-bold"
            >
              Save Attendance
            </button>
          </div>

          <div className="bg-white rounded-2xl p-5 shadow-sm border">
            <h3 className="font-bold text-navy-900 mb-3">Recent Attendance History</h3>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
              {attHistory.slice(0, 18).map((h) => (
                <div key={h.id} className="p-2.5 rounded-lg bg-slate-50 border flex justify-between">
                  <span>{h.attendance_date} • {h.student_code} {h.student_name}</span>
                  <span className={`font-bold ${h.status === "PRESENT" ? "text-emerald-700" : "text-red-600"}`}>{h.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* MARKS ENTRY (SUBMISSION BECOMES PENDING FOR ADMIN APPROVAL) */}
      {tab === "marks" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-4">
            <h3 className="font-bold text-navy-900">Examination Marks Entry</h3>
            <p className="text-xs text-slate-600">
              Submitted marks enter <strong>PENDING</strong> status for Administrator review and approval. Teachers cannot publish official results directly.
            </p>
            <select
              value={selectedExamSubjId}
              onChange={(e) => loadMarksSheet(e.target.value)}
              className="rounded-xl border px-3.5 py-2 text-sm min-w-[300px]"
            >
              <option value="">Select Assigned Examination & Subject</option>
              {exams.map((ex) =>
                ex.subjects.map((es) => (
                  <option key={es.examination_subject_id} value={es.examination_subject_id}>
                    {ex.name} ({ex.class_name}) — {es.subject_name} [Max: {es.max_marks}] ({es.approval_status})
                  </option>
                ))
              )}
            </select>

            {marksSheet && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 bg-blue-50 p-3 rounded-xl text-xs">
                  <div>
                    <strong>{marksSheet.examination_name}</strong> — {marksSheet.subject_name} (Max Marks: {marksSheet.max_marks})
                  </div>
                  <div>
                    Approval Status: <strong className="text-royal-700">{marksSheet.approval_status}</strong>
                    {marksSheet.rejection_reason && <span className="text-red-600 ml-2">Reason: {marksSheet.rejection_reason}</span>}
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm border">
                    <thead className="bg-navy-900 text-white text-xs uppercase">
                      <tr>
                        <th className="p-2.5 text-left">Student ID</th>
                        <th className="p-2.5 text-left">Name</th>
                        <th className="p-2.5 text-center">Marks Obtained (Max {marksSheet.max_marks})</th>
                        <th className="p-2.5 text-left">Remarks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {marksSheet.students.map((st, idx) => (
                        <tr key={st.student_id}>
                          <td className="p-2.5 font-mono font-bold text-royal-700">{st.student_code}</td>
                          <td className="p-2.5 font-medium">{st.student_name}</td>
                          <td className="p-2.5 text-center">
                            <input
                              type="number"
                              min={0}
                              max={marksSheet.max_marks}
                              step="0.5"
                              value={st.marks_obtained}
                              onChange={(e) => {
                                const next = { ...marksSheet };
                                next.students[idx].marks_obtained = e.target.value;
                                setMarksSheet(next);
                              }}
                              className="w-28 rounded border px-2 py-1 text-center"
                            />
                          </td>
                          <td className="p-2.5">
                            <input
                              value={st.remarks || ""}
                              onChange={(e) => {
                                const next = { ...marksSheet };
                                next.students[idx].remarks = e.target.value;
                                setMarksSheet(next);
                              }}
                              placeholder="Optional remarks"
                              className="w-full rounded border px-2.5 py-1 text-xs"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {marksSheet.approval_status !== "PUBLISHED" && (
                  <button
                    onClick={async () => {
                      try {
                        const entries = marksSheet.students
                          .filter((s) => s.marks_obtained !== "" && s.marks_obtained !== null)
                          .map((s) => ({
                            student_id: s.student_id,
                            marks_obtained: Number(s.marks_obtained),
                            remarks: s.remarks,
                          }));
                        const res = await api.post("/api/teacher/marks", {
                          examination_id: marksSheet.examination_id,
                          examination_subject_id: marksSheet.examination_subject_id,
                          submit_for_approval: true,
                          entries,
                        });
                        notify(res.data.message);
                        loadAll();
                        loadMarksSheet(marksSheet.examination_subject_id);
                      } catch (err) {
                        notify(err.response?.data?.detail || "Submission failed.", "error");
                      }
                    }}
                    className="px-6 py-2.5 rounded-xl bg-navy-900 hover:bg-royal-600 text-white text-sm font-bold"
                  >
                    Submit Marks for Admin Approval (PENDING)
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* QUESTION PAPER GENERATOR (ALL 9 QUESTION TYPES) */}
      {tab === "papers" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api.post("/api/teacher/question-papers", {
                  ...qpForm,
                  class_id: Number(qpForm.class_id),
                  subject_id: Number(qpForm.subject_id),
                  examination_id: qpForm.examination_id ? Number(qpForm.examination_id) : null,
                  duration_minutes: Number(qpForm.duration_minutes),
                  total_marks: Number(qpForm.total_marks),
                  questions: qpForm.questions.map((q, i) => ({
                    ...q,
                    marks: Number(q.marks),
                    order_index: i + 1,
                    match_pairs: q.question_type === "MATCH_FOLLOWING" ? q.match_pairs : null,
                    options: q.question_type === "MCQ" ? q.options : [],
                  })),
                });
                notify("Question paper & online test created!");
                loadAll();
              } catch (err) {
                notify(err.response?.data?.detail || "Validation failed.", "error");
              }
            }}
            className="bg-white rounded-2xl p-5 shadow-sm border space-y-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-bold text-navy-900 text-lg">Question Paper & Online Practice Test Builder</h3>
              <div className={`text-xs font-bold px-3 py-1 rounded-full ${Math.abs(sumQuestionMarks - Number(qpForm.total_marks)) < 0.01 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                Sum of Questions: {sumQuestionMarks} / Configured Total: {qpForm.total_marks}
              </div>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
              <input required placeholder="Question Paper Title" value={qpForm.title} onChange={(e) => setQpForm({ ...qpForm, title: e.target.value })} className="sm:col-span-2 rounded-lg border px-3 py-2" />
              <select required value={qpForm.class_id} onChange={(e) => setQpForm({ ...qpForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="">Select Class</option>
                {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <select required value={qpForm.subject_id} onChange={(e) => setQpForm({ ...qpForm, subject_id: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="">Select Subject</option>
                {Array.from(new Map((dash?.assignments || []).map((a) => [a.subject_id, { id: a.subject_id, name: a.subject_name }])).values()).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <input type="number" required placeholder="Duration (mins)" value={qpForm.duration_minutes} onChange={(e) => setQpForm({ ...qpForm, duration_minutes: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input type="number" required placeholder="Total Marks" value={qpForm.total_marks} onChange={(e) => setQpForm({ ...qpForm, total_marks: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Evaluation Scheme" value={qpForm.evaluation_scheme} onChange={(e) => setQpForm({ ...qpForm, evaluation_scheme: e.target.value })} className="sm:col-span-2 rounded-lg border px-3 py-2" />
            </div>

            <div className="space-y-4">
              {qpForm.questions.map((q, qIdx) => (
                <div key={qIdx} className="p-4 rounded-xl bg-slate-50 border space-y-3">
                  <div className="flex flex-wrap gap-2 items-center justify-between">
                    <span className="font-bold text-xs text-navy-900">Question {qIdx + 1}</span>
                    <div className="flex gap-2">
                      <select
                        value={q.question_type}
                        onChange={(e) => {
                          const next = [...qpForm.questions];
                          next[qIdx].question_type = e.target.value;
                          setQpForm({ ...qpForm, questions: next });
                        }}
                        className="rounded-lg border px-2.5 py-1 text-xs"
                      >
                        {QUESTION_TYPES.map((qt) => <option key={qt.value} value={qt.value}>{qt.label}</option>)}
                      </select>
                      <input
                        type="number"
                        step="0.5"
                        value={q.marks}
                        onChange={(e) => {
                          const next = [...qpForm.questions];
                          next[qIdx].marks = e.target.value;
                          setQpForm({ ...qpForm, questions: next });
                        }}
                        className="w-20 rounded-lg border px-2 py-1 text-xs"
                        placeholder="Marks"
                      />
                      {qpForm.questions.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setQpForm({ ...qpForm, questions: qpForm.questions.filter((_, i) => i !== qIdx) })}
                          className="p-1 text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  <textarea
                    required
                    rows={2}
                    placeholder="Enter question text..."
                    value={q.question_text}
                    onChange={(e) => {
                      const next = [...qpForm.questions];
                      next[qIdx].question_text = e.target.value;
                      setQpForm({ ...qpForm, questions: next });
                    }}
                    className="w-full rounded-lg border px-3 py-2 text-sm bg-white"
                  />

                  {q.question_type === "MCQ" && (
                    <div className="grid sm:grid-cols-2 gap-2">
                      {q.options.map((opt, oIdx) => (
                        <div key={opt.option_label} className="flex items-center gap-2">
                          <input
                            type="radio"
                            name={`correct-${qIdx}`}
                            checked={opt.is_correct}
                            onChange={() => {
                              const next = [...qpForm.questions];
                              next[qIdx].options.forEach((o, i) => (o.is_correct = i === oIdx));
                              next[qIdx].correct_answer = opt.option_label;
                              setQpForm({ ...qpForm, questions: next });
                            }}
                          />
                          <input
                            required
                            placeholder={`Option ${opt.option_label}`}
                            value={opt.option_text}
                            onChange={(e) => {
                              const next = [...qpForm.questions];
                              next[qIdx].options[oIdx].option_text = e.target.value;
                              setQpForm({ ...qpForm, questions: next });
                            }}
                            className="flex-1 rounded border px-2.5 py-1 text-xs bg-white"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {q.question_type === "FILL_IN_BLANK" && (
                    <input
                      placeholder="Exact correct answer for auto-evaluation"
                      value={q.correct_answer || ""}
                      onChange={(e) => {
                        const next = [...qpForm.questions];
                        next[qIdx].correct_answer = e.target.value;
                        setQpForm({ ...qpForm, questions: next });
                      }}
                      className="w-full rounded border px-3 py-1.5 text-xs bg-white"
                    />
                  )}

                  {q.question_type === "MATCH_FOLLOWING" && (
                    <div className="space-y-1.5">
                      {q.match_pairs.map((mp, pIdx) => (
                        <div key={pIdx} className="grid grid-cols-2 gap-2">
                          <input
                            placeholder="Column A item"
                            value={mp.left}
                            onChange={(e) => {
                              const next = [...qpForm.questions];
                              next[qIdx].match_pairs[pIdx].left = e.target.value;
                              setQpForm({ ...qpForm, questions: next });
                            }}
                            className="rounded border px-2.5 py-1 text-xs bg-white"
                          />
                          <input
                            placeholder="Column B match"
                            value={mp.right}
                            onChange={(e) => {
                              const next = [...qpForm.questions];
                              next[qIdx].match_pairs[pIdx].right = e.target.value;
                              setQpForm({ ...qpForm, questions: next });
                            }}
                            className="rounded border px-2.5 py-1 text-xs bg-white"
                          />
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => {
                          const next = [...qpForm.questions];
                          next[qIdx].match_pairs.push({ left: "", right: "" });
                          setQpForm({ ...qpForm, questions: next });
                        }}
                        className="text-xs font-semibold text-royal-600"
                      >
                        + Add Match Pair
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-3 justify-between">
              <button
                type="button"
                onClick={() =>
                  setQpForm({
                    ...qpForm,
                    questions: [
                      ...qpForm.questions,
                      {
                        question_type: "TWO_MARK",
                        question_text: "",
                        marks: 2,
                        correct_answer: "",
                        match_pairs: [{ left: "", right: "" }],
                        options: [
                          { option_label: "A", option_text: "", is_correct: true },
                          { option_label: "B", option_text: "", is_correct: false },
                          { option_label: "C", option_text: "", is_correct: false },
                          { option_label: "D", option_text: "", is_correct: false },
                        ],
                      },
                    ],
                  })
                }
                className="inline-flex items-center gap-1 px-4 py-2 rounded-xl border border-royal-600 text-royal-700 text-sm font-semibold"
              >
                <Plus className="w-4 h-4" /> Add Question
              </button>
              <button type="submit" className="px-6 py-2.5 rounded-xl bg-navy-900 text-white text-sm font-bold">
                Save & Publish Question Paper
              </button>
            </div>
          </form>

          <div className="grid sm:grid-cols-2 gap-4">
            {papers.map((p) => (
              <div key={p.id} className="bg-white rounded-2xl p-4 shadow-sm border flex justify-between items-center gap-3">
                <div>
                  <h4 className="font-bold text-navy-900 text-sm">{p.title}</h4>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {p.class_name} • {p.subject_name} • {p.question_count} Questions • {p.total_marks} Marks ({p.duration_minutes} mins)
                  </div>
                </div>
                <button
                  onClick={() => downloadAuthorizedFile(`/api/teacher/question-papers/${p.id}/pdf`, `AK_QuestionPaper_${p.id}.pdf`)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-900 text-white text-xs font-semibold shrink-0"
                >
                  <Download className="w-3.5 h-3.5" /> PDF
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TEST EVALUATION */}
      {tab === "evaluate" && (
        <div className="space-y-4">
          {attempts.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border">No student practice test attempts submitted yet.</div>
          ) : (
            attempts.map((a) => (
              <div key={a.id} className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
                <div className="flex flex-wrap justify-between items-center gap-2">
                  <div>
                    <h4 className="font-bold text-navy-900">{a.paper_title}</h4>
                    <div className="text-xs text-slate-500">{a.student_name} ({a.student_code}) • Status: {a.status} • Score: {a.total_score}/{a.max_score}</div>
                  </div>
                </div>
                <div className="space-y-2">
                  {a.answers.map((ans) => (
                    <div key={ans.answer_id} className="p-3 rounded-xl bg-slate-50 border text-xs space-y-1.5">
                      <div className="font-semibold text-navy-900">[{ans.question_type}] {ans.question_text} (Max: {ans.max_marks})</div>
                      <div>Student Answer: <span className="font-medium text-slate-800">{ans.answer_text || (ans.selected_option_id ? `Option ID #${ans.selected_option_id}` : "No answer")}</span></div>
                      <div className="flex flex-wrap gap-2 items-center">
                        <input
                          type="number"
                          step="0.5"
                          max={ans.max_marks}
                          min={0}
                          placeholder="Marks"
                          defaultValue={ans.marks_awarded ?? ""}
                          onChange={(e) =>
                            setEvalMap({
                              ...evalMap,
                              [ans.answer_id]: { ...(evalMap[ans.answer_id] || {}), marks_awarded: Number(e.target.value) },
                            })
                          }
                          className="w-24 rounded border px-2 py-1 bg-white"
                        />
                        <input
                          placeholder="Teacher comment"
                          defaultValue={ans.teacher_comment || ""}
                          onChange={(e) =>
                            setEvalMap({
                              ...evalMap,
                              [ans.answer_id]: { ...(evalMap[ans.answer_id] || {}), teacher_comment: e.target.value },
                            })
                          }
                          className="flex-1 rounded border px-2.5 py-1 bg-white"
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={async () => {
                    const evaluations = a.answers.map((ans) => ({
                      answer_id: ans.answer_id,
                      marks_awarded: evalMap[ans.answer_id]?.marks_awarded ?? ans.marks_awarded ?? 0,
                      teacher_comment: evalMap[ans.answer_id]?.teacher_comment ?? ans.teacher_comment ?? "",
                    }));
                    try {
                      await api.post(`/api/teacher/test-attempts/${a.id}/evaluate`, { evaluations, teacher_feedback: "Evaluated by teacher." });
                      notify("Evaluation saved & quiz result released to student.");
                      loadAll();
                    } catch (err) {
                      notify(err.response?.data?.detail || "Error saving evaluation.", "error");
                    }
                  }}
                  className="px-4 py-2 rounded-xl bg-emerald-700 text-white text-xs font-bold"
                >
                  Save Review &amp; Release Quiz Result
                </button>
              </div>
            ))
          )}
        </div>
      )}

      {/* ADD STUDENT MODAL (TEACHER) */}
      {studentModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl max-w-xl w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg text-navy-900">Add Student &amp; Generate Unique Login</h3>
              <button onClick={() => setStudentModal(false)}><X className="w-5 h-5" /></button>
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const res = await api.post("/api/teacher/students", {
                    ...studentForm,
                    class_id: Number(studentForm.class_id),
                    student_password: studentForm.student_password || null,
                    parent_password: studentForm.parent_password || null,
                  });
                  setStudentModal(false);
                  setCredsModal(res.data.generated_credentials);
                  notify(`Student ${res.data.student_code} added with unique credentials!`);
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Failed to add student.", "error");
                }
              }}
              className="grid sm:grid-cols-2 gap-3 text-sm"
            >
              <input required placeholder="Student Full Name" value={studentForm.student_name} onChange={(e) => setStudentForm({ ...studentForm, student_name: e.target.value })} className="rounded-lg border px-3 py-2" />
              <select required value={studentForm.class_id} onChange={(e) => setStudentForm({ ...studentForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="">Select Assigned Class</option>
                {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <input required placeholder="Parent / Guardian Name" value={studentForm.parent_name} onChange={(e) => setStudentForm({ ...studentForm, parent_name: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input required placeholder="Parent Phone Number" value={studentForm.parent_phone} onChange={(e) => setStudentForm({ ...studentForm, parent_phone: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Student Phone Number" value={studentForm.student_phone} onChange={(e) => setStudentForm({ ...studentForm, student_phone: e.target.value })} className="rounded-lg border px-3 py-2" />
              <select value={studentForm.gender} onChange={(e) => setStudentForm({ ...studentForm, gender: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
              <input placeholder="Student Password (auto-unique if blank)" value={studentForm.student_password} onChange={(e) => setStudentForm({ ...studentForm, student_password: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Parent Password (auto-unique if blank)" value={studentForm.parent_password} onChange={(e) => setStudentForm({ ...studentForm, parent_password: e.target.value })} className="rounded-lg border px-3 py-2" />
              <div className="sm:col-span-2 flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setStudentModal(false)} className="px-4 py-2 rounded-lg border">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-lg bg-navy-900 text-white font-semibold">Add Student</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SHAREABLE CREDENTIALS MODAL FOR GROUP / PARENTS */}
      {credsModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <div className="flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-navy-900" />
                <h3 className="font-bold text-navy-900">Student &amp; Parent Login Credentials</h3>
              </div>
              <button onClick={() => setCredsModal(null)}><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3 text-xs">
              <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 space-y-1">
                <div className="font-bold text-navy-900 uppercase">Student Portal Login</div>
                <div>Student Name: <strong>{credsModal.student_name}</strong></div>
                <div>Student ID: <strong className="font-mono text-sm">{credsModal.student_username}</strong></div>
                <div>Unique Password: <strong className="font-mono text-sm text-emerald-700">{credsModal.student_password}</strong></div>
              </div>
              <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 space-y-1">
                <div className="font-bold text-navy-900 uppercase">Parent Portal Login</div>
                <div>Parent Phone: <strong className="font-mono text-sm">{credsModal.parent_phone}</strong> (or <strong>{credsModal.parent_username}</strong>)</div>
                <div>Unique Password: <strong className="font-mono text-sm text-emerald-700">{credsModal.parent_password || "(existing parent account)"}</strong></div>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  const text = `AK TUITION PORTAL LOGIN\nStudent: ${credsModal.student_name}\nStudent ID: ${credsModal.student_username}\nStudent Password: ${credsModal.student_password}\nParent Login Phone: ${credsModal.parent_phone}\nParent Password: ${credsModal.parent_password || "(existing account)"}`;
                  navigator.clipboard?.writeText(text);
                  notify("Credentials copied — ready to share in WhatsApp/Group!");
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-navy-900 text-white text-xs font-semibold"
              >
                <Copy className="w-3.5 h-3.5" /> Copy for Group / WhatsApp
              </button>
              <button type="button" onClick={() => setCredsModal(null)} className="px-4 py-2 rounded-lg border text-xs font-semibold">Done</button>
            </div>
          </div>
        </div>
      )}
    </PortalLayout>
  );
}
