import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  LayoutDashboard,
  Users,
  UserCheck,
  BookOpen,
  IndianRupee,
  Calendar,
  CheckSquare,
  Bell,
  Megaphone,
  FileSpreadsheet,
  Settings,
  Plus,
  Download,
  Trash2,
  Edit3,
  Upload,
  Check,
  X,
  Eye,
  KeyRound,
  Copy,
} from "lucide-react";
import PortalLayout from "../components/PortalLayout";
import api, { downloadAuthorizedFile, resolveAssetUrl } from "../api/client";

const REPORT_LIST = [
  { id: "overall_students", label: "1. Overall Student Report" },
  { id: "class_wise_students", label: "2. Class-wise Student Report" },
  { id: "student_attendance", label: "3. Student Attendance Report" },
  { id: "absent_students", label: "4. Absent Student Report" },
  { id: "overall_attendance_percentage", label: "5. Overall Attendance Percentage Report" },
  { id: "examination_timetable", label: "6. Examination Timetable" },
  { id: "examination_results", label: "7. Examination Results" },
  { id: "individual_marks_card", label: "8. Individual Marks Card (PDF)", pdfOnly: true },
  { id: "class_wise_performance", label: "9. Class-wise Performance" },
  { id: "fee_collection", label: "10. Fee Collection Report" },
  { id: "pending_fees", label: "11. Pending Fee Report" },
  { id: "student_payment_history", label: "12. Student Payment History" },
  { id: "teacher_report", label: "13. Teacher Report" },
];

