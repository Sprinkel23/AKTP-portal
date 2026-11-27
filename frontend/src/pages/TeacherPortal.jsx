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
  IndianRupee,
  HelpCircle,
  Landmark,
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
  const [allClasses, setAllClasses] = useState([]);
  const [allSubjects, setAllSubjects] = useState([]);
  const [absentAlerts, setAbsentAlerts] = useState([]);
  const [studentClassFilter, setStudentClassFilter] = useState("");
  const [focusedStudentId, setFocusedStudentId] = useState("");
  const [matrixSubjectFilter, setMatrixSubjectFilter] = useState("");
  const [feeData, setFeeData] = useState({ students: [], collections: [] });
  const [feeForm, setFeeForm] = useState({
    student_id: "",
    total_fees: "",
    amount: "",
    payment_mode: "CASH",
    payment_date: new Date().toISOString().slice(0, 10),
    reference_number: "",
    remarks: "",
  });
  const [salaryData, setSalaryData] = useState({ bank_details: {}, payouts: [] });
  const [bankForm, setBankForm] = useState({
    bank_account_holder: "",
    bank_name: "",
    bank_account_number: "",
    bank_ifsc: "",
    upi_id: "",
  });
  const [salReqForm, setSalReqForm] = useState({
    month_label: new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" }),
    requested_amount: "",
    remarks: "",
  });
  const [toast, setToast] = useState({ type: "", text: "" });

  // Attendance state
  const [attClassId, setAttClassId] = useState("");
  const [attDate, setAttDate] = useState(new Date().toISOString().slice(0, 10));
  const [attRows, setAttRows] = useState([]);

  // Marks state
  const [marksMode, setMarksMode] = useState("matrix"); // matrix | direct | existing
  const [selectedExamSubjId, setSelectedExamSubjId] = useState("");
  const [marksSheet, setMarksSheet] = useState(null);
  const [matrixCfg, setMatrixCfg] = useState({
    class_id: "",
    examination_id: "",
    exam_name: "",
    exam_type: "UNIT_TEST",
    exam_date: new Date().toISOString().slice(0, 10),
  });
  const [matrixSubjects, setMatrixSubjects] = useState([]);
  const [matrixRows, setMatrixRows] = useState([]);
  const [directExam, setDirectExam] = useState({
    exam_name: "",
    exam_type: "RE_EXAMINATION",
    class_id: "",
    subject_id: "",
    exam_date: new Date().toISOString().slice(0, 10),
    max_marks: 100,
  });
  const [directEntries, setDirectEntries] = useState([]);

  // Question Paper state
  const [autoTopic, setAutoTopic] = useState("");
  const [qpForm, setQpForm] = useState({
    title: "",
    class_id: "",
    subject_id: "",
    examination_id: "",
    duration_minutes: 60,
    total_marks: 10,
    evaluation_scheme: "Stepwise marking as per AK Tuition rubric.",
    instructions: "Answer all questions neatly.",
    watermark_text: "AK TUITION",
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
      const [dRes, clsRes, sRes, exRes, qpRes, attHistRes, atmpRes, feeRes, salRes] = await Promise.all([
        api.get("/api/teacher/dashboard"),
        api.get("/api/teacher/classes"),
        api.get("/api/teacher/students"),
        api.get("/api/teacher/examinations"),
        api.get("/api/teacher/question-papers"),
        api.get("/api/teacher/attendance/history"),
        api.get("/api/teacher/test-attempts"),
        api.get("/api/teacher/fees/collections").catch(() => ({ data: { students: [], collections: [] } })),
        api.get("/api/teacher/salary").catch(() => ({ data: { bank_details: {}, payouts: [] } })),
      ]);
      setDash(dRes.data);
      const loadedClasses = clsRes.data.classes || [];
      setAllClasses(loadedClasses);
      setAllSubjects(clsRes.data.subjects || []);
      setStudents(sRes.data);
      setExams(exRes.data);
      setPapers(qpRes.data);
      setAttHistory(attHistRes.data);
      setAttempts(atmpRes.data);
      setFeeData(feeRes.data || { students: [], collections: [] });
      setSalaryData(salRes.data || { bank_details: {}, payouts: [] });
      if (salRes.data?.bank_details) {
        setBankForm((prev) => ({ ...prev, ...salRes.data.bank_details }));
      }
      if (!matrixCfg.class_id && loadedClasses.length > 0) {
        const firstCid = String(loadedClasses[0].id);
        setMatrixCfg((prev) => ({
          ...prev,
          class_id: firstCid,
          exam_name: prev.exam_name || `Assessment ${new Date().toISOString().slice(0, 10)}`,
        }));
        loadAllSubjectsMatrix(firstCid, "");
      }
    } catch (err) {
      notify(err.response?.data?.detail || "Error loading teacher portal.", "error");
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const uniqueClasses = allClasses.length
    ? allClasses.map((c) => ({ id: c.id, name: `${c.name} (${c.section})` }))
    : Array.from(new Map((dash?.assignments || []).map((a) => [a.class_id, { id: a.class_id, name: a.class_name }])).values());

  const loadAllSubjectsMatrix = async (classId, examId = "") => {
    if (!classId) {
      setMatrixSubjects([]);
      setMatrixRows([]);
      return;
    }
    try {
      const res = await api.get(
        `/api/teacher/marks/matrix?class_id=${classId}${examId ? `&examination_id=${examId}` : ""}`
      );
      setMatrixSubjects(
        (res.data.subjects || []).map((s) => ({
          ...s,
          included: !s.is_published,
        }))
      );
      setMatrixRows(
        (res.data.students || []).map((st) => ({
          ...st,
          scores: { ...(st.scores || {}) },
        }))
      );
    } catch (err) {
      notify(err.response?.data?.detail || "Could not load all-subjects marks sheet.", "error");
    }
  };

  const handleAutoCreatePaper = () => {
    const total = Math.max(1, Math.round(Number(qpForm.total_marks) || 20));
    const subjObj = allSubjects.find((s) => String(s.id) === String(qpForm.subject_id));
    const topicLabel = (autoTopic || subjObj?.name || "Core Concepts").trim();
    const generated = [];
    let remaining = total;

    // 1. Add up to 4 MCQs (1 mark each) when total >= 5
    const mcqCount = Math.min(4, Math.floor(total * 0.2));
    for (let i = 1; i <= mcqCount && remaining >= 1; i++) {
      generated.push({
        question_type: "MCQ",
        question_text: `Choose the correct principle regarding ${topicLabel} (Concept ${i}).`,
        marks: 1,
        correct_answer: "A",
        match_pairs: [{ left: "", right: "" }],
        options: [
          { option_label: "A", option_text: `Standard property of ${topicLabel}`, is_correct: true },
          { option_label: "B", option_text: "Inverse relation only", is_correct: false },
          { option_label: "C", option_text: "Undefined condition", is_correct: false },
          { option_label: "D", option_text: "None of the above", is_correct: false },
        ],
      });
      remaining -= 1;
    }

    // 2. Add Fill in the Blanks (1 mark each)
    const fibCount = Math.min(2, Math.floor(remaining * 0.2));
    for (let i = 1; i <= fibCount && remaining >= 1; i++) {
      generated.push({
        question_type: "FILL_IN_BLANK",
        question_text: `Fill in the blank: The fundamental law of ${topicLabel} states that ________ (${i}).`,
        marks: 1,
        correct_answer: topicLabel,
        match_pairs: [{ left: "", right: "" }],
        options: [],
      });
      remaining -= 1;
    }

    // 3. Allocate 5-mark and 2-mark / 1-mark questions cleanly to match total_marks exactly
    let sec5 = 1;
    while (remaining >= 7) {
      generated.push({
        question_type: "FIVE_MARK",
        question_text: `Explain in detail with neat steps/derivation on ${topicLabel} — Section Question ${sec5++}.`,
        marks: 5,
        correct_answer: "",
        match_pairs: [{ left: "", right: "" }],
        options: [],
      });
      remaining -= 5;
    }
    let sec2 = 1;
    while (remaining >= 2) {
      generated.push({
        question_type: "TWO_MARK",
        question_text: `Define and illustrate key points on ${topicLabel} (Short Answer ${sec2++}).`,
        marks: 2,
        correct_answer: "",
        match_pairs: [{ left: "", right: "" }],
        options: [],
      });
      remaining -= 2;
    }
    if (remaining === 1) {
      generated.push({
        question_type: "ONE_MARK",
        question_text: `State one key application or formula of ${topicLabel}.`,
        marks: 1,
        correct_answer: "",
        match_pairs: [{ left: "", right: "" }],
        options: [],
      });
      remaining -= 1;
    }

    setQpForm((prev) => ({
      ...prev,
      title: prev.title.trim() ? prev.title : `${subjObj?.name || "Subject"} — ${topicLabel} Question Paper`,
      questions: generated,
    }));
    notify(`Auto-created ${generated.length} balanced questions totaling ${total} marks!`);
  };

  const loadAttendanceSheet = async () => {
    if (!attDate) return;
    try {
      const clsParam = attClassId ? `&class_id=${attClassId}` : "";
      const res = await api.get(`/api/teacher/attendance?attendance_date=${attDate}${clsParam}`);
      setAttRows(res.data.students);
    } catch (err) {
      notify(err.response?.data?.detail || "Could not load attendance sheet.", "error");
    }
  };

  useEffect(() => {
    if (tab === "attendance") {
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
    { id: "students", label: "All Students", icon: Users },
    { id: "attendance", label: "Daily Attendance", icon: ClipboardCheck },
    { id: "marks", label: "Marks Entry", icon: FileEdit },
    { id: "fees", label: "Student Fees", icon: IndianRupee },
    { id: "salary", label: "Salary & Bank", icon: Landmark },
    { id: "papers", label: "Question Papers", icon: FilePlus2 },
    { id: "evaluate", label: "Test Evaluation", icon: CheckCircle },
    { id: "guide", label: "How to Use", icon: HelpCircle },
  ];

  const openMarksForStudent = async (st) => {
    const cid = String(st.class_id || "");
    const todayLabel = `Assessment ${new Date().toISOString().slice(0, 10)}`;
    setMarksMode("matrix");
    setFocusedStudentId(String(st.id));
    setMatrixSubjectFilter("");
    setMatrixCfg((prev) => ({
      ...prev,
      class_id: cid,
      examination_id: "",
      exam_name: prev.exam_name.trim() ? prev.exam_name : todayLabel,
    }));
    await loadAllSubjectsMatrix(cid, "");
    setTab("marks");
  };

  const openFeeForStudent = (st) => {
    const fRec = (feeData.students || []).find((x) => String(x.student_id) === String(st.id));
    setFeeForm((prev) => ({
      ...prev,
      student_id: String(st.id),
      total_fees: fRec && fRec.total_fees > 0 ? String(fRec.total_fees) : "",
    }));
    setTab("fees");
  };

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
            <div className="flex flex-wrap items-center gap-3">
              <div className="font-bold text-navy-900">All Students (Unified Classes) &amp; Academic Summary</div>
              <select
                value={studentClassFilter}
                onChange={(e) => setStudentClassFilter(e.target.value)}
                className="rounded-lg border px-2.5 py-1.5 text-xs font-semibold"
              >
                <option value="">All Classes Together</option>
                {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
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
                  <th className="p-3 text-left">Name (Click to Enter Marks)</th>
                  <th className="p-3 text-left">Class</th>
                  <th className="p-3 text-center">Attendance %</th>
                  <th className="p-3 text-left">Recent Marks</th>
                  <th className="p-3 text-right">Quick Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(studentClassFilter ? students.filter((s) => String(s.class_id) === String(studentClassFilter)) : students).map((s) => (
                  <tr key={s.id} className="hover:bg-blue-50/40 transition">
                    <td className="p-3 font-mono font-bold text-royal-700">{s.student_code}</td>
                    <td className="p-3 font-semibold">
                      <button
                        type="button"
                        onClick={() => openMarksForStudent(s)}
                        className="text-left text-navy-900 hover:text-royal-700 hover:underline font-bold"
                        title="Click student name to enter marks"
                      >
                        {s.student_name}
                      </button>
                    </td>
                    <td className="p-3">{s.class_name} ({s.section})</td>
                    <td className="p-3 text-center font-bold">{s.attendance_percentage}% ({s.present_days}/{s.working_days})</td>
                    <td className="p-3 text-xs space-y-1">
                      {s.recent_marks.map((m, idx) => (
                        <div key={idx}>{m.exam} • {m.subject}: <strong>{m.marks_obtained}/{m.max_marks}</strong> ({m.status})</div>
                      ))}
                    </td>
                    <td className="p-3 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => openMarksForStudent(s)}
                        className="px-2.5 py-1 rounded-lg bg-navy-900 hover:bg-royal-600 text-white text-xs font-bold"
                      >
                        Enter Marks
                      </button>
                      <button
                        type="button"
                        onClick={() => openFeeForStudent(s)}
                        className="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold"
                      >
                        Collect Fee
                      </button>
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
                <label className="block text-xs font-semibold text-slate-600 mb-1">Filter Class (Optional)</label>
                <select value={attClassId} onChange={(e) => setAttClassId(e.target.value)} className="rounded-lg border px-3 py-2 text-sm">
                  <option value="">All Classes Together</option>
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
                    <th className="p-2.5 text-left">Class</th>
                    <th className="p-2.5 text-center">Status</th>
                    <th className="p-2.5 text-left">Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {attRows.map((row, idx) => (
                    <tr key={row.student_id}>
                      <td className="p-2.5 font-mono font-bold text-royal-700">{row.student_code}</td>
                      <td className="p-2.5 font-medium">{row.student_name}</td>
                      <td className="p-2.5 text-xs text-slate-600">{row.class_name} ({row.section})</td>
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
                    class_id: attClassId ? Number(attClassId) : null,
                    attendance_date: attDate,
                    entries: attRows.map((r) => ({ student_id: r.student_id, status: r.status, remarks: r.remarks })),
                  });
                  setAbsentAlerts(res.data.absent_alerts || []);
                  notify(res.data.message);
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Failed to save attendance.", "error");
                }
              }}
              className="px-6 py-2.5 rounded-xl bg-navy-900 text-white text-sm font-bold"
            >
              Save Attendance &amp; Trigger Absence Alerts
            </button>

            {absentAlerts.length > 0 && (
              <div className="mt-4 p-4 rounded-xl bg-amber-50 border border-amber-300 space-y-2">
                <div className="font-bold text-amber-950 text-sm">
                  Absence Alerts Triggered for Registered Numbers ({absentAlerts.length})
                </div>
                <p className="text-xs text-amber-800">
                  Send instant notification to the registered WhatsApp or SMS number for each absent student:
                </p>
                <div className="space-y-2">
                  {absentAlerts.map((al, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-white border flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div>
                        <strong>{al.student_name}</strong> ({al.student_code}, {al.class_name}) • <span className="uppercase">{al.target}</span>: <strong className="font-mono">{al.phone}</strong>
                        <span className={`ml-2 px-1.5 py-0.5 rounded font-bold ${al.status === "SENT" ? "bg-emerald-100 text-emerald-800" : "bg-blue-50 text-royal-700"}`}>
                          {al.status === "SENT" ? "AUTO SENT" : "READY"}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        {al.whatsapp_url && (
                          <a href={al.whatsapp_url} target="_blank" rel="noreferrer" className="px-3 py-1 rounded-lg bg-emerald-600 text-white font-bold">
                            Send WhatsApp
                          </a>
                        )}
                        {al.sms_url && (
                          <a href={al.sms_url} className="px-3 py-1 rounded-lg bg-navy-900 text-white font-bold">
                            Send SMS
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-navy-900">Examination &amp; Re-Examination Marks Entry</h3>
                <p className="text-xs text-slate-600">
                  Enter <strong>ALL Subjects at once</strong> in one full-class spreadsheet, OR enter a single Exam / Re-Exam subject. Submitted marks enter <strong>PENDING</strong> status for Admin approval.
                </p>
              </div>
              <div className="inline-flex flex-wrap rounded-xl border p-1 bg-slate-50 text-xs font-bold gap-1">
                <button
                  type="button"
                  onClick={() => setMarksMode("matrix")}
                  className={`px-3 py-1.5 rounded-lg ${marksMode === "matrix" ? "bg-navy-900 text-white" : "text-slate-600"}`}
                >
                  All Subjects at Once (One Teacher)
                </button>
                <button
                  type="button"
                  onClick={() => setMarksMode("direct")}
                  className={`px-3 py-1.5 rounded-lg ${marksMode === "direct" ? "bg-navy-900 text-white" : "text-slate-600"}`}
                >
                  Type Exam / Re-Exam
                </button>
                <button
                  type="button"
                  onClick={() => setMarksMode("existing")}
                  className={`px-3 py-1.5 rounded-lg ${marksMode === "existing" ? "bg-navy-900 text-white" : "text-slate-600"}`}
                >
                  Select Scheduled Subject
                </button>
              </div>
            </div>

            {marksMode === "matrix" ? (
              <div className="space-y-4 p-4 rounded-xl bg-slate-50 border">
                <div className="grid sm:grid-cols-2 lg:grid-cols-6 gap-3 text-sm">
                  <select
                    value={matrixCfg.class_id}
                    onChange={(e) => {
                      const cid = e.target.value;
                      setFocusedStudentId("");
                      setMatrixCfg({ ...matrixCfg, class_id: cid, examination_id: "" });
                      loadAllSubjectsMatrix(cid, "");
                    }}
                    className="rounded-lg border px-3 py-2 bg-white font-semibold"
                  >
                    <option value="">1. Select Class</option>
                    {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                  <select
                    value={matrixCfg.examination_id}
                    onChange={(e) => {
                      const exId = e.target.value;
                      setMatrixCfg({ ...matrixCfg, examination_id: exId });
                      if (matrixCfg.class_id) loadAllSubjectsMatrix(matrixCfg.class_id, exId);
                    }}
                    className="rounded-lg border px-3 py-2 bg-white"
                  >
                    <option value="">2a. New Exam / Auto-Save</option>
                    {exams
                      .filter((ex) => !matrixCfg.class_id || String(ex.class_id) === String(matrixCfg.class_id))
                      .map((ex) => (
                        <option key={ex.id} value={ex.id}>
                          {ex.name} ({ex.class_name})
                        </option>
                      ))}
                  </select>
                  <input
                    disabled={Boolean(matrixCfg.examination_id)}
                    placeholder="2b. Or Exam / Re-Exam Name"
                    value={matrixCfg.exam_name}
                    onChange={(e) => setMatrixCfg({ ...matrixCfg, exam_name: e.target.value })}
                    className="rounded-lg border px-3 py-2 bg-white disabled:bg-slate-100"
                  />
                  <select
                    value={matrixSubjectFilter}
                    onChange={(e) => {
                      const val = e.target.value;
                      setMatrixSubjectFilter(val);
                      setMatrixSubjects((prev) =>
                        prev.map((s) => ({
                          ...s,
                          included: !s.is_published && (!val || String(s.subject_id) === String(val)),
                        }))
                      );
                    }}
                    className="rounded-lg border px-3 py-2 bg-white font-semibold text-navy-900"
                  >
                    <option value="">Subject: All Subjects (Default)</option>
                    {matrixSubjects.map((s) => (
                      <option key={s.subject_id} value={s.subject_id}>
                        Subject: {s.name}
                      </option>
                    ))}
                  </select>
                  <select
                    disabled={Boolean(matrixCfg.examination_id)}
                    value={matrixCfg.exam_type}
                    onChange={(e) => setMatrixCfg({ ...matrixCfg, exam_type: e.target.value })}
                    className="rounded-lg border px-3 py-2 bg-white disabled:bg-slate-100"
                  >
                    <option value="UNIT_TEST">Unit Test</option>
                    <option value="MID_TERM">Mid-Term Exam</option>
                    <option value="FINAL_EXAM">Final Exam</option>
                    <option value="RE_EXAMINATION">Re-Examination</option>
                    <option value="PRACTICE_TEST">Practice Test</option>
                  </select>
                  <input
                    type="date"
                    value={matrixCfg.exam_date}
                    onChange={(e) => setMatrixCfg({ ...matrixCfg, exam_date: e.target.value })}
                    className="rounded-lg border px-3 py-2 bg-white text-xs"
                  />
                </div>

                {focusedStudentId && (
                  <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-blue-50 border border-blue-200 text-xs">
                    <span>
                      Showing selected student:{" "}
                      <strong className="text-navy-900">
                        {matrixRows.find((r) => String(r.student_id) === String(focusedStudentId))?.student_name || "Selected Student"}
                      </strong>{" "}
                      — enter marks by subject below and save directly.
                    </span>
                    <button
                      type="button"
                      onClick={() => setFocusedStudentId("")}
                      className="px-2.5 py-1 rounded bg-navy-900 text-white font-bold"
                    >
                      Show Full Class Instead
                    </button>
                  </div>
                )}

                {matrixSubjects.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-bold text-navy-900">Subjects Included:</span>
                    {matrixSubjects.map((subj, idx) => (
                      <label
                        key={subj.subject_id}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border cursor-pointer ${
                          subj.is_published
                            ? "bg-emerald-50 border-emerald-300 text-emerald-800"
                            : subj.included
                            ? "bg-navy-900 text-white border-navy-900"
                            : "bg-white text-slate-600 border-slate-300"
                        }`}
                      >
                        <input
                          type="checkbox"
                          disabled={subj.is_published}
                          checked={subj.included}
                          onChange={(e) => {
                            const next = [...matrixSubjects];
                            next[idx].included = e.target.checked;
                            setMatrixSubjects(next);
                          }}
                        />
                        <span>{subj.name}{subj.is_published ? " (Published)" : ""}</span>
                      </label>
                    ))}
                  </div>
                )}

                {matrixRows.length > 0 && matrixSubjects.some((s) => s.included) ? (
                  <div className="space-y-3">
                    {focusedStudentId ? (() => {
                      const targetRow = matrixRows.find((r) => String(r.student_id) === String(focusedStudentId));
                      const rIdx = matrixRows.findIndex((r) => String(r.student_id) === String(focusedStudentId));
                      if (!targetRow || rIdx < 0) return null;
                      const activeCols = matrixSubjects.filter((s) => s.included);
                      let sumObt = 0;
                      let sumMax = 0;
                      activeCols.forEach((col) => {
                        const v = targetRow.scores?.[col.subject_id];
                        if (v !== "" && v !== undefined && v !== null && !Number.isNaN(Number(v))) {
                          sumObt += Number(v);
                          sumMax += Number(col.max_marks) || 0;
                        }
                      });
                      const totalPct = sumMax ? ((sumObt / sumMax) * 100).toFixed(1) : "0.0";
                      return (
                        <div className="space-y-3">
                          <div className="bg-white border border-slate-300 rounded-lg overflow-hidden">
                            <div className="bg-[#0A2463] text-white px-4 py-2.5 flex flex-wrap items-center justify-between text-xs font-bold">
                              <span>
                                SUBJECT-WISE MARKS ENTRY — {targetRow.student_code} • {targetRow.student_name}
                              </span>
                              <span className="text-gold-400">
                                Total: {sumObt} / {sumMax} ({totalPct}%)
                              </span>
                            </div>
                            <table className="w-full text-xs">
                              <thead className="bg-slate-100 text-slate-700 uppercase border-b">
                                <tr>
                                  <th className="p-3 text-left">Subject</th>
                                  <th className="p-3 text-center">Max Marks</th>
                                  <th className="p-3 text-center">Marks Obtained</th>
                                  <th className="p-3 text-center">% Score</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y">
                                {activeCols.map((col) => {
                                  const sIdx = matrixSubjects.findIndex((x) => x.subject_id === col.subject_id);
                                  const rawVal = targetRow.scores?.[col.subject_id] ?? "";
                                  const pctCell =
                                    rawVal !== "" && Number(col.max_marks) > 0
                                      ? `${((Number(rawVal) / Number(col.max_marks)) * 100).toFixed(1)}%`
                                      : "-";
                                  return (
                                    <tr key={col.subject_id} className="hover:bg-slate-50">
                                      <td className="p-3 font-bold text-navy-900">
                                        {col.name} <span className="text-slate-400 font-mono">({col.code})</span>
                                      </td>
                                      <td className="p-3 text-center">
                                        <input
                                          type="number"
                                          min={1}
                                          value={col.max_marks}
                                          onChange={(e) => {
                                            const next = [...matrixSubjects];
                                            next[sIdx].max_marks = e.target.value;
                                            setMatrixSubjects(next);
                                          }}
                                          className="w-24 rounded border border-slate-300 px-2 py-1 text-center font-semibold"
                                        />
                                      </td>
                                      <td className="p-3 text-center">
                                        <input
                                          type="number"
                                          min={0}
                                          max={Number(col.max_marks) || 100}
                                          step="0.5"
                                          placeholder="Enter marks"
                                          value={rawVal}
                                          onChange={(e) => {
                                            const next = [...matrixRows];
                                            next[rIdx].scores = {
                                              ...(next[rIdx].scores || {}),
                                              [col.subject_id]: e.target.value,
                                            };
                                            setMatrixRows(next);
                                          }}
                                          className="w-32 rounded border-2 border-[#0A2463]/40 focus:border-[#0A2463] px-2.5 py-1.5 text-center font-bold text-sm"
                                        />
                                      </td>
                                      <td className="p-3 text-center font-bold text-royal-700">{pctCell}</td>
                                    </tr>
                                  );
                                })}
                              </tbody>
                            </table>
                          </div>
                          <input
                            value={targetRow.remarks || ""}
                            onChange={(e) => {
                              const next = [...matrixRows];
                              next[rIdx].remarks = e.target.value;
                              setMatrixRows(next);
                            }}
                            placeholder="Optional overall teacher remarks for this student..."
                            className="w-full rounded border border-slate-300 px-3 py-2 text-xs bg-white"
                          />
                        </div>
                      );
                    })() : (
                    <div className="overflow-x-auto bg-white rounded-lg border border-slate-300">
                      <table className="w-full text-xs">
                        <thead className="bg-navy-900 text-white uppercase">
                          <tr>
                            <th className="p-2.5 text-left">ID</th>
                            <th className="p-2.5 text-left min-w-[140px]">Student Name</th>
                            {matrixSubjects.map((subj, sIdx) =>
                              subj.included ? (
                                <th key={subj.subject_id} className="p-2 text-center min-w-[105px]">
                                  <div>{subj.name}</div>
                                  <div className="flex items-center justify-center gap-1 mt-1 font-normal normal-case">
                                    <span className="text-[10px] text-gold-400">Max:</span>
                                    <input
                                      type="number"
                                      min={1}
                                      value={subj.max_marks}
                                      onChange={(e) => {
                                        const next = [...matrixSubjects];
                                        next[sIdx].max_marks = e.target.value;
                                        setMatrixSubjects(next);
                                      }}
                                      className="w-14 rounded px-1 py-0.5 text-center text-navy-900 text-[11px] font-bold"
                                    />
                                  </div>
                                </th>
                              ) : null
                            )}
                            <th className="p-2.5 text-center">Total / %</th>
                            <th className="p-2.5 text-left min-w-[120px]">Remarks</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {matrixRows.map((st, rIdx) => {
                            const activeCols = matrixSubjects.filter((s) => s.included);
                            let rowObt = 0;
                            let rowMax = 0;
                            activeCols.forEach((col) => {
                              const v = st.scores?.[col.subject_id];
                              if (v !== "" && v !== undefined && v !== null && !Number.isNaN(Number(v))) {
                                rowObt += Number(v);
                                rowMax += Number(col.max_marks) || 0;
                              }
                            });
                            const rowPct = rowMax ? ((rowObt / rowMax) * 100).toFixed(1) : "0.0";
                            return (
                              <tr key={st.student_id}>
                                <td className="p-2 font-mono font-bold text-royal-700">{st.student_code}</td>
                                <td className="p-2 font-medium">{st.student_name}</td>
                                {activeCols.map((col) => (
                                  <td key={col.subject_id} className="p-2 text-center">
                                    <input
                                      type="number"
                                      min={0}
                                      max={Number(col.max_marks) || 100}
                                      step="0.5"
                                      value={st.scores?.[col.subject_id] ?? ""}
                                      onChange={(e) => {
                                        const next = [...matrixRows];
                                        next[rIdx].scores = {
                                          ...(next[rIdx].scores || {}),
                                          [col.subject_id]: e.target.value,
                                        };
                                        setMatrixRows(next);
                                      }}
                                      className="w-20 rounded border px-1.5 py-1 text-center font-semibold"
                                    />
                                  </td>
                                ))}
                                <td className="p-2 text-center font-bold text-navy-900 whitespace-nowrap">
                                  {rowObt} / {rowMax} <span className="text-royal-700">({rowPct}%)</span>
                                </td>
                                <td className="p-2">
                                  <input
                                    value={st.remarks || ""}
                                    onChange={(e) => {
                                      const next = [...matrixRows];
                                      next[rIdx].remarks = e.target.value;
                                      setMatrixRows(next);
                                    }}
                                    placeholder="Remarks"
                                    className="w-full rounded border px-2 py-1 text-xs"
                                  />
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    )}
                    <div className="flex flex-wrap gap-3">
                      <button
                        type="button"
                        onClick={async () => {
                          if (!matrixCfg.class_id) {
                            notify("Select a class first.", "error");
                            return;
                          }
                          const autoName = matrixCfg.exam_name.trim() || `Assessment ${new Date().toISOString().slice(0, 10)}`;
                          const selectedCols = matrixSubjects
                            .filter((s) => s.included && !s.is_published)
                            .map((s) => ({ subject_id: s.subject_id, max_marks: Number(s.max_marks) || 100 }));
                          const targetRows = focusedStudentId
                            ? matrixRows.filter((r) => String(r.student_id) === String(focusedStudentId))
                            : matrixRows;
                          const entries = targetRows
                            .map((r) => {
                              const scores = {};
                              selectedCols.forEach((col) => {
                                const raw = r.scores?.[col.subject_id];
                                if (raw !== "" && raw !== undefined && raw !== null) {
                                  scores[col.subject_id] = Number(raw);
                                }
                              });
                              return { student_id: r.student_id, scores, remarks: r.remarks || null };
                            })
                            .filter((r) => Object.keys(r.scores).length > 0);
                          if (!entries.length) {
                            notify("Enter at least one student mark across the grid.", "error");
                            return;
                          }
                          try {
                            const res = await api.post("/api/teacher/marks/bulk-all-subjects", {
                              class_id: Number(matrixCfg.class_id),
                              examination_id: matrixCfg.examination_id ? Number(matrixCfg.examination_id) : null,
                              exam_name: matrixCfg.examination_id ? null : autoName,
                              exam_type: matrixCfg.exam_type,
                              exam_date: matrixCfg.exam_date || null,
                              submit_for_approval: false,
                              subjects: selectedCols,
                              entries,
                            });
                            notify(`Saved ${res.data.marks_saved} subject mark(s) for '${res.data.exam_name}'!`);
                            loadAll();
                            loadAllSubjectsMatrix(matrixCfg.class_id, res.data.examination_id);
                            setMatrixCfg((prev) => ({ ...prev, examination_id: String(res.data.examination_id), exam_name: "" }));
                          } catch (err) {
                            notify(err.response?.data?.detail || "Failed to save marks.", "error");
                          }
                        }}
                        className="px-5 py-2.5 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white text-sm font-bold"
                      >
                        Save Marks (Default Subject Sheet)
                      </button>
                      <button
                        type="button"
                        onClick={async () => {
                          if (!matrixCfg.class_id) {
                            notify("Select a class first.", "error");
                            return;
                          }
                          const autoName = matrixCfg.exam_name.trim() || `Assessment ${new Date().toISOString().slice(0, 10)}`;
                          const selectedCols = matrixSubjects
                            .filter((s) => s.included && !s.is_published)
                            .map((s) => ({ subject_id: s.subject_id, max_marks: Number(s.max_marks) || 100 }));
                          const targetRows = focusedStudentId
                            ? matrixRows.filter((r) => String(r.student_id) === String(focusedStudentId))
                            : matrixRows;
                          const entries = targetRows
                            .map((r) => {
                              const scores = {};
                              selectedCols.forEach((col) => {
                                const raw = r.scores?.[col.subject_id];
                                if (raw !== "" && raw !== undefined && raw !== null) {
                                  scores[col.subject_id] = Number(raw);
                                }
                              });
                              return { student_id: r.student_id, scores, remarks: r.remarks || null };
                            })
                            .filter((r) => Object.keys(r.scores).length > 0);
                          if (!entries.length) {
                            notify("Enter at least one student mark across the grid.", "error");
                            return;
                          }
                          try {
                            const res = await api.post("/api/teacher/marks/bulk-all-subjects", {
                              class_id: Number(matrixCfg.class_id),
                              examination_id: matrixCfg.examination_id ? Number(matrixCfg.examination_id) : null,
                              exam_name: matrixCfg.examination_id ? null : autoName,
                              exam_type: matrixCfg.exam_type,
                              exam_date: matrixCfg.exam_date || null,
                              submit_for_approval: true,
                              subjects: selectedCols,
                              entries,
                            });
                            notify(res.data.message);
                            loadAll();
                            loadAllSubjectsMatrix(matrixCfg.class_id, res.data.examination_id);
                            setMatrixCfg((prev) => ({ ...prev, examination_id: String(res.data.examination_id), exam_name: "" }));
                          } catch (err) {
                            notify(err.response?.data?.detail || "Failed to submit all-subject marks.", "error");
                          }
                        }}
                        className="px-6 py-2.5 rounded-xl bg-navy-900 hover:bg-royal-600 text-white text-sm font-bold"
                      >
                        Save &amp; Submit ALL Subject Marks for Admin Approval
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">
                    Select a Class above to load all active students and enter every subject mark in one single spreadsheet.
                  </p>
                )}
              </div>
            ) : marksMode === "direct" ? (
              <div className="space-y-4 p-4 rounded-xl bg-slate-50 border">
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
                  <input
                    placeholder="Type Exam / Re-Examination Name (e.g. Maths Re-Exam)"
                    value={directExam.exam_name}
                    onChange={(e) => setDirectExam({ ...directExam, exam_name: e.target.value })}
                    className="sm:col-span-2 rounded-lg border px-3 py-2 bg-white"
                  />
                  <select
                    value={directExam.exam_type}
                    onChange={(e) => setDirectExam({ ...directExam, exam_type: e.target.value })}
                    className="rounded-lg border px-3 py-2 bg-white"
                  >
                    <option value="RE_EXAMINATION">Re-Examination</option>
                    <option value="UNIT_TEST">Unit Test</option>
                    <option value="MID_TERM">Mid-Term Examination</option>
                    <option value="FINAL_EXAM">Final Examination</option>
                    <option value="PRACTICE_TEST">Practice Test</option>
                  </select>
                  <select
                    value={directExam.class_id}
                    onChange={(e) => {
                      const cid = e.target.value;
                      setDirectExam({ ...directExam, class_id: cid });
                      const clsStudents = students.filter((s) => String(s.class_id) === String(cid));
                      setDirectEntries(clsStudents.map((s) => ({
                        student_id: s.id,
                        student_code: s.student_code,
                        student_name: s.student_name,
                        marks_obtained: "",
                        remarks: "",
                      })));
                    }}
                    className="rounded-lg border px-3 py-2 bg-white"
                  >
                    <option value="">Select Class</option>
                    {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                  <select
                    value={directExam.subject_id}
                    onChange={(e) => setDirectExam({ ...directExam, subject_id: e.target.value })}
                    className="rounded-lg border px-3 py-2 bg-white"
                  >
                    <option value="">Select Subject</option>
                    {(allSubjects.length
                      ? allSubjects
                      : Array.from(new Map((dash?.assignments || []).map((a) => [a.subject_id, { id: a.subject_id, name: a.subject_name }])).values())
                    ).map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <input
                      type="date"
                      value={directExam.exam_date}
                      onChange={(e) => setDirectExam({ ...directExam, exam_date: e.target.value })}
                      className="w-1/2 rounded-lg border px-2.5 py-2 bg-white text-xs"
                    />
                    <input
                      type="number"
                      min={1}
                      placeholder="Max Marks"
                      value={directExam.max_marks}
                      onChange={(e) => setDirectExam({ ...directExam, max_marks: e.target.value })}
                      className="w-1/2 rounded-lg border px-2.5 py-2 bg-white"
                    />
                  </div>
                </div>

                {directEntries.length > 0 && (
                  <div className="space-y-3">
                    <div className="overflow-x-auto bg-white rounded-xl border">
                      <table className="w-full text-sm">
                        <thead className="bg-navy-900 text-white text-xs uppercase">
                          <tr>
                            <th className="p-2.5 text-left">Student ID</th>
                            <th className="p-2.5 text-left">Name</th>
                            <th className="p-2.5 text-center">Marks Obtained (Max {directExam.max_marks})</th>
                            <th className="p-2.5 text-left">Remarks</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {directEntries.map((st, idx) => (
                            <tr key={st.student_id}>
                              <td className="p-2.5 font-mono font-bold text-royal-700">{st.student_code}</td>
                              <td className="p-2.5 font-medium">{st.student_name}</td>
                              <td className="p-2.5 text-center">
                                <input
                                  type="number"
                                  min={0}
                                  max={Number(directExam.max_marks) || 100}
                                  step="0.5"
                                  value={st.marks_obtained}
                                  onChange={(e) => {
                                    const next = [...directEntries];
                                    next[idx].marks_obtained = e.target.value;
                                    setDirectEntries(next);
                                  }}
                                  className="w-28 rounded border px-2 py-1 text-center"
                                />
                              </td>
                              <td className="p-2.5">
                                <input
                                  value={st.remarks}
                                  onChange={(e) => {
                                    const next = [...directEntries];
                                    next[idx].remarks = e.target.value;
                                    setDirectEntries(next);
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
                    <button
                      type="button"
                      onClick={async () => {
                        if (!directExam.exam_name.trim() || !directExam.class_id || !directExam.subject_id) {
                          notify("Enter Exam / Re-Exam name, Class, and Subject.", "error");
                          return;
                        }
                        const entries = directEntries
                          .filter((s) => s.marks_obtained !== "" && s.marks_obtained !== null)
                          .map((s) => ({
                            student_id: s.student_id,
                            marks_obtained: Number(s.marks_obtained),
                            remarks: s.remarks,
                          }));
                        if (!entries.length) {
                          notify("Enter marks for at least one student.", "error");
                          return;
                        }
                        try {
                          const res = await api.post("/api/teacher/marks/direct", {
                            exam_name: directExam.exam_name.trim(),
                            exam_type: directExam.exam_type,
                            class_id: Number(directExam.class_id),
                            subject_id: Number(directExam.subject_id),
                            exam_date: directExam.exam_date || null,
                            max_marks: Number(directExam.max_marks) || 100,
                            submit_for_approval: true,
                            entries,
                          });
                          notify(res.data.message);
                          setDirectExam({ ...directExam, exam_name: "" });
                          loadAll();
                        } catch (err) {
                          notify(err.response?.data?.detail || "Direct marks submission failed.", "error");
                        }
                      }}
                      className="px-6 py-2.5 rounded-xl bg-navy-900 hover:bg-royal-600 text-white text-sm font-bold"
                    >
                      Submit {directExam.exam_type === "RE_EXAMINATION" ? "Re-Examination" : "Examination"} Marks for Approval (PENDING)
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
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

            {marksMode === "existing" && marksSheet && (
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
              </>
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
                {(allSubjects.length
                  ? allSubjects
                  : Array.from(new Map((dash?.assignments || []).map((a) => [a.subject_id, { id: a.subject_id, name: a.subject_name }])).values())
                ).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <input type="number" required placeholder="Duration (mins)" value={qpForm.duration_minutes} onChange={(e) => setQpForm({ ...qpForm, duration_minutes: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input type="number" required placeholder="Total Marks" value={qpForm.total_marks} onChange={(e) => setQpForm({ ...qpForm, total_marks: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Watermark Text (e.g. AK TUITION)" value={qpForm.watermark_text || ""} onChange={(e) => setQpForm({ ...qpForm, watermark_text: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Evaluation Scheme" value={qpForm.evaluation_scheme} onChange={(e) => setQpForm({ ...qpForm, evaluation_scheme: e.target.value })} className="rounded-lg border px-3 py-2" />
            </div>

            <div className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 flex flex-wrap items-center gap-3 text-xs">
              <div className="font-bold text-navy-900">Automatic Paper Creator:</div>
              <input
                placeholder="Enter Chapter / Topic (e.g. Quadratic Equations)"
                value={autoTopic}
                onChange={(e) => setAutoTopic(e.target.value)}
                className="flex-1 min-w-[210px] rounded-lg border px-3 py-1.5 bg-white"
              />
              <button
                type="button"
                onClick={handleAutoCreatePaper}
                className="px-4 py-1.5 rounded-lg bg-navy-900 hover:bg-royal-600 text-white font-bold"
              >
                Auto-Create {qpForm.total_marks || 10}-Mark Questions
              </button>
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
                    {p.watermark_text && <span className="ml-2 text-royal-700 font-semibold">• Watermark: {p.watermark_text}</span>}
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
                    parent_name: studentForm.parent_name || null,
                    parent_phone: studentForm.parent_phone || studentForm.student_phone || null,
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
              <input required placeholder="Student Full Name *" value={studentForm.student_name} onChange={(e) => setStudentForm({ ...studentForm, student_name: e.target.value })} className="rounded-lg border px-3 py-2" />
              <select required value={studentForm.class_id} onChange={(e) => setStudentForm({ ...studentForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="">Select Class *</option>
                {uniqueClasses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <input required placeholder="Student / Parent Mobile Number *" value={studentForm.student_phone} onChange={(e) => setStudentForm({ ...studentForm, student_phone: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Parent Phone (if different)" value={studentForm.parent_phone} onChange={(e) => setStudentForm({ ...studentForm, parent_phone: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Parent / Guardian Name (optional)" value={studentForm.parent_name} onChange={(e) => setStudentForm({ ...studentForm, parent_name: e.target.value })} className="rounded-lg border px-3 py-2" />
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

      {/* TEACHER FEE COLLECTION -> SENT TO ADMIN VERIFICATION */}
      {tab === "fees" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const res = await api.post("/api/teacher/fees/collect", {
                  ...feeForm,
                  student_id: Number(feeForm.student_id),
                  total_fees: feeForm.total_fees !== "" ? Number(feeForm.total_fees) : null,
                  amount: Number(feeForm.amount),
                  idempotency_key: `TFEE-${feeForm.student_id}-${Date.now()}`,
                });
                notify(res.data.message);
                setFeeForm({
                  student_id: "",
                  total_fees: "",
                  amount: "",
                  payment_mode: "CASH",
                  payment_date: new Date().toISOString().slice(0, 10),
                  reference_number: "",
                  remarks: "",
                });
                loadAll();
              } catch (err) {
                notify(err.response?.data?.detail || "Could not submit fee collection.", "error");
              }
            }}
            className="bg-white rounded-lg p-5 shadow-sm border border-slate-300 space-y-4"
          >
            <div>
              <h3 className="font-bold text-navy-900 text-lg">Student Fee Entry &amp; Collection (Send to Admin Verification)</h3>
              <p className="text-xs text-slate-600">
                Enter the student&apos;s <strong>Total Fees</strong> and <strong>Paid Fees Collected</strong> directly. Admin verifies and issues the Official PDF Receipt + SMS link to the parent.
              </p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
              <select
                required
                value={feeForm.student_id}
                onChange={(e) => {
                  const sid = e.target.value;
                  const fRec = (feeData.students || []).find((x) => String(x.student_id) === String(sid));
                  setFeeForm({
                    ...feeForm,
                    student_id: sid,
                    total_fees: fRec && fRec.total_fees > 0 ? String(fRec.total_fees) : "",
                  });
                }}
                className="rounded border border-slate-300 px-3 py-2 bg-white font-semibold"
              >
                <option value="">Select Student *</option>
                {(feeData.students || []).map((st) => (
                  <option key={st.student_id} value={st.student_id}>
                    {st.student_code} - {st.student_name} ({st.class_name}) [Total: Rs.{st.total_fees} | Paid: Rs.{st.paid_amount}]
                  </option>
                ))}
              </select>
              <input
                type="number"
                required
                min={0}
                step="0.01"
                placeholder="Total Fees for Student (Rs.) *"
                value={feeForm.total_fees}
                onChange={(e) => setFeeForm({ ...feeForm, total_fees: e.target.value })}
                className="rounded border border-slate-300 px-3 py-2 font-semibold"
              />
              <input
                type="number"
                required
                min={1}
                step="0.01"
                placeholder="Paid Fees Collected Now (Rs.) *"
                value={feeForm.amount}
                onChange={(e) => setFeeForm({ ...feeForm, amount: e.target.value })}
                className="rounded border border-slate-300 px-3 py-2 font-semibold"
              />
              <select
                value={feeForm.payment_mode}
                onChange={(e) => setFeeForm({ ...feeForm, payment_mode: e.target.value })}
                className="rounded border border-slate-300 px-3 py-2 bg-white"
              >
                <option value="CASH">Cash</option>
                <option value="UPI">UPI</option>
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="OTHER">Other / Cheque</option>
              </select>
              <input
                type="date"
                value={feeForm.payment_date}
                onChange={(e) => setFeeForm({ ...feeForm, payment_date: e.target.value })}
                className="rounded border border-slate-300 px-3 py-2"
              />
              <input
                placeholder="Transaction / Ref No. (Optional)"
                value={feeForm.reference_number}
                onChange={(e) => setFeeForm({ ...feeForm, reference_number: e.target.value })}
                className="rounded border border-slate-300 px-3 py-2"
              />
              <input
                placeholder="Remarks (Optional)"
                value={feeForm.remarks}
                onChange={(e) => setFeeForm({ ...feeForm, remarks: e.target.value })}
                className="sm:col-span-2 lg:col-span-3 rounded border border-slate-300 px-3 py-2"
              />
            </div>
            <button type="submit" className="px-6 py-2.5 rounded bg-navy-900 hover:bg-royal-600 text-white text-sm font-bold">
              Submit Fee Entry to Admin for Verification
            </button>
          </form>

          <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
            <div className="p-4 border-b font-bold text-navy-900">Recent Fee Collections &amp; Verified PDF Receipts</div>
            <table className="w-full text-xs">
              <thead className="bg-navy-900 text-white uppercase">
                <tr>
                  <th className="p-3 text-left">Date</th>
                  <th className="p-3 text-left">Student</th>
                  <th className="p-3 text-left">Class</th>
                  <th className="p-3 text-center">Amount</th>
                  <th className="p-3 text-center">Mode</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">PDF Receipt &amp; SMS</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(feeData.collections || []).map((p) => (
                  <tr key={p.id}>
                    <td className="p-3">{p.payment_date}</td>
                    <td className="p-3 font-semibold">{p.student_code} - {p.student_name}</td>
                    <td className="p-3">{p.class_name}</td>
                    <td className="p-3 text-center font-bold">Rs. {p.amount.toLocaleString()}</td>
                    <td className="p-3 text-center">{p.payment_mode}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full font-bold ${
                        p.status === "VERIFIED" ? "bg-emerald-100 text-emerald-800" :
                        p.status === "REJECTED" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="p-3 text-right space-x-2 whitespace-nowrap">
                      {p.status === "VERIFIED" ? (
                        <>
                          <button
                            type="button"
                            onClick={() => downloadAuthorizedFile(`/api/teacher/fees/${p.id}/receipt-pdf`, `AK_Receipt_${p.student_code}_${p.id}.pdf`)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-navy-900 text-white font-bold"
                          >
                            <Download className="w-3.5 h-3.5" /> PDF ({p.receipt_number})
                          </button>
                          {p.sms_url && (
                            <a href={p.sms_url} className="inline-flex items-center px-2.5 py-1 rounded-lg bg-royal-600 text-white font-bold">
                              SMS PDF
                            </a>
                          )}
                          {p.whatsapp_url && (
                            <a href={p.whatsapp_url} target="_blank" rel="noreferrer" className="inline-flex items-center px-2.5 py-1 rounded-lg bg-emerald-600 text-white font-bold">
                              WhatsApp PDF
                            </a>
                          )}
                        </>
                      ) : (
                        <span className="text-slate-400">Waiting Admin Verification</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TEACHER BANK DETAILS & SALARY PAYOUTS */}
      {tab === "salary" && (
        <div className="space-y-6">
          <div className="grid lg:grid-cols-2 gap-6">
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const res = await api.put("/api/teacher/bank-details", bankForm);
                  notify(res.data.message);
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Could not save bank details.", "error");
                }
              }}
              className="bg-white rounded-lg p-5 shadow-sm border border-slate-300 space-y-3"
            >
              <h3 className="font-bold text-navy-900 text-base">Bank Account &amp; UPI Details (Send to Admin)</h3>
              <p className="text-xs text-slate-600">
                Enter your bank details below so Administrator can verify and disburse salary payouts through the portal.
              </p>
              <div className="grid sm:grid-cols-2 gap-3 text-sm">
                <input
                  required
                  placeholder="Account Holder Name *"
                  value={bankForm.bank_account_holder || ""}
                  onChange={(e) => setBankForm({ ...bankForm, bank_account_holder: e.target.value })}
                  className="rounded border border-slate-300 px-3 py-2"
                />
                <input
                  required
                  placeholder="Bank Name *"
                  value={bankForm.bank_name || ""}
                  onChange={(e) => setBankForm({ ...bankForm, bank_name: e.target.value })}
                  className="rounded border border-slate-300 px-3 py-2"
                />
                <input
                  required
                  placeholder="Account Number *"
                  value={bankForm.bank_account_number || ""}
                  onChange={(e) => setBankForm({ ...bankForm, bank_account_number: e.target.value })}
                  className="rounded border border-slate-300 px-3 py-2 font-mono"
                />
                <input
                  required
                  placeholder="IFSC Code *"
                  value={bankForm.bank_ifsc || ""}
                  onChange={(e) => setBankForm({ ...bankForm, bank_ifsc: e.target.value.toUpperCase() })}
                  className="rounded border border-slate-300 px-3 py-2 font-mono uppercase"
                />
                <input
                  placeholder="UPI ID (Optional, e.g. name@okaxis)"
                  value={bankForm.upi_id || ""}
                  onChange={(e) => setBankForm({ ...bankForm, upi_id: e.target.value })}
                  className="sm:col-span-2 rounded border border-slate-300 px-3 py-2"
                />
              </div>
              <button type="submit" className="px-5 py-2 rounded bg-navy-900 hover:bg-royal-600 text-white text-xs font-bold">
                Save &amp; Send Bank Details to Admin
              </button>
            </form>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const res = await api.post("/api/teacher/salary/request", {
                    ...salReqForm,
                    requested_amount: Number(salReqForm.requested_amount),
                  });
                  notify(res.data.message);
                  setSalReqForm({ ...salReqForm, requested_amount: "", remarks: "" });
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Salary request failed.", "error");
                }
              }}
              className="bg-white rounded-lg p-5 shadow-sm border border-slate-300 space-y-3"
            >
              <h3 className="font-bold text-navy-900 text-base">Request Salary Payout</h3>
              <p className="text-xs text-slate-600">
                Submit monthly salary payout details to Admin after saving your Bank / UPI details.
              </p>
              <div className="grid sm:grid-cols-2 gap-3 text-sm">
                <input
                  required
                  placeholder="Month (e.g. November 2026)"
                  value={salReqForm.month_label}
                  onChange={(e) => setSalReqForm({ ...salReqForm, month_label: e.target.value })}
                  className="rounded border border-slate-300 px-3 py-2"
                />
                <input
                  type="number"
                  required
                  min={1}
                  placeholder="Salary Amount (Rs.) *"
                  value={salReqForm.requested_amount}
                  onChange={(e) => setSalReqForm({ ...salReqForm, requested_amount: e.target.value })}
                  className="rounded border border-slate-300 px-3 py-2"
                />
                <input
                  placeholder="Remarks (Optional)"
                  value={salReqForm.remarks}
                  onChange={(e) => setSalReqForm({ ...salReqForm, remarks: e.target.value })}
                  className="sm:col-span-2 rounded border border-slate-300 px-3 py-2"
                />
              </div>
              <button type="submit" className="px-5 py-2 rounded bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold">
                Send Salary Payout Request to Admin
              </button>
            </form>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-slate-300 overflow-x-auto">
            <div className="p-4 border-b font-bold text-navy-900 text-sm">Salary Payout History &amp; Official Salary Slips</div>
            <table className="w-full text-xs">
              <thead className="bg-navy-900 text-white uppercase">
                <tr>
                  <th className="p-3 text-left">Month</th>
                  <th className="p-3 text-left">Slip No</th>
                  <th className="p-3 text-center">Base</th>
                  <th className="p-3 text-center">Bonus / Ded</th>
                  <th className="p-3 text-center">Net Paid</th>
                  <th className="p-3 text-center">Mode / UTR</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Salary Slip PDF</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(salaryData.payouts || []).map((p) => (
                  <tr key={p.id}>
                    <td className="p-3 font-semibold">{p.month_label}</td>
                    <td className="p-3 font-mono font-bold text-royal-700">{p.slip_number || "-"}</td>
                    <td className="p-3 text-center">Rs. {p.base_salary.toLocaleString()}</td>
                    <td className="p-3 text-center">+Rs.{p.bonus} / -Rs.{p.deductions}</td>
                    <td className="p-3 text-center font-bold text-navy-900">Rs. {p.net_amount.toLocaleString()}</td>
                    <td className="p-3 text-center">{p.payment_mode} {p.transaction_reference ? `(${p.transaction_reference})` : ""}</td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 rounded font-bold ${p.status === "PAID" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      {p.status === "PAID" ? (
                        <button
                          type="button"
                          onClick={() => downloadAuthorizedFile(`/api/teacher/salary/${p.id}/slip-pdf`, `AK_SalarySlip_${p.id}.pdf`)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-navy-900 text-white font-bold"
                        >
                          <Download className="w-3.5 h-3.5" /> Slip PDF
                        </button>
                      ) : (
                        <span className="text-slate-400">Pending Admin Payout</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* HOW TO USE GUIDE */}
      {tab === "guide" && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border space-y-5">
          <div>
            <h3 className="font-bold text-navy-900 text-xl">AK Tuition Portal — Step-by-Step Teacher Guide</h3>
            <p className="text-xs text-slate-600 mt-1">
              Quick visual instructions for every daily workflow in AKTP Portal.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            {[
              {
                step: "Step 1: Add Students & Take Unified Attendance",
                desc: "Open All Students to add a student (auto AK ID + instant login credentials). In Daily Attendance, mark Absent students once and Save — absence alerts prepare/send automatically to parent numbers and your Group.",
              },
              {
                step: "Step 2: Click Any Student Name -> Enter Marks by Subject",
                desc: "In All Students, simply click a student's name (or 'Enter Marks'). It opens Marks Entry with All Subjects loaded by default and a Subject filter dropdown. Enter scores per subject and click 'Save Marks' or 'Save & Submit ALL Subject Marks'.",
              },
              {
                step: "Step 3: Collect Fees -> Admin Verifies -> Official PDF + SMS",
                desc: "Open 'Collect Fees' (or click 'Collect Fee' on a student row), enter collected amount and Cash/UPI mode, and submit to Admin. Once Admin clicks Verify, an official Receipt PDF is generated and can be sent via SMS/WhatsApp.",
              },
              {
                step: "Step 4: Auto Question Papers & Custom Watermarks",
                desc: "Open 'Question Papers', enter a topic & Total Marks, type a Watermark (e.g. AK TUITION), and click 'Auto-Create Questions'. Download the watermarked PDF anytime.",
              },
              {
                step: "Step 5: Result Publishing & 15-Day Shareable Link",
                desc: "After Teacher submits marks, Admin clicks 'Publish All & Announce Results'. Students immediately view & download digitally signed Marks Cards on /results (valid 15 days publicly; permanent in Student/Parent login).",
              },
            ].map((card) => (
              <div key={card.step} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="font-bold text-navy-900">{card.step}</div>
                <p className="text-xs text-slate-600 leading-relaxed">{card.desc}</p>
              </div>
            ))}
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
              <a
                href={`https://wa.me/${String(credsModal.parent_phone || "").replace(/\D/g, "").replace(/^(\d{10})$/, "91$1")}?text=${encodeURIComponent(`AK TUITION PORTAL LOGIN\nStudent: ${credsModal.student_name}\nStudent ID: ${credsModal.student_username}\nStudent Password: ${credsModal.student_password}\nParent Login Phone: ${credsModal.parent_phone}\nPortal: https://aktp-portal.netlify.app`)}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-semibold"
              >
                Send on WhatsApp
              </a>
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
