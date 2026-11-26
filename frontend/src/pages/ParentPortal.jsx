import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import {
  LayoutDashboard,
  ClipboardCheck,
  Calendar,
  Award,
  IndianRupee,
  Bell,
  Download,
} from "lucide-react";
import PortalLayout from "../components/PortalLayout";
import MarksCardModal from "../components/MarksCardModal";
import api, { downloadAuthorizedFile, resolveAssetUrl } from "../api/client";

export default function ParentPortal() {
  const [tab, setTab] = useState("dashboard");
  const [data, setData] = useState(null);
  const [selectedChildId, setSelectedChildId] = useState("");
  const [activeMarksCard, setActiveMarksCard] = useState(null);
  const [toast, setToast] = useState("");

  const loadData = async (childId = "") => {
    try {
      const url = childId ? `/api/parent/dashboard?student_id=${childId}` : "/api/parent/dashboard";
      const res = await api.get(url);
      setData(res.data);
      if (!selectedChildId && res.data.selected_child) {
        setSelectedChildId(String(res.data.selected_child.id));
      }
    } catch {}
  };

  useEffect(() => {
    loadData();
  }, []);

  const navItems = [
    { id: "dashboard", label: "Child Overview", icon: LayoutDashboard },
    { id: "attendance", label: "Attendance & Absent Dates", icon: ClipboardCheck },
    { id: "exams", label: "Exam Timetables", icon: Calendar },
    { id: "results", label: "Published Results", icon: Award },
    { id: "notifications", label: "Notifications & Consent", icon: Bell },
  ];

  const child = data?.selected_child;

  return (
    <PortalLayout
      title="Parent Portal"
      subtitle={data ? `Parent: ${data.parent.parent_name}` : "Monitor Child Progress"}
      navItems={navItems}
      activeTab={tab}
      onSelectTab={setTab}
    >
      {toast && <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800">{toast}</div>}

      {/* Child Switcher (if multiple children) */}
      {data?.children?.length > 1 && (
        <div className="mb-4 flex items-center gap-3 bg-white p-3 rounded-xl border">
          <span className="text-xs font-bold text-slate-600">Select Child:</span>
          <select
            value={selectedChildId}
            onChange={(e) => {
              setSelectedChildId(e.target.value);
              loadData(e.target.value);
            }}
            className="rounded-lg border px-3 py-1.5 text-sm font-semibold"
          >
            {data.children.map((c) => (
              <option key={c.id} value={c.id}>{c.student_name} ({c.student_code}) — {c.class_name}</option>
            ))}
          </select>
        </div>
      )}

      {/* DASHBOARD */}
      {tab === "dashboard" && data && child && (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-navy-900 to-royal-700 rounded-2xl p-6 text-white flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {child.photo_path ? (
                <img src={resolveAssetUrl(child.photo_path)} alt={child.student_name} className="w-16 h-16 rounded-full object-cover border-2 border-gold-400" />
              ) : (
                <div className="w-16 h-16 rounded-full bg-gold-500 text-navy-950 font-extrabold text-xl flex items-center justify-center">
                  {child.student_name.slice(0, 2).toUpperCase()}
                </div>
              )}
              <div>
                <div className="text-xs font-bold text-gold-400 uppercase">{child.student_code} • {child.class_name} ({child.section})</div>
                <h2 className="text-2xl font-bold">{child.student_name}</h2>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="bg-white/10 rounded-xl px-4 py-2">
                <div className="text-xs text-blue-200">Attendance</div>
                <div className="text-xl font-extrabold text-gold-300">{data.attendance.attendance_percentage}%</div>
              </div>
              <div className="bg-white/10 rounded-xl px-4 py-2">
                <div className="text-xs text-blue-200">Published Results</div>
                <div className="text-xl font-extrabold text-emerald-300">{data.published_results?.length || 0}</div>
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-2xl p-5 shadow-sm border">
              <h3 className="font-bold text-navy-900 mb-3 text-sm">Subject-Wise Performance (%)</h3>
              <div className="h-60">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.subject_performance}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="subject" fontSize={11} />
                    <YAxis domain={[0, 100]} fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="percentage" fill="#1E40AF" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
              <h3 className="font-bold text-navy-900 text-sm">Recent Announcements</h3>
              {data.announcements.map((a) => (
                <div key={a.id} className="p-3 rounded-xl bg-slate-50 border text-xs">
                  <div className="font-bold text-navy-900">{a.title}</div>
                  <div className="text-slate-600 mt-0.5">{a.content}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ATTENDANCE & DEDICATED ABSENT DETAILS */}
      {tab === "attendance" && data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl p-4 border-l-4 border-navy-900">
              <div className="text-xs text-slate-500 uppercase font-semibold">Working Days</div>
              <div className="text-2xl font-extrabold text-navy-900 mt-1">{data.attendance.total_working_days}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-emerald-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Total Present Days</div>
              <div className="text-2xl font-extrabold text-emerald-700 mt-1">{data.attendance.present_days}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-red-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Total Absent Days</div>
              <div className="text-2xl font-extrabold text-red-600 mt-1">{data.attendance.absent_days}</div>
            </div>
            <div className="bg-white rounded-2xl p-4 border-l-4 border-royal-600">
              <div className="text-xs text-slate-500 uppercase font-semibold">Attendance %</div>
              <div className="text-2xl font-extrabold text-royal-700 mt-1">{data.attendance.attendance_percentage}%</div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-5 shadow-sm border">
            <h3 className="font-bold text-navy-900 mb-3">Absent Dates</h3>
            {data.attendance.absent_details.length === 0 ? (
              <p className="text-sm text-emerald-700 font-medium">No absent dates recorded.</p>
            ) : (
              <table className="w-full max-w-md text-sm border">
                <thead className="bg-navy-900 text-white text-xs uppercase">
                  <tr>
                    <th className="p-2.5 text-left">Absent Date</th>
                    <th className="p-2.5 text-center">Attendance Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.attendance.absent_details.map((row, i) => (
                    <tr key={i}>
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

      {/* EXAM TIMETABLES */}
      {tab === "exams" && data && child && (
        <div className="space-y-4">
          {data.upcoming_examinations.map((ex) => (
            <div key={ex.id} className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
              <div className="flex flex-wrap justify-between items-center gap-2">
                <div>
                  <h4 className="font-bold text-navy-900 text-lg">{ex.name}</h4>
                  <div className="text-xs text-slate-500">{ex.start_date} to {ex.end_date}</div>
                </div>
                <button
                  onClick={() => downloadAuthorizedFile(`/api/parent/children/${child.id}/examinations/${ex.id}/timetable-pdf`, `AK_Timetable_${child.student_code}.pdf`)}
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
                    <div>Max Marks: {s.max_marks}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* PUBLISHED RESULTS & OFFICIAL MARKS CARDS */}
      {tab === "results" && data && child && (
        <div className="space-y-4">
          {data.published_results.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border">No published results yet.</div>
          ) : (
            data.published_results.map((res) => (
              <div key={res.examination_id} className="bg-white rounded-2xl p-5 shadow-sm border flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h4 className="font-bold text-navy-900 text-lg">{res.examination_name}</h4>
                  <p className="text-xs text-slate-600">
                    {res.total_obtained}/{res.total_max} ({res.percentage}%) • Grade: <strong>{res.overall_grade}</strong>
                    {res.class_rank ? <> • Class Rank: <strong className="text-royal-700">#{res.class_rank} / {res.class_total_students}</strong></> : null}
                    {" "}• Status: <strong className="text-emerald-700">{res.result_status}</strong>
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      setActiveMarksCard({
                        ...res,
                        student_name: child.student_name,
                        student_code: child.student_code,
                        class_name: child.class_name,
                        section: child.section,
                      })
                    }
                    className="px-4 py-2 rounded-xl bg-navy-900 text-gold-400 text-xs font-bold"
                  >
                    View Marks Card
                  </button>
                  <button
                    onClick={() => downloadAuthorizedFile(`/api/parent/children/${child.id}/results/${res.examination_id}/marks-card-pdf`, `AK_MarksCard_${child.student_code}_Exam${res.examination_id}.pdf`)}
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

      {/* NOTIFICATIONS & CONSENT */}
      {tab === "notifications" && data && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-5 shadow-sm border flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-navy-900">WhatsApp &amp; SMS Notification Preferences</h3>
              <p className="text-xs text-slate-500">Manage consent for examination, result, and attendance alerts.</p>
            </div>
            <div className="flex gap-4 text-sm">
              <label className="inline-flex items-center gap-2 font-medium">
                <input
                  type="checkbox"
                  checked={data.parent.sms_consent}
                  onChange={async (e) => {
                    await api.put("/api/parent/consent", { sms_consent: e.target.checked, whatsapp_consent: data.parent.whatsapp_consent });
                    setToast("Notification preferences updated.");
                    loadData(selectedChildId);
                  }}
                />
                SMS Alerts
              </label>
              <label className="inline-flex items-center gap-2 font-medium">
                <input
                  type="checkbox"
                  checked={data.parent.whatsapp_consent}
                  onChange={async (e) => {
                    await api.put("/api/parent/consent", { sms_consent: data.parent.sms_consent, whatsapp_consent: e.target.checked });
                    setToast("Notification preferences updated.");
                    loadData(selectedChildId);
                  }}
                />
                WhatsApp Alerts
              </label>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-5 shadow-sm border space-y-3">
            <h3 className="font-bold text-navy-900">Received Notifications</h3>
            {data.notifications.length === 0 ? (
              <p className="text-sm text-slate-500">No notifications sent to your account yet.</p>
            ) : (
              data.notifications.map((n) => (
                <div key={n.id} className="p-3.5 rounded-xl bg-slate-50 border text-xs space-y-1">
                  <div className="flex justify-between font-bold">
                    <span className="text-navy-900">{n.channel} • {n.notification_type}</span>
                    <span className="text-royal-700">{n.status}</span>
                  </div>
                  <div className="text-slate-700">{n.message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <MarksCardModal
        result={activeMarksCard}
        pdfUrl={activeMarksCard && child ? `/api/parent/children/${child.id}/results/${activeMarksCard.examination_id}/marks-card-pdf` : null}
        onClose={() => setActiveMarksCard(null)}
      />
    </PortalLayout>
  );
}