export default function AdminPortal() {
  const [tab, setTab] = useState("dashboard");
  const [dash, setDash] = useState(null);
  const [students, setStudents] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [classes, setClasses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [feesData, setFeesData] = useState({ student_fees: [], payments: [] });
  const [exams, setExams] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [notifData, setNotifData] = useState({ mode: {}, notifications: [] });
  const [settings, setSettings] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [teacherAtt, setTeacherAtt] = useState([]);

  const [toast, setToast] = useState({ type: "", text: "" });
  const [searchTerm, setSearchTerm] = useState("");
  const [classFilter, setClassFilter] = useState("");

  // Modals / Forms
  const [studentModal, setStudentModal] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [studentForm, setStudentForm] = useState({
    student_name: "",
    date_of_birth: "",
    gender: "Male",
    class_id: "",
    section: "A",
    address: "",
    student_phone: "",
    parent_name: "",
    parent_phone: "",
    assigned_teacher_id: "",
    total_fees: "",
    student_password: "",
    parent_password: "",
  });
  const [historyModal, setHistoryModal] = useState(null);
  const [credentialsModal, setCredentialsModal] = useState(null);

  const [teacherForm, setTeacherForm] = useState({
    teacher_name: "",
    username: "",
    password: "",
    phone: "",
    email: "",
    qualification: "",
    specialization: "",
  });
  const [assignForm, setAssignForm] = useState({ teacher_id: "", class_id: "", subject_id: "", is_class_teacher: false });
  const [tAttForm, setTAttForm] = useState({ teacher_id: "", attendance_date: new Date().toISOString().slice(0, 10), status: "PRESENT", remarks: "" });

  const [classForm, setClassForm] = useState({ grade_level: 1, name: "Class 1", section: "B", capacity: 40, tuition_fee: 11000 });
  const [subjectForm, setSubjectForm] = useState({ name: "", code: "", description: "" });
  const [classSubjForm, setClassSubjForm] = useState({ class_id: "", subject_ids: [] });

  const [paymentModal, setPaymentModal] = useState(null);
  const [paymentForm, setPaymentForm] = useState({ amount: "", payment_mode: "UPI", reference_number: "", remarks: "" });

  const [examForm, setExamForm] = useState({
    name: "",
    class_id: "",
    exam_type: "UNIT_TEST",
    start_date: "",
    end_date: "",
    instructions: "",
    subjects: [{ subject_id: "", exam_date: "", start_time: "10:00 AM", duration_minutes: 90, max_marks: 100, passing_marks: 35 }],
  });

  const [rejectReasonMap, setRejectReasonMap] = useState({});
  const [annForm, setAnnForm] = useState({ title: "", category: "NOTICE", content: "", event_date: "", target_audience: "PUBLIC", is_featured: false });
  const [notifForm, setNotifForm] = useState({ notification_type: "ANNOUNCEMENT", channel: "SMS", class_id: "", message: "" });
  const [reportFilters, setReportFilters] = useState({ class_id: "", student_id: "", examination_id: "", subject_id: "", start_date: "", end_date: "" });

  const notify = (text, type = "success") => {
    setToast({ type, text });
    setTimeout(() => setToast({ type: "", text: "" }), 5000);
  };

  const loadAll = async () => {
    try {
      const [dRes, sRes, tRes, cRes, subRes, fRes, exRes, apRes, anRes, nRes, setRes] = await Promise.all([
        api.get("/api/admin/dashboard"),
        api.get("/api/admin/students"),
        api.get("/api/admin/teachers"),
        api.get("/api/admin/classes"),
        api.get("/api/admin/subjects"),
        api.get("/api/admin/fees"),
        api.get("/api/admin/examinations"),
        api.get("/api/admin/result-approvals"),
        api.get("/api/admin/announcements"),
        api.get("/api/admin/notifications"),
        api.get("/api/admin/settings"),
      ]);
      setDash(dRes.data);
      setStudents(sRes.data);
      setTeachers(tRes.data);
      setClasses(cRes.data);
      setSubjects(subRes.data);
      setFeesData(fRes.data);
      setExams(exRes.data);
      setApprovals(apRes.data);
      setAnnouncements(anRes.data);
      setNotifData(nRes.data);
      setSettings(setRes.data);
    } catch (e) {
      notify(e.response?.data?.detail || "Error loading admin data", "error");
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (tab === "settings") {
      api.get("/api/admin/audit-logs").then((r) => setAuditLogs(r.data)).catch(() => {});
    }
    if (tab === "teachers") {
      api.get("/api/admin/teacher-attendance").then((r) => setTeacherAtt(r.data)).catch(() => {});
    }
  }, [tab]);

  const pendingCount = approvals.filter((a) => a.status === "PENDING").length;

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "students", label: "Students", icon: Users },
    { id: "teachers", label: "Teachers", icon: UserCheck },
    { id: "classes", label: "Classes & Subjects", icon: BookOpen },
    { id: "fees", label: "Fees & Payments", icon: IndianRupee },
    { id: "examinations", label: "Examinations", icon: Calendar },
    { id: "approvals", label: "Result Approvals", icon: CheckSquare, badge: pendingCount },
    { id: "notifications", label: "SMS & WhatsApp", icon: Bell },
    { id: "announcements", label: "News & Notices", icon: Megaphone },
    { id: "reports", label: "PDF & Excel Reports", icon: FileSpreadsheet },
    { id: "settings", label: "Settings & Audit", icon: Settings },
  ];

  // Handlers
  const handleSaveStudent = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...studentForm,
        class_id: Number(studentForm.class_id),
        date_of_birth: studentForm.date_of_birth || null,
        assigned_teacher_id: studentForm.assigned_teacher_id ? Number(studentForm.assigned_teacher_id) : null,
        total_fees: studentForm.total_fees !== "" ? Number(studentForm.total_fees) : null,
        student_password: studentForm.student_password || null,
        parent_password: studentForm.parent_password || null,
      };
      if (editingStudent) {
        await api.put(`/api/admin/students/${editingStudent.id}`, payload);
        notify("Student record updated.");
      } else {
        const res = await api.post("/api/admin/students", payload);
        setCredentialsModal({
          title: `Portal Login Details — ${res.data.student_name} (${res.data.student_code})`,
          type: "student_parent",
          data: res.data.generated_credentials,
        });
        notify(`Student ${res.data.student_code} registered with unique portal credentials.`);
      }
      setStudentModal(false);
      setEditingStudent(null);
      loadAll();
    } catch (err) {
      notify(err.response?.data?.detail || "Failed to save student.", "error");
    }
  };

  const handleDeactivateStudent = async (st) => {
    if (!window.confirm(`Deactivate student ${st.student_name} (${st.student_code})?`)) return;
    try {
      await api.delete(`/api/admin/students/${st.id}`);
      notify(`Student ${st.student_code} deactivated.`);
      loadAll();
    } catch (err) {
      notify(err.response?.data?.detail || "Action failed.", "error");
    }
  };

  const handlePhotoUpload = async (studentId, file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post(`/api/admin/students/${studentId}/photo`, fd);
      notify("Student photograph uploaded.");
      loadAll();
    } catch (err) {
      notify(err.response?.data?.detail || "Photo upload failed.", "error");
    }
  };

  const handleRecordPayment = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post("/api/admin/payments", {
        student_id: paymentModal.student_id,
        amount: Number(paymentForm.amount),
        payment_mode: paymentForm.payment_mode,
        reference_number: paymentForm.reference_number || null,
        idempotency_key: `PAY-${paymentModal.student_id}-${Date.now()}`,
        remarks: paymentForm.remarks,
      });
      notify(`Payment recorded! Receipt ${res.data.receipt_number}`);
      setPaymentModal(null);
      setPaymentForm({ amount: "", payment_mode: "UPI", reference_number: "", remarks: "" });
      loadAll();
    } catch (err) {
      notify(err.response?.data?.detail || "Payment recording failed.", "error");
    }
  };

  const handleCreateExam = async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/admin/examinations", {
        ...examForm,
        class_id: Number(examForm.class_id),
        subjects: examForm.subjects.map((s) => ({
          ...s,
          subject_id: Number(s.subject_id),
          duration_minutes: Number(s.duration_minutes),
          max_marks: Number(s.max_marks),
          passing_marks: Number(s.passing_marks),
        })),
      });
      notify("Examination & timetable created.");
      setExamForm({
        name: "",
        class_id: "",
        exam_type: "UNIT_TEST",
        start_date: "",
        end_date: "",
        instructions: "",
        subjects: [{ subject_id: "", exam_date: "", start_time: "10:00 AM", duration_minutes: 90, max_marks: 100, passing_marks: 35 }],
      });
      loadAll();
    } catch (err) {
      notify(err.response?.data?.detail || "Failed to create examination.", "error");
    }
  };

  const handleReviewApproval = async (approvalId, action) => {
    try {
      const res = await api.post(`/api/admin/result-approvals/${approvalId}/review`, {
        action,
        rejection_reason: rejectReasonMap[approvalId] || "",
        send_notifications: true,
      });
      notify(res.data.message);
      loadAll();
    } catch (err) {
      notify(err.response?.data?.detail || "Review failed.", "error");
    }
  };

  const handleDownloadReport = async (reportId, format) => {
    try {
      const params = new URLSearchParams({ format });
      Object.entries(reportFilters).forEach(([k, v]) => {
        if (v) params.append(k, v);
      });
      await downloadAuthorizedFile(
        `/api/admin/reports/${reportId}?${params.toString()}`,
        `AKTP_${reportId}.${format}`
      );
    } catch (err) {
      notify(err.response?.data?.detail || "Could not generate report. Check required filters.", "error");
    }
  };

  const filteredStudents = students.filter((s) => {
    const matchesSearch =
      !searchTerm ||
      s.student_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.student_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.parent_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesClass = !classFilter || String(s.class_id) === String(classFilter);
    return matchesSearch && matchesClass;
  });

  return (
    <PortalLayout
      title="Administrator Portal"
      subtitle="AKTP PORTAL — Complete Control Center"
      navItems={navItems}
      activeTab={tab}
      onSelectTab={setTab}
    >
      {toast.text && (
        <div
          className={`mb-4 px-4 py-3 rounded-xl text-sm font-medium border ${
            toast.type === "error"
              ? "bg-red-50 text-red-700 border-red-200"
              : "bg-emerald-50 text-emerald-800 border-emerald-200"
          }`}
        >
          {toast.text}
        </div>
      )}

      {/* DASHBOARD */}
      {tab === "dashboard" && dash && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {[
              { label: "Total Students", val: dash.cards.total_students, color: "border-royal-500" },
              { label: "Total Teachers", val: dash.cards.total_teachers, color: "border-navy-900" },
              { label: "Total Classes", val: dash.cards.total_classes, color: "border-indigo-500" },
              { label: "Total Fees Collected", val: `₹${dash.cards.total_fees_collected.toLocaleString("en-IN")}`, color: "border-emerald-600" },
              { label: "Pending Fees", val: `₹${dash.cards.pending_fees.toLocaleString("en-IN")}`, color: "border-amber-500" },
              { label: "Today's Attendance", val: `${dash.cards.today_attendance_present}/${dash.cards.today_attendance_total} (${dash.cards.today_attendance_pct}%)`, color: "border-sky-600" },
              { label: "Overall Attendance %", val: `${dash.cards.overall_attendance_pct}%`, color: "border-teal-600" },
              { label: "Upcoming Examinations", val: dash.cards.upcoming_examinations, color: "border-purple-600" },
              { label: "Published Results", val: dash.cards.published_results, color: "border-emerald-700" },
              { label: "Pending Result Approvals", val: dash.cards.pending_result_approvals, color: "border-red-600" },
              { label: "Active Practice Tests", val: dash.cards.active_practice_tests, color: "border-gold-500" },
            ].map((card) => (
              <div key={card.label} className={`bg-white rounded-2xl p-4 shadow-sm border-l-4 ${card.color}`}>
                <div className="text-xs font-semibold text-slate-500 uppercase">{card.label}</div>
                <div className="text-xl sm:text-2xl font-extrabold text-navy-900 mt-1">{card.val}</div>
              </div>
            ))}
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Monthly Fee Collection (₹)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dash.charts.monthly_fee_collection}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" fontSize={11} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="amount" fill="#1E40AF" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Student Enrollment Growth</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dash.charts.enrollment_growth}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" fontSize={11} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Line type="monotone" dataKey="students" stroke="#0A2463" strokeWidth={3} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Daily Attendance Statistics</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dash.charts.attendance_stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={10} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="present" fill="#059669" />
                    <Bar dataKey="absent" fill="#DC2626" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Examination & Subject Performance (%)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dash.charts.subject_wise_performance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="subject" fontSize={11} />
                    <YAxis domain={[0, 100]} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="average_pct" name="Avg %" fill="#D4AF37" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Class-Wise Published Results (%)</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dash.charts.class_wise_results}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="class_name" fontSize={11} />
                    <YAxis domain={[0, 100]} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="average_pct" name="Avg %" fill="#0A2463" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Exam-Wise Average Performance (%)</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dash.charts.exam_performance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="exam" fontSize={11} />
                    <YAxis domain={[0, 100]} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="average_pct" name="Avg %" fill="#2563EB" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* STUDENTS */}
      {tab === "students" && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2 flex-1">
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by Student ID (AK001), name, or parent..."
                className="rounded-xl border border-slate-300 px-3.5 py-2 text-sm min-w-[240px]"
              />
              <select
                value={classFilter}
                onChange={(e) => setClassFilter(e.target.value)}
                className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">All Classes</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>{c.name} ({c.section})</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => {
                setEditingStudent(null);
                setStudentForm({
                  student_name: "",
                  date_of_birth: "",
                  gender: "Male",
                  class_id: classes[0]?.id || "",
                  section: "A",
                  address: "",
                  student_phone: "",
                  parent_name: "",
                  parent_phone: "",
                  assigned_teacher_id: "",
                  total_fees: "",
                  student_password: "",
                  parent_password: "",
                });
                setStudentModal(true);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy-900 hover:bg-royal-600 text-white text-sm font-semibold"
            >
              <Plus className="w-4 h-4" /> Add Student (Auto AK ID)
            </button>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-navy-900 text-white text-xs uppercase">
                <tr>
                  <th className="p-3 text-left">ID</th>
                  <th className="p-3 text-left">Student</th>
                  <th className="p-3 text-left">Class</th>
                  <th className="p-3 text-left">Parent & Phone</th>
                  <th className="p-3 text-right">Fees (Paid / Total)</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredStudents.map((st) => (
                  <tr key={st.id} className="hover:bg-blue-50/40">
                    <td className="p-3 font-mono font-bold text-royal-700">{st.student_code}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2.5">
                        {st.photo_path ? (
                          <img src={resolveAssetUrl(st.photo_path)} alt={st.student_name} className="w-8 h-8 rounded-full object-cover" />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-navy-900 font-bold flex items-center justify-center text-xs">
                            {st.student_name.slice(0, 2).toUpperCase()}
                          </div>
                        )}
                        <div>
                          <div className="font-semibold text-navy-900">{st.student_name}</div>
                          <div className="text-xs text-slate-500">{st.gender || "-"}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3">{st.class_name} ({st.section})</td>
                    <td className="p-3">
                      <div className="font-medium">{st.parent_name}</div>
                      <div className="text-xs text-slate-500">{st.parent_phone}</div>
                    </td>
                    <td className="p-3 text-right">
                      <div className="font-semibold text-emerald-700">₹{st.paid_fees.toLocaleString("en-IN")} / ₹{st.total_fees.toLocaleString("en-IN")}</div>
                      <div className="text-xs text-amber-700">Pending: ₹{st.pending_fees.toLocaleString("en-IN")}</div>
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${st.is_active ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"}`}>
                        {st.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="p-3 text-right space-x-1 whitespace-nowrap">
                      <button
                        onClick={async () => {
                          const r = await api.get(`/api/admin/students/${st.id}/history`);
                          setHistoryModal(r.data);
                        }}
                        className="p-1.5 rounded-lg bg-blue-50 text-royal-600 hover:bg-blue-100"
                        title="View Academic History"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => {
                          setEditingStudent(st);
                          setStudentForm({
                            student_name: st.student_name,
                            date_of_birth: st.date_of_birth || "",
                            gender: st.gender || "Male",
                            class_id: st.class_id,
                            section: st.section,
                            address: st.address || "",
                            student_phone: st.student_phone || "",
                            parent_name: st.parent_name,
                            parent_phone: st.parent_phone,
                            total_fees: st.total_fees,
                          });
                          setStudentModal(true);
                        }}
                        className="p-1.5 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100"
                        title="Edit Student"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <label className="inline-block p-1.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 cursor-pointer" title="Upload Photo">
                        <Upload className="w-4 h-4" />
                        <input type="file" accept="image/*" className="hidden" onChange={(e) => handlePhotoUpload(st.id, e.target.files?.[0])} />
                      </label>
                      <button
                        onClick={async () => {
                          if (!window.confirm(`Generate new unique login passwords for ${st.student_name} (${st.student_code}) and parent?`)) return;
                          const r = await api.post(`/api/admin/students/${st.id}/reset-credentials`);
                          setCredentialsModal({
                            title: `Updated Login Details — ${st.student_name} (${st.student_code})`,
                            type: "student_parent",
                            data: r.data,
                          });
                        }}
                        className="p-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
                        title="Generate Unique Login & Password"
                      >
                        <KeyRound className="w-4 h-4" />
                      </button>
                      {st.is_active && (
                        <button
                          onClick={() => handleDeactivateStudent(st)}
                          className="p-1.5 rounded-lg bg-red-50 text-red-600 hover:bg-red-100"
                          title="Deactivate Student"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TEACHERS */}
      {tab === "teachers" && (
        <div className="space-y-6">
          <div className="grid lg:grid-cols-2 gap-6">
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const res = await api.post("/api/admin/teachers", teacherForm);
                  setCredentialsModal({
                    title: `Teacher Login Details — ${res.data.teacher_name} (${res.data.teacher_code})`,
                    type: "teacher",
                    data: res.data,
                  });
                  notify(`Teacher ${res.data.teacher_code} created with unique access key.`);
                  setTeacherForm({ teacher_name: "", username: "", password: "", phone: "", email: "", qualification: "", specialization: "" });
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Failed to add teacher.", "error");
                }
              }}
              className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 space-y-3"
            >
              <h3 className="font-bold text-navy-900">Add New Teacher</h3>
              <div className="grid sm:grid-cols-2 gap-3">
                <input required placeholder="Full Name" value={teacherForm.teacher_name} onChange={(e) => setTeacherForm({ ...teacherForm, teacher_name: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input required placeholder="Login Username" value={teacherForm.username} onChange={(e) => setTeacherForm({ ...teacherForm, username: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input placeholder="Access Key / Password (auto-unique if blank)" value={teacherForm.password} onChange={(e) => setTeacherForm({ ...teacherForm, password: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input required placeholder="Phone Number" value={teacherForm.phone} onChange={(e) => setTeacherForm({ ...teacherForm, phone: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input placeholder="Qualification (e.g. M.Sc., B.Ed.)" value={teacherForm.qualification} onChange={(e) => setTeacherForm({ ...teacherForm, qualification: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input placeholder="Specialization" value={teacherForm.specialization} onChange={(e) => setTeacherForm({ ...teacherForm, specialization: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              </div>
              <button type="submit" className="px-4 py-2 rounded-xl bg-navy-900 text-white text-sm font-semibold">Add Teacher</button>
            </form>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await api.post("/api/admin/teacher-assignments", {
                    teacher_id: Number(assignForm.teacher_id),
                    class_id: Number(assignForm.class_id),
                    subject_id: Number(assignForm.subject_id),
                    is_class_teacher: assignForm.is_class_teacher,
                  });
                  notify("Class & subject assigned to teacher.");
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Assignment failed.", "error");
                }
              }}
              className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 space-y-3"
            >
              <h3 className="font-bold text-navy-900">Assign Class & Subject to Teacher</h3>
              <div className="grid sm:grid-cols-3 gap-3">
                <select required value={assignForm.teacher_id} onChange={(e) => setAssignForm({ ...assignForm, teacher_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                  <option value="">Select Teacher</option>
                  {teachers.map((t) => <option key={t.id} value={t.id}>{t.teacher_name}</option>)}
                </select>
                <select required value={assignForm.class_id} onChange={(e) => setAssignForm({ ...assignForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                  <option value="">Select Class</option>
                  {classes.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.section})</option>)}
                </select>
                <select required value={assignForm.subject_id} onChange={(e) => setAssignForm({ ...assignForm, subject_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                  <option value="">Select Subject</option>
                  {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-600">
                <input type="checkbox" checked={assignForm.is_class_teacher} onChange={(e) => setAssignForm({ ...assignForm, is_class_teacher: e.target.checked })} />
                Class Teacher
              </label>
              <div>
                <button type="submit" className="px-4 py-2 rounded-xl bg-royal-600 text-white text-sm font-semibold">Assign Subject</button>
              </div>
            </form>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-navy-900 text-white text-xs uppercase">
                <tr>
                  <th className="p-3 text-left">Code</th>
                  <th className="p-3 text-left">Name</th>
                  <th className="p-3 text-left">Qualification</th>
                  <th className="p-3 text-left">Assignments</th>
                  <th className="p-3 text-center">Status</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {teachers.map((t) => (
                  <tr key={t.id}>
                    <td className="p-3 font-mono font-bold text-royal-700">{t.teacher_code}</td>
                    <td className="p-3">
                      <div className="font-semibold text-navy-900">{t.teacher_name}</div>
                      <div className="text-xs text-slate-500">{t.phone} • @{t.username}</div>
                    </td>
                    <td className="p-3 text-xs">{t.qualification}<div className="text-slate-500">{t.specialization}</div></td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1.5">
                        {t.assignments.map((a) => (
                          <span key={a.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-royal-700 text-xs">
                            {a.class_name}: {a.subject_name}
                            <button
                              onClick={async () => {
                                await api.delete(`/api/admin/teacher-assignments/${a.id}`);
                                loadAll();
                              }}
                              className="text-red-500 hover:text-red-700"
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${t.is_active ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-700"}`}>
                        {t.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="p-3 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        onClick={async () => {
                          if (!window.confirm(`Generate new unique access key for ${t.teacher_name}?`)) return;
                          const r = await api.post(`/api/admin/teachers/${t.id}/reset-credentials`);
                          setCredentialsModal({
                            title: `Updated Teacher Access Key — ${t.teacher_name}`,
                            type: "teacher",
                            data: r.data,
                          });
                        }}
                        className="px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 text-xs font-semibold"
                      >
                        Reset Key
                      </button>
                      <button
                        onClick={async () => {
                          await api.put(`/api/admin/teachers/${t.id}`, { is_active: !t.is_active });
                          loadAll();
                        }}
                        className="px-3 py-1 rounded-lg border text-xs font-semibold"
                      >
                        {t.is_active ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Teacher Attendance */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200 space-y-4">
            <h3 className="font-bold text-navy-900">Teacher Attendance Register</h3>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                await api.post("/api/admin/teacher-attendance", { ...tAttForm, teacher_id: Number(tAttForm.teacher_id) });
                notify("Teacher attendance saved.");
                const r = await api.get("/api/admin/teacher-attendance");
                setTeacherAtt(r.data);
              }}
              className="flex flex-wrap gap-3"
            >
              <select required value={tAttForm.teacher_id} onChange={(e) => setTAttForm({ ...tAttForm, teacher_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">Select Teacher</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.teacher_name}</option>)}
              </select>
              <input type="date" value={tAttForm.attendance_date} onChange={(e) => setTAttForm({ ...tAttForm, attendance_date: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              <select value={tAttForm.status} onChange={(e) => setTAttForm({ ...tAttForm, status: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="PRESENT">PRESENT</option>
                <option value="ABSENT">ABSENT</option>
                <option value="LEAVE">LEAVE</option>
              </select>
              <input placeholder="Remarks" value={tAttForm.remarks} onChange={(e) => setTAttForm({ ...tAttForm, remarks: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              <button type="submit" className="px-4 py-2 rounded-lg bg-navy-900 text-white text-sm font-semibold">Mark</button>
            </form>
            <div className="grid sm:grid-cols-3 gap-2 text-xs">
              {teacherAtt.slice(0, 9).map((r) => (
                <div key={r.id} className="p-2.5 rounded-lg bg-slate-50 border flex justify-between">
                  <span>{r.teacher_name} ({r.attendance_date})</span>
                  <span className="font-bold text-navy-900">{r.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* CLASSES & SUBJECTS */}
      {tab === "classes" && (
        <div className="space-y-6">
          <div className="grid lg:grid-cols-2 gap-6">
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await api.post("/api/admin/classes", {
                    ...classForm,
                    grade_level: Number(classForm.grade_level),
                    capacity: Number(classForm.capacity),
                    tuition_fee: Number(classForm.tuition_fee),
                  });
                  notify("Class section created.");
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Error creating class.", "error");
                }
              }}
              className="bg-white rounded-2xl p-5 shadow-sm border space-y-3"
            >
              <h3 className="font-bold text-navy-900">Create Class / Section (1–10)</h3>
              <div className="grid grid-cols-2 gap-3">
                <input type="number" min={1} max={10} required placeholder="Grade (1-10)" value={classForm.grade_level} onChange={(e) => setClassForm({ ...classForm, grade_level: e.target.value, name: `Class ${e.target.value}` })} className="rounded-lg border px-3 py-2 text-sm" />
                <input required placeholder="Class Name" value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input required placeholder="Section (A, B...)" value={classForm.section} onChange={(e) => setClassForm({ ...classForm, section: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input type="number" required placeholder="Tuition Fee" value={classForm.tuition_fee} onChange={(e) => setClassForm({ ...classForm, tuition_fee: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              </div>
              <button type="submit" className="px-4 py-2 rounded-xl bg-navy-900 text-white text-sm font-semibold">Add Class Section</button>
            </form>

            <form
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  await api.post("/api/admin/subjects", subjectForm);
                  notify("Subject added.");
                  setSubjectForm({ name: "", code: "", description: "" });
                  loadAll();
                } catch (err) {
                  notify(err.response?.data?.detail || "Error adding subject.", "error");
                }
              }}
              className="bg-white rounded-2xl p-5 shadow-sm border space-y-3"
            >
              <h3 className="font-bold text-navy-900">Add Subject</h3>
              <div className="grid grid-cols-2 gap-3">
                <input required placeholder="Subject Name" value={subjectForm.name} onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
                <input required placeholder="Code (e.g. PHY)" value={subjectForm.code} onChange={(e) => setSubjectForm({ ...subjectForm, code: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              </div>
              <input placeholder="Description" value={subjectForm.description} onChange={(e) => setSubjectForm({ ...subjectForm, description: e.target.value })} className="w-full rounded-lg border px-3 py-2 text-sm" />
              <button type="submit" className="px-4 py-2 rounded-xl bg-royal-600 text-white text-sm font-semibold">Add Subject</button>
            </form>
          </div>

          <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
            <h3 className="font-bold text-navy-900">Assign Subjects to Class</h3>
            <div className="flex flex-wrap gap-3 items-center">
              <select
                value={classSubjForm.class_id}
                onChange={(e) => {
                  const cid = e.target.value;
                  const cls = classes.find((c) => String(c.id) === String(cid));
                  setClassSubjForm({ class_id: cid, subject_ids: cls ? cls.subjects.map((s) => s.id) : [] });
                }}
                className="rounded-lg border px-3 py-2 text-sm"
              >
                <option value="">Select Class</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.section})</option>)}
              </select>
              <div className="flex flex-wrap gap-2">
                {subjects.map((s) => {
                  const checked = classSubjForm.subject_ids.includes(s.id);
                  return (
                    <label key={s.id} className={`px-3 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer ${checked ? "bg-navy-900 text-white" : "bg-slate-50"}`}>
                      <input
                        type="checkbox"
                        className="hidden"
                        checked={checked}
                        onChange={() => {
                          const next = checked
                            ? classSubjForm.subject_ids.filter((id) => id !== s.id)
                            : [...classSubjForm.subject_ids, s.id];
                          setClassSubjForm({ ...classSubjForm, subject_ids: next });
                        }}
                      />
                      {s.name}
                    </label>
                  );
                })}
              </div>
              <button
                onClick={async () => {
                  if (!classSubjForm.class_id) return;
                  await api.post("/api/admin/class-subjects", { class_id: Number(classSubjForm.class_id), subject_ids: classSubjForm.subject_ids });
                  notify("Class subjects updated.");
                  loadAll();
                }}
                className="px-4 py-2 rounded-lg bg-gold-500 text-navy-950 font-bold text-xs"
              >
                Save Mapping
              </button>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {classes.map((c) => (
              <div key={c.id} className="bg-white rounded-2xl p-4 shadow-sm border">
                <div className="flex justify-between items-center">
                  <div className="font-bold text-navy-900">{c.name} — Section {c.section}</div>
                  <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-royal-700 text-xs font-bold">
                    Strength: {c.student_strength} / {c.capacity}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-1">Annual Tuition Fee: ₹{c.tuition_fee.toLocaleString("en-IN")}</div>
                <div className="flex flex-wrap gap-1 mt-3">
                  {c.subjects.map((s) => (
                    <span key={s.id} className="px-2 py-0.5 rounded bg-slate-100 text-xs text-slate-700">{s.code}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* FEES & PAYMENTS */}
      {tab === "fees" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
            <div className="p-4 border-b font-bold text-navy-900">Student-Wise Tuition Fee Ledger</div>
            <table className="w-full text-sm">
              <thead className="bg-navy-900 text-white text-xs uppercase">
                <tr>
                  <th className="p-3 text-left">Student ID</th>
                  <th className="p-3 text-left">Name</th>
                  <th className="p-3 text-left">Class</th>
                  <th className="p-3 text-right">Total Fees</th>
                  <th className="p-3 text-right">Paid</th>
                  <th className="p-3 text-right">Pending</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {feesData.student_fees.map((f) => (
                  <tr key={f.fee_id}>
                    <td className="p-3 font-mono font-bold text-royal-700">{f.student_code}</td>
                    <td className="p-3 font-medium">{f.student_name}</td>
                    <td className="p-3">{f.class_name}</td>
                    <td className="p-3 text-right">₹{f.total_fees.toLocaleString("en-IN")}</td>
                    <td className="p-3 text-right text-emerald-700 font-semibold">₹{f.paid_amount.toLocaleString("en-IN")}</td>
                    <td className="p-3 text-right text-amber-700 font-bold">₹{f.pending_amount.toLocaleString("en-IN")}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => {
                          setPaymentModal(f);
                          setPaymentForm({ amount: f.pending_amount || "", payment_mode: "UPI", reference_number: "", remarks: "" });
                        }}
                        className="px-3 py-1.5 rounded-lg bg-navy-900 text-white text-xs font-semibold"
                      >
                        Record Payment
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
            <div className="p-4 border-b font-bold text-navy-900">Recent Payment History & PDF Receipts</div>
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-slate-700 text-xs uppercase">
                <tr>
                  <th className="p-3 text-left">Receipt No</th>
                  <th className="p-3 text-left">Date</th>
                  <th className="p-3 text-left">Student</th>
                  <th className="p-3 text-left">Mode</th>
                  <th className="p-3 text-left">Reference</th>
                  <th className="p-3 text-right">Amount</th>
                  <th className="p-3 text-right">Receipt PDF</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {feesData.payments.map((p) => (
                  <tr key={p.id}>
                    <td className="p-3 font-mono font-semibold text-navy-900">{p.receipt_number}</td>
                    <td className="p-3">{p.payment_date}</td>
                    <td className="p-3">{p.student_name} ({p.student_code})</td>
                    <td className="p-3">{p.payment_mode}</td>
                    <td className="p-3 text-xs text-slate-500">{p.reference_number || "-"}</td>
                    <td className="p-3 text-right font-bold">₹{p.amount.toLocaleString("en-IN")}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => downloadAuthorizedFile(`/api/admin/payments/${p.id}/receipt-pdf`, `AK_Receipt_${p.receipt_number}.pdf`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 text-royal-700 text-xs font-semibold"
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

      {/* EXAMINATIONS */}
      {tab === "examinations" && (
        <div className="space-y-6">
          <form onSubmit={handleCreateExam} className="bg-white rounded-2xl p-5 shadow-sm border space-y-4">
            <h3 className="font-bold text-navy-900">Create Examination & Timetable</h3>
            <div className="grid sm:grid-cols-4 gap-3">
              <input required placeholder="Exam Name (e.g. Unit Test 2)" value={examForm.name} onChange={(e) => setExamForm({ ...examForm, name: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              <select required value={examForm.class_id} onChange={(e) => setExamForm({ ...examForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">Select Class</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.section})</option>)}
              </select>
              <input type="date" required value={examForm.start_date} onChange={(e) => setExamForm({ ...examForm, start_date: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              <input type="date" required value={examForm.end_date} onChange={(e) => setExamForm({ ...examForm, end_date: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-600 uppercase">Subject Schedule Rows</span>
                <button
                  type="button"
                  onClick={() => setExamForm({ ...examForm, subjects: [...examForm.subjects, { subject_id: "", exam_date: examForm.start_date || "", start_time: "10:00 AM", duration_minutes: 90, max_marks: 100, passing_marks: 35 }] })}
                  className="text-xs font-semibold text-royal-600"
                >
                  + Add Subject Row
                </button>
              </div>
              {examForm.subjects.map((sub, idx) => (
                <div key={idx} className="grid sm:grid-cols-5 gap-2">
                  <select required value={sub.subject_id} onChange={(e) => {
                    const next = [...examForm.subjects];
                    next[idx].subject_id = e.target.value;
                    setExamForm({ ...examForm, subjects: next });
                  }} className="rounded-lg border px-2.5 py-1.5 text-sm">
                    <option value="">Subject</option>
                    {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                  <input type="date" required value={sub.exam_date} onChange={(e) => {
                    const next = [...examForm.subjects];
                    next[idx].exam_date = e.target.value;
                    setExamForm({ ...examForm, subjects: next });
                  }} className="rounded-lg border px-2.5 py-1.5 text-sm" />
                  <input required placeholder="Time (10:00 AM)" value={sub.start_time} onChange={(e) => {
                    const next = [...examForm.subjects];
                    next[idx].start_time = e.target.value;
                    setExamForm({ ...examForm, subjects: next });
                  }} className="rounded-lg border px-2.5 py-1.5 text-sm" />
                  <input type="number" required placeholder="Duration (min)" value={sub.duration_minutes} onChange={(e) => {
                    const next = [...examForm.subjects];
                    next[idx].duration_minutes = e.target.value;
                    setExamForm({ ...examForm, subjects: next });
                  }} className="rounded-lg border px-2.5 py-1.5 text-sm" />
                  <input type="number" required placeholder="Max Marks" value={sub.max_marks} onChange={(e) => {
                    const next = [...examForm.subjects];
                    next[idx].max_marks = e.target.value;
                    setExamForm({ ...examForm, subjects: next });
                  }} className="rounded-lg border px-2.5 py-1.5 text-sm" />
                </div>
              ))}
            </div>
            <button type="submit" className="px-5 py-2 rounded-xl bg-navy-900 text-white text-sm font-semibold">Create Examination</button>
          </form>

          <div className="space-y-4">
            {exams.map((ex) => (
              <div key={ex.id} className="bg-white rounded-2xl p-5 shadow-sm border">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h4 className="font-bold text-navy-900 text-lg">{ex.name}</h4>
                    <p className="text-xs text-slate-500">{ex.class_name} • {ex.start_date} to {ex.end_date} • Status: {ex.status}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => downloadAuthorizedFile(`/api/admin/examinations/${ex.id}/timetable-pdf`, `AK_Timetable_${ex.id}.pdf`)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-900 text-white text-xs font-semibold"
                    >
                      <Download className="w-3.5 h-3.5" /> Timetable PDF
                    </button>
                    <button
                      onClick={async () => {
                        await api.put(`/api/admin/examinations/${ex.id}`, { is_timetable_published: !ex.is_timetable_published });
                        loadAll();
                      }}
                      className="px-3 py-1.5 rounded-lg border text-xs font-semibold"
                    >
                      {ex.is_timetable_published ? "Unpublish Timetable" : "Publish Timetable"}
                    </button>
                    {ex.status !== "CANCELLED" && (
                      <button
                        onClick={async () => {
                          if (!window.confirm(`Cancel examination "${ex.name}"?`)) return;
                          await api.put(`/api/admin/examinations/${ex.id}`, { status: "CANCELLED" });
                          loadAll();
                        }}
                        className="px-3 py-1.5 rounded-lg bg-red-50 text-red-600 text-xs font-semibold"
                      >
                        Cancel Exam
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-3 grid sm:grid-cols-3 gap-2 text-xs">
                  {ex.subjects.map((es) => (
                    <div key={es.id} className="p-2.5 rounded-lg bg-blue-50/70 border border-blue-100">
                      <div className="font-bold text-navy-900">{es.subject_name}</div>
                      <div>{es.exam_date} • {es.start_time} ({es.duration_minutes}m)</div>
                      <div className="text-royal-700 font-semibold">Max Marks: {es.max_marks}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* RESULT APPROVALS (CRITICAL WORKFLOW) */}
      {tab === "approvals" && (
        <div className="space-y-4">
          <div className="bg-amber-50 border border-gold-400 rounded-2xl p-4 text-sm text-navy-900 flex flex-wrap items-center justify-between gap-3">
            <div>
              <strong>Official Result Governance:</strong> Teacher-submitted marks remain <strong>PENDING</strong> and invisible to students/parents until reviewed and published by the Administrator.
            </div>
            <button
              onClick={() => handleDownloadReport("examination_results", "pdf")}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-navy-900 text-white text-xs font-bold shrink-0"
            >
              <Download className="w-4 h-4" /> Print Overall AK Tuition Marks PDF
            </button>
          </div>
          {approvals.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border">No marks submissions found yet.</div>
          ) : (
            approvals.map((ap) => (
              <div key={ap.id} className="bg-white rounded-2xl p-5 shadow-sm border space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      ap.status === "PUBLISHED" ? "bg-emerald-100 text-emerald-800" :
                      ap.status === "REJECTED" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"
                    }`}>
                      {ap.status}
                    </span>
                    <h4 className="font-bold text-navy-900 text-lg mt-1">{ap.examination_name} — {ap.subject_name}</h4>
                    <p className="text-xs text-slate-500">
                      {ap.class_name} • Submitted by {ap.submitted_by} on {ap.submitted_date.slice(0, 10)}
                      {ap.approved_by && ` • Reviewed by ${ap.approved_by}`}
                    </p>
                    {ap.rejection_reason && <p className="text-xs text-red-600 mt-1">Rejection Reason: {ap.rejection_reason}</p>}
                  </div>
                  {ap.status === "PENDING" && (
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        placeholder="Rejection reason (if rejecting)"
                        value={rejectReasonMap[ap.id] || ""}
                        onChange={(e) => setRejectReasonMap({ ...rejectReasonMap, [ap.id]: e.target.value })}
                        className="rounded-lg border px-3 py-1.5 text-xs min-w-[210px]"
                      />
                      <button
                        onClick={() => handleReviewApproval(ap.id, "APPROVE")}
                        className="inline-flex items-center gap-1 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold"
                      >
                        <Check className="w-4 h-4" /> Approve & Publish
                      </button>
                      <button
                        onClick={() => handleReviewApproval(ap.id, "REJECT")}
                        className="inline-flex items-center gap-1 px-3 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold"
                      >
                        <X className="w-4 h-4" /> Reject
                      </button>
                    </div>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="p-2 text-left">Student ID</th>
                        <th className="p-2 text-left">Name</th>
                        <th className="p-2 text-center">Obtained / Max</th>
                        <th className="p-2 text-center">Grade</th>
                        <th className="p-2 text-left">Remarks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {ap.marks.map((m) => (
                        <tr key={m.id}>
                          <td className="p-2 font-mono font-bold">{m.student_code}</td>
                          <td className="p-2">{m.student_name}</td>
                          <td className="p-2 text-center font-bold">{m.marks_obtained} / {m.max_marks}</td>
                          <td className="p-2 text-center">{m.grade}</td>
                          <td className="p-2">{m.remarks}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* NOTIFICATIONS (SMS & WHATSAPP) */}
      {tab === "notifications" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-4 border flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm">
              <strong>Gateway Status:</strong>{" "}
              SMS (MSG91):{" "}
              <span className={`font-bold ${notifData.mode?.sms_live ? "text-emerald-700" : "text-amber-700"}`}>
                {notifData.mode?.sms_live ? "LIVE CONFIGURED" : "DEMONSTRATION MODE (configure MSG91 key in Settings)"}
              </span>{" "}
              • WhatsApp Cloud:{" "}
              <span className={`font-bold ${notifData.mode?.whatsapp_live ? "text-emerald-700" : "text-amber-700"}`}>
                {notifData.mode?.whatsapp_live ? "LIVE CONFIGURED" : "DEMONSTRATION MODE (configure Meta token in Settings)"}
              </span>
            </div>
          </div>

          <form
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                const res = await api.post("/api/admin/notifications/dispatch", {
                  ...notifForm,
                  class_id: notifForm.class_id ? Number(notifForm.class_id) : null,
                });
                notify(`Dispatched ${res.data.dispatched_count} notification(s). Check delivery status below.`);
                loadAll();
              } catch (err) {
                notify(err.response?.data?.detail || "Dispatch failed.", "error");
              }
            }}
            className="bg-white rounded-2xl p-5 shadow-sm border space-y-3"
          >
            <h3 className="font-bold text-navy-900">Send Parent Notification (SMS / WhatsApp)</h3>
            <div className="grid sm:grid-cols-3 gap-3">
              <select value={notifForm.notification_type} onChange={(e) => setNotifForm({ ...notifForm, notification_type: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="TEST_REMINDER">Test Reminder</option>
                <option value="EXAM_TIMETABLE">Exam Timetable Update</option>
                <option value="FEE_REMINDER">Fee Reminder</option>
                <option value="HOLIDAY">Holiday Announcement</option>
                <option value="PARENT_MEETING">Parent Meeting</option>
                <option value="ANNOUNCEMENT">Academic Announcement</option>
              </select>
              <select value={notifForm.channel} onChange={(e) => setNotifForm({ ...notifForm, channel: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="SMS">SMS (MSG91)</option>
                <option value="WHATSAPP">WhatsApp Business Cloud</option>
                <option value="BOTH">Both SMS & WhatsApp</option>
              </select>
              <select value={notifForm.class_id} onChange={(e) => setNotifForm({ ...notifForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">All Active Students</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.section})</option>)}
              </select>
            </div>
            <textarea
              required
              rows={3}
              value={notifForm.message}
              onChange={(e) => setNotifForm({ ...notifForm, message: e.target.value })}
              placeholder="Message text (supports {student_name} and {student_code} placeholders)..."
              className="w-full rounded-lg border px-3 py-2 text-sm"
            />
            <button type="submit" className="px-5 py-2 rounded-xl bg-navy-900 text-white text-sm font-semibold">Dispatch Notifications</button>
          </form>

          <div className="bg-white rounded-2xl shadow-sm border overflow-x-auto">
            <div className="p-4 border-b font-bold text-navy-900">Notification Delivery History</div>
            <table className="w-full text-xs">
              <thead className="bg-slate-100 uppercase">
                <tr>
                  <th className="p-3 text-left">Time</th>
                  <th className="p-3 text-left">Phone</th>
                  <th className="p-3 text-left">Channel</th>
                  <th className="p-3 text-left">Type</th>
                  <th className="p-3 text-left">Status / Provider</th>
                  <th className="p-3 text-left">Message & Delivery Detail</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {notifData.notifications.map((n) => (
                  <tr key={n.id}>
                    <td className="p-3 whitespace-nowrap">{n.created_at.slice(0, 16).replace("T", " ")}</td>
                    <td className="p-3 font-mono">{n.recipient_phone}</td>
                    <td className="p-3 font-bold">{n.channel}</td>
                    <td className="p-3">{n.notification_type}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded font-bold ${
                        n.status === "SENT" ? "bg-emerald-100 text-emerald-800" :
                        n.status === "DEMO_SIMULATED" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-700"
                      }`}>
                        {n.status}
                      </span>
                      <div className="text-[10px] text-slate-500 mt-0.5">{n.provider}</div>
                    </td>
                    <td className="p-3">
                      <div>{n.message}</div>
                      {n.error_detail && <div className="text-[11px] text-amber-700 mt-0.5">{n.error_detail}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ANNOUNCEMENTS */}
      {tab === "announcements" && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await api.post("/api/admin/announcements", { ...annForm, event_date: annForm.event_date || null });
              notify("Announcement published to portal & homepage.");
              setAnnForm({ title: "", category: "NOTICE", content: "", event_date: "", target_audience: "PUBLIC", is_featured: false });
              loadAll();
            }}
            className="bg-white rounded-2xl p-5 shadow-sm border space-y-3"
          >
            <h3 className="font-bold text-navy-900">Publish News, Events & Announcements</h3>
            <div className="grid sm:grid-cols-4 gap-3">
              <input required placeholder="Title" value={annForm.title} onChange={(e) => setAnnForm({ ...annForm, title: e.target.value })} className="sm:col-span-2 rounded-lg border px-3 py-2 text-sm" />
              <select value={annForm.category} onChange={(e) => setAnnForm({ ...annForm, category: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="EXAM_DATE">Upcoming Exam Date</option>
                <option value="TEST_SCHEDULE">Test Schedule</option>
                <option value="HOLIDAY">Holiday</option>
                <option value="PARENT_MEETING">Parent Meeting</option>
                <option value="ADMISSION">Admission</option>
                <option value="ACADEMIC_EVENT">Academic Event</option>
                <option value="NEWS">Latest News</option>
                <option value="NOTICE">Important Notice</option>
              </select>
              <input type="date" value={annForm.event_date} onChange={(e) => setAnnForm({ ...annForm, event_date: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
            </div>
            <textarea required rows={3} placeholder="Announcement details..." value={annForm.content} onChange={(e) => setAnnForm({ ...annForm, content: e.target.value })} className="w-full rounded-lg border px-3 py-2 text-sm" />
            <button type="submit" className="px-5 py-2 rounded-xl bg-navy-900 text-white text-sm font-semibold">Publish Announcement</button>
          </form>

          <div className="grid md:grid-cols-2 gap-4">
            {announcements.map((a) => (
              <div key={a.id} className="bg-white rounded-2xl p-4 shadow-sm border flex justify-between gap-3">
                <div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-royal-700">{a.category}</span>
                  <h4 className="font-bold text-navy-900 mt-1">{a.title}</h4>
                  <p className="text-xs text-slate-600 mt-1">{a.content}</p>
                  {a.event_date && <div className="text-[11px] text-slate-400 mt-1">Event Date: {a.event_date}</div>}
                </div>
                <button
                  onClick={async () => {
                    await api.delete(`/api/admin/announcements/${a.id}`);
                    loadAll();
                  }}
                  className="p-2 h-fit rounded-lg bg-red-50 text-red-600"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 13 ADMIN REPORTS */}
      {tab === "reports" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
            <h3 className="font-bold text-navy-900">Report Filters</h3>
            <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <select value={reportFilters.class_id} onChange={(e) => setReportFilters({ ...reportFilters, class_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">All Classes</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.section})</option>)}
              </select>
              <select value={reportFilters.student_id} onChange={(e) => setReportFilters({ ...reportFilters, student_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">All Students</option>
                {students.map((s) => <option key={s.id} value={s.id}>{s.student_code} - {s.student_name}</option>)}
              </select>
              <select value={reportFilters.examination_id} onChange={(e) => setReportFilters({ ...reportFilters, examination_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">All Examinations</option>
                {exams.map((ex) => <option key={ex.id} value={ex.id}>{ex.name}</option>)}
              </select>
              <select value={reportFilters.subject_id} onChange={(e) => setReportFilters({ ...reportFilters, subject_id: e.target.value })} className="rounded-lg border px-3 py-2 text-sm">
                <option value="">All Subjects</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
              <input type="date" value={reportFilters.start_date} onChange={(e) => setReportFilters({ ...reportFilters, start_date: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
              <input type="date" value={reportFilters.end_date} onChange={(e) => setReportFilters({ ...reportFilters, end_date: e.target.value })} className="rounded-lg border px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {REPORT_LIST.map((r) => (
              <div key={r.id} className="bg-white rounded-2xl p-4 shadow-sm border flex flex-col justify-between gap-3">
                <div className="font-bold text-navy-900 text-sm">{r.label}</div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDownloadReport(r.id, "pdf")}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-navy-900 text-white text-xs font-semibold"
                  >
                    <Download className="w-3.5 h-3.5" /> PDF
                  </button>
                  {!r.pdfOnly && (
                    <button
                      onClick={() => handleDownloadReport(r.id, "xlsx")}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-700 text-white text-xs font-semibold"
                    >
                      <FileSpreadsheet className="w-3.5 h-3.5" /> Excel
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SETTINGS & AUDIT LOGS */}
      {tab === "settings" && settings && (
        <div className="space-y-6">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await api.put("/api/admin/settings", settings);
              notify("Institution & gateway settings saved.");
              loadAll();
            }}
            className="bg-white rounded-2xl p-6 shadow-sm border space-y-4"
          >
            <h3 className="font-bold text-navy-900 text-lg">Institution, Signature & Gateway Settings</h3>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Tuition Name</label>
                <input value={settings.tuition_name} onChange={(e) => setSettings({ ...settings, tuition_name: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Director Name</label>
                <input value={settings.director_name} onChange={(e) => setSettings({ ...settings, director_name: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Director Designation</label>
                <input value={settings.director_designation} onChange={(e) => setSettings({ ...settings, director_designation: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Phone</label>
                <input value={settings.phone} onChange={(e) => setSettings({ ...settings, phone: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Email</label>
                <input value={settings.email} onChange={(e) => setSettings({ ...settings, email: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Academic Year</label>
                <input value={settings.academic_year_label} onChange={(e) => setSettings({ ...settings, academic_year_label: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
              <div className="sm:col-span-2 lg:col-span-3">
                <label className="block text-xs font-semibold text-slate-600 mb-1">Campus Address</label>
                <input value={settings.address} onChange={(e) => setSettings({ ...settings, address: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 pt-3 border-t">
              <div className="p-4 rounded-xl bg-slate-50 border space-y-2">
                <div className="font-bold text-sm text-navy-900">Director Authorized Signature Image</div>
                <p className="text-xs text-slate-500">
                  {settings.director_signature_path ? "Authorized signature image uploaded." : "No signature image uploaded yet (clean placeholder shown on Marks Cards)."}
                </p>
                <input
                  type="file"
                  accept="image/*"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    const fd = new FormData();
                    fd.append("file", file);
                    await api.post("/api/admin/settings/signature", fd);
                    notify("Director signature uploaded.");
                    loadAll();
                  }}
                  className="text-xs"
                />
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border space-y-2 text-xs">
                <div className="font-bold text-sm text-navy-900">SMS (MSG91) & WhatsApp Cloud Credentials</div>
                <div className="flex gap-4">
                  <label className="inline-flex items-center gap-1.5">
                    <input type="checkbox" checked={settings.sms_enabled} onChange={(e) => setSettings({ ...settings, sms_enabled: e.target.checked })} />
                    Enable Live SMS
                  </label>
                  <label className="inline-flex items-center gap-1.5">
                    <input type="checkbox" checked={settings.whatsapp_enabled} onChange={(e) => setSettings({ ...settings, whatsapp_enabled: e.target.checked })} />
                    Enable Live WhatsApp
                  </label>
                </div>
                <input
                  placeholder={settings.has_msg91_auth_key ? "MSG91 Auth Key (configured — leave blank to keep)" : "MSG91 Auth Key"}
                  onChange={(e) => setSettings({ ...settings, msg91_auth_key: e.target.value })}
                  className="w-full rounded border px-2.5 py-1.5"
                />
                <input
                  placeholder="WhatsApp Phone Number ID"
                  value={settings.whatsapp_phone_number_id || ""}
                  onChange={(e) => setSettings({ ...settings, whatsapp_phone_number_id: e.target.value })}
                  className="w-full rounded border px-2.5 py-1.5"
                />
                <input
                  placeholder={settings.has_whatsapp_access_token ? "WhatsApp Access Token (configured)" : "WhatsApp Cloud Access Token"}
                  onChange={(e) => setSettings({ ...settings, whatsapp_access_token: e.target.value })}
                  className="w-full rounded border px-2.5 py-1.5"
                />
              </div>
            </div>

            <button type="submit" className="px-6 py-2.5 rounded-xl bg-navy-900 text-white text-sm font-bold">Save All Settings</button>
          </form>

          <div className="bg-white rounded-2xl p-5 shadow-sm border">
            <h3 className="font-bold text-navy-900 mb-3">System Audit Logs</h3>
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-xs">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="p-2 text-left">Timestamp</th>
                    <th className="p-2 text-left">User</th>
                    <th className="p-2 text-left">Action</th>
                    <th className="p-2 text-left">Entity</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {auditLogs.map((l) => (
                    <tr key={l.id}>
                      <td className="p-2">{l.created_at.slice(0, 19).replace("T", " ")}</td>
                      <td className="p-2 font-semibold">{l.user}</td>
                      <td className="p-2 font-mono">{l.action}</td>
                      <td className="p-2">{l.entity_type} {l.entity_id ? `#${l.entity_id}` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ADD / EDIT STUDENT MODAL */}
      {studentModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg text-navy-900">
                {editingStudent ? `Edit Student (${editingStudent.student_code})` : "Register New Student (Auto AK ID)"}
              </h3>
              <button onClick={() => setStudentModal(false)}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSaveStudent} className="grid sm:grid-cols-2 gap-3 text-sm">
              <input required placeholder="Student Full Name" value={studentForm.student_name} onChange={(e) => setStudentForm({ ...studentForm, student_name: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input type="date" value={studentForm.date_of_birth} onChange={(e) => setStudentForm({ ...studentForm, date_of_birth: e.target.value })} className="rounded-lg border px-3 py-2" />
              <select value={studentForm.gender} onChange={(e) => setStudentForm({ ...studentForm, gender: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
              <select required value={studentForm.class_id} onChange={(e) => setStudentForm({ ...studentForm, class_id: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="">Select Class</option>
                {classes.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.section})</option>)}
              </select>
              <input placeholder="Section" value={studentForm.section} onChange={(e) => setStudentForm({ ...studentForm, section: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input placeholder="Student Phone" value={studentForm.student_phone} onChange={(e) => setStudentForm({ ...studentForm, student_phone: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input required placeholder="Parent Name" value={studentForm.parent_name} onChange={(e) => setStudentForm({ ...studentForm, parent_name: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input required placeholder="Parent Phone" value={studentForm.parent_phone} onChange={(e) => setStudentForm({ ...studentForm, parent_phone: e.target.value })} className="rounded-lg border px-3 py-2" />
              <input type="number" placeholder="Total Annual Fees (optional)" value={studentForm.total_fees} onChange={(e) => setStudentForm({ ...studentForm, total_fees: e.target.value })} className="rounded-lg border px-3 py-2" />
              <select value={studentForm.assigned_teacher_id || ""} onChange={(e) => setStudentForm({ ...studentForm, assigned_teacher_id: e.target.value })} className="rounded-lg border px-3 py-2">
                <option value="">Assign Teacher (optional)</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.teacher_name}</option>)}
              </select>
              <input placeholder="Address" value={studentForm.address} onChange={(e) => setStudentForm({ ...studentForm, address: e.target.value })} className="sm:col-span-2 rounded-lg border px-3 py-2" />
              {!editingStudent && (
                <>
                  <input placeholder="Student Password (auto-unique if blank)" value={studentForm.student_password || ""} onChange={(e) => setStudentForm({ ...studentForm, student_password: e.target.value })} className="rounded-lg border px-3 py-2" />
                  <input placeholder="Parent Password (auto-unique if blank)" value={studentForm.parent_password || ""} onChange={(e) => setStudentForm({ ...studentForm, parent_password: e.target.value })} className="rounded-lg border px-3 py-2" />
                </>
              )}
              <div className="sm:col-span-2 flex justify-end gap-2 pt-3">
                <button type="button" onClick={() => setStudentModal(false)} className="px-4 py-2 rounded-lg border">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-lg bg-navy-900 text-white font-semibold">
                  {editingStudent ? "Save Changes" : "Create Student"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RECORD PAYMENT MODAL */}
      {paymentModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-navy-900">Record Fee Payment — {paymentModal.student_name}</h3>
              <button onClick={() => setPaymentModal(null)}><X className="w-5 h-5" /></button>
            </div>
            <p className="text-xs text-slate-500 mb-3">Pending Balance: ₹{paymentModal.pending_amount.toLocaleString("en-IN")}</p>
            <form onSubmit={handleRecordPayment} className="space-y-3 text-sm">
              <input type="number" step="0.01" required placeholder="Amount (₹)" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              <select value={paymentForm.payment_mode} onChange={(e) => setPaymentForm({ ...paymentForm, payment_mode: e.target.value })} className="w-full rounded-lg border px-3 py-2">
                <option value="CASH">Cash</option>
                <option value="UPI">UPI</option>
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="OTHER">Other</option>
              </select>
              <input placeholder="Transaction Reference Number (prevents duplicates)" value={paymentForm.reference_number} onChange={(e) => setPaymentForm({ ...paymentForm, reference_number: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              <input placeholder="Remarks" value={paymentForm.remarks} onChange={(e) => setPaymentForm({ ...paymentForm, remarks: e.target.value })} className="w-full rounded-lg border px-3 py-2" />
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setPaymentModal(null)} className="px-4 py-2 rounded-lg border">Cancel</button>
                <button type="submit" className="px-5 py-2 rounded-lg bg-emerald-700 text-white font-semibold">Save & Issue Receipt</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* STUDENT ACADEMIC HISTORY MODAL */}
      {historyModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold text-lg text-navy-900">
                Academic Profile — {historyModal.student.student_name} ({historyModal.student.student_code})
              </h3>
              <button onClick={() => setHistoryModal(null)}><X className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-3 gap-3 bg-blue-50 p-3 rounded-xl text-xs">
              <div><strong>Attendance:</strong> {historyModal.attendance.percentage}% ({historyModal.attendance.present_days}/{historyModal.attendance.total_working_days})</div>
              <div><strong>Class:</strong> {historyModal.student.class_name}</div>
              <div><strong>Parent:</strong> {historyModal.student.parent_name}</div>
            </div>
            <div>
              <h4 className="font-bold text-xs uppercase text-slate-500 mb-2">Examination Marks</h4>
              <div className="space-y-1 text-xs">
                {historyModal.marks.map((m) => (
                  <div key={m.id} className="flex justify-between p-2 bg-slate-50 rounded">
                    <span>{m.examination} — {m.subject}</span>
                    <span className="font-bold">{m.marks_obtained}/{m.max_marks} ({m.grade}) [{m.status}]</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* GENERATED / RESET LOGIN CREDENTIALS MODAL */}
      {credentialsModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <div className="flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-navy-900" />
                <h3 className="font-bold text-navy-900">{credentialsModal.title}</h3>
              </div>
              <button onClick={() => setCredentialsModal(null)}><X className="w-5 h-5" /></button>
            </div>
            <p className="text-xs text-slate-600">
              Share these unique login details securely with the user. Passwords are encrypted in the database and cannot be viewed later once closed.
            </p>
            {credentialsModal.type === "student_parent" ? (
              <div className="space-y-3 text-xs">
                <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 space-y-1">
                  <div className="font-bold text-navy-900 uppercase">Student Portal Login</div>
                  <div>Student ID / Username: <strong className="font-mono text-sm">{credentialsModal.data.student_username}</strong></div>
                  <div>Unique Password: <strong className="font-mono text-sm text-emerald-700">{credentialsModal.data.student_password}</strong></div>
                </div>
                <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 space-y-1">
                  <div className="font-bold text-navy-900 uppercase">Parent Portal Login</div>
                  <div>Registered Phone / Username: <strong className="font-mono text-sm">{credentialsModal.data.parent_phone}</strong> (or <strong>{credentialsModal.data.parent_username}</strong>)</div>
                  <div>
                    Unique Password:{" "}
                    <strong className="font-mono text-sm text-emerald-700">
                      {credentialsModal.data.parent_password || "Existing parent account retained"}
                    </strong>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 space-y-1 text-xs">
                <div className="font-bold text-navy-900 uppercase">Teacher Portal Login</div>
                <div>Teacher Code: <strong>{credentialsModal.data.teacher_code}</strong></div>
                <div>Username: <strong className="font-mono text-sm">{credentialsModal.data.username}</strong></div>
                <div>Unique Access Key / Password: <strong className="font-mono text-sm text-emerald-700">{credentialsModal.data.teacher_password}</strong></div>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  const d = credentialsModal.data;
                  const text =
                    credentialsModal.type === "student_parent"
                      ? `AK TUITION PORTAL LOGIN\nStudent: ${d.student_name} (${d.student_username})\nStudent Password: ${d.student_password}\nParent Login: ${d.parent_phone} / ${d.parent_username}\nParent Password: ${d.parent_password || "(existing account)"}`
                      : `AK TUITION TEACHER PORTAL\nName: ${d.teacher_name} (${d.teacher_code})\nUsername: ${d.username}\nAccess Key: ${d.teacher_password}`;
                  navigator.clipboard?.writeText(text);
                  notify("Login credentials copied to clipboard.");
                }}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-navy-900 text-white text-xs font-semibold"
              >
                <Copy className="w-3.5 h-3.5" /> Copy Details
              </button>
              <button type="button" onClick={() => setCredentialsModal(null)} className="px-4 py-2 rounded-lg border text-xs font-semibold">
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </PortalLayout>
  );
}
