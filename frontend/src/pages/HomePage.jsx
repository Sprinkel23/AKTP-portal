import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Award,
  BookOpen,
  Calendar,
  CheckCircle2,
  ClipboardList,
  GraduationCap,
  Mail,
  MapPin,
  Menu,
  Newspaper,
  Phone,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import api from "../api/client";

export default function HomePage() {
  const [data, setData] = useState(null);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [contact, setContact] = useState({ name: "", phone: "", email: "", student_class: "", message: "" });
  const [contactStatus, setContactStatus] = useState("");

  useEffect(() => {
    api
      .get("/api/public/home")
      .then((res) => setData(res.data))
      .catch(() => {});
  }, []);

  const inst = data?.institution || {
    tuition_name: "AK TUITION",
    tagline: "Learn • Practise • Achieve",
    director_name: "G. Akash, B.E.",
    phone: "+91 72042 09785",
    email: "akashgakash140@gmail.com",
    address: "AK Tuition Campus, Bengaluru, Karnataka, India",
  };

  const announcements = data?.announcements || [];
  const newsItems = announcements.filter((a) => ["NEWS", "ADMISSION", "NOTICE", "HOLIDAY"].includes(a.category));
  const eventItems = announcements.filter((a) => ["ACADEMIC_EVENT", "PARENT_MEETING", "TEST_SCHEDULE", "EXAM_DATE"].includes(a.category));

  const handleContact = async (e) => {
    e.preventDefault();
    setContactStatus("");
    try {
      const res = await api.post("/api/public/contact", contact);
      setContactStatus(res.data.message);
      setContact({ name: "", phone: "", email: "", student_class: "", message: "" });
    } catch {
      setContactStatus("Could not submit right now. Please call us directly.");
    }
  };

  const navLinks = [
    { label: "Home", href: "#home" },
    { label: "About Us", href: "#about" },
    { label: "Courses", href: "#courses" },
    { label: "Classes", href: "#classes" },
    { label: "Examinations", href: "#examinations" },
    { label: "News", href: "#news" },
    { label: "Events", href: "#events" },
    { label: "Contact Us", href: "#contact" },
  ];

  return (
    <div className="min-h-screen bg-white text-slate-800">
      {/* Top Announcement / Contact Strip */}
      <div className="bg-navy-900 text-blue-100 text-xs py-2 px-4 border-b border-gold-500/30">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-gold-400" /> {inst.phone}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Mail className="w-3.5 h-3.5 text-gold-400" /> {inst.email}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-gold-400 font-semibold">AKTP PORTAL • Learn • Practise • Achieve</span>
            <Link to="/login/student" className="hover:text-white underline">
              Student Login
            </Link>
            <Link to="/login/parent" className="hover:text-white underline">
              Parent Login
            </Link>
          </div>
        </div>
      </div>

      {/* Main Sticky Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <a href="#home" className="flex items-center gap-3 shrink-0">
            <img
              src="/ak-tuition-logo.png"
              alt="AK Tuition Circular Logo"
              className="w-12 h-12 sm:w-14 sm:h-14 object-contain"
            />
            <div>
              <div className="font-display font-extrabold text-lg sm:text-xl text-navy-900 leading-tight">
                {inst.tuition_name}
              </div>
              <div className="text-[11px] font-semibold tracking-wider text-royal-600 uppercase">
                {inst.tagline}
              </div>
            </div>
          </a>

          <nav className="hidden xl:flex items-center gap-6 text-sm font-medium text-slate-700">
            {navLinks.map((n) => (
              <a key={n.label} href={n.href} className="hover:text-royal-600 transition">
                {n.label}
              </a>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-2.5">
            <Link
              to="/login"
              className="px-4 py-2 rounded-full bg-navy-900 hover:bg-royal-600 text-white text-sm font-semibold transition shadow-sm"
            >
              Portal Login
            </Link>
            <a
              href="#contact"
              className="px-4 py-2 rounded-full bg-gold-500 hover:bg-gold-400 text-navy-950 text-sm font-bold transition shadow-sm"
            >
              Enquire Now
            </a>
          </div>

          <button
            onClick={() => setMobileMenu(!mobileMenu)}
            className="xl:hidden p-2 rounded-lg border border-slate-200 text-navy-900"
            aria-label="Toggle Menu"
          >
            {mobileMenu ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {mobileMenu && (
          <div className="xl:hidden bg-white border-t border-slate-200 px-4 py-4 space-y-2">
            {navLinks.map((n) => (
              <a
                key={n.label}
                href={n.href}
                onClick={() => setMobileMenu(false)}
                className="block py-2 text-sm font-medium text-slate-700 hover:text-royal-600"
              >
                {n.label}
              </a>
            ))}
            <div className="pt-2 flex flex-wrap gap-2">
              <Link to="/login/student" className="px-4 py-2 rounded-lg bg-royal-600 text-white text-sm font-semibold">
                Student Login
              </Link>
              <Link to="/login/parent" className="px-4 py-2 rounded-lg bg-navy-900 text-white text-sm font-semibold">
                Parent Login
              </Link>
              <Link to="/login" className="px-4 py-2 rounded-lg bg-gold-500 text-navy-950 text-sm font-bold">
                All Portals
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* HERO SECTION (EduAll inspired) */}
      <section id="home" className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-14 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-6 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-royal-500/20 shadow-sm text-xs font-semibold text-royal-600">
              <Sparkles className="w-4 h-4 text-gold-500" />
              Director: {inst.director_name} • Classes 1 to 10
            </div>
            <h1 className="font-display text-3xl sm:text-5xl font-extrabold text-navy-900 leading-tight">
              Learning Made Simple.{" "}
              <span className="text-royal-600">Success Made Possible.</span>
            </h1>
            <p className="text-base sm:text-lg text-slate-600 leading-relaxed">
              Quality Education, Personal Guidance and Academic Excellence for Every Student.
            </p>

            {/* 4 Required Hero Buttons */}
            <div className="flex flex-wrap gap-3 pt-2">
              <a
                href="#tutors"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-royal-600 hover:bg-royal-700 text-white font-semibold text-sm shadow-md transition"
              >
                Find Your Tutor <ArrowRight className="w-4 h-4" />
              </a>
              <a
                href="#courses"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-gold-500 hover:bg-gold-400 text-navy-950 font-bold text-sm shadow-md transition"
              >
                Explore Courses
              </a>
              <Link
                to="/login/student"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-navy-900 hover:bg-navy-800 text-white font-semibold text-sm shadow transition"
              >
                Student Login
              </Link>
              <Link
                to="/login/parent"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-white border-2 border-navy-900 text-navy-900 hover:bg-blue-50 font-semibold text-sm transition"
              >
                Parent Login
              </Link>
            </div>

            {/* Live Quick Stats */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-200/80">
              <div>
                <div className="text-2xl font-extrabold text-navy-900">1–10</div>
                <div className="text-xs text-slate-500 font-medium">Structured Classes</div>
              </div>
              <div>
                <div className="text-2xl font-extrabold text-royal-600">{data?.stats?.total_subjects || 6}+</div>
                <div className="text-xs text-slate-500 font-medium">Core Subjects</div>
              </div>
              <div>
                <div className="text-2xl font-extrabold text-gold-600">98%</div>
                <div className="text-xs text-slate-500 font-medium">Board Distinction</div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6 relative">
            <div className="relative rounded-3xl overflow-hidden shadow-2xl border-4 border-white bg-white">
              <img
                src="/images/hero-education.png"
                alt="AK Tuition Students and Mentor"
                className="w-full h-auto object-cover"
              />
            </div>
            <div className="hidden sm:flex items-center gap-3 bg-white rounded-2xl shadow-xl p-4 border border-slate-100 absolute -bottom-5 -left-4">
              <div className="w-11 h-11 rounded-xl bg-navy-900 text-gold-400 flex items-center justify-center">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <div className="text-sm font-bold text-navy-900">4 Connected Portals</div>
                <div className="text-xs text-slate-500">Admin • Teacher • Student • Parent</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Latest Announcements Ticker */}
      {announcements.length > 0 && (
        <section className="bg-navy-900 text-white py-3.5 px-4">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-3 text-sm">
            <span className="px-3 py-1 rounded-full bg-gold-500 text-navy-950 font-bold text-xs uppercase tracking-wide">
              Latest Notice
            </span>
            <span className="font-medium text-blue-100">
              {announcements[0].title} — {announcements[0].content}
            </span>
          </div>
        </section>
      )}

      {/* 1. ABOUT AK TUITION & 2. TEACHING APPROACH */}
      <section id="about" className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-5">
            <div className="rounded-3xl overflow-hidden shadow-xl border border-blue-100 bg-blue-50">
              <img
                src="/images/about-teaching.png"
                alt="AK Tuition Mentorship Approach"
                className="w-full h-auto object-cover"
              />
            </div>
          </div>
          <div className="lg:col-span-7 space-y-5">
            <span className="text-xs font-bold uppercase tracking-widest text-royal-600">
              About AK Tuition
            </span>
            <h2 className="font-display text-3xl font-bold text-navy-900">
              Building Strong Academic Foundations Under {inst.director_name}
            </h2>
            <p className="text-slate-600 leading-relaxed">
              AK Tuition is dedicated to nurturing curious, confident learners from Classes 1 to 10.
              Through our unified AKTP PORTAL, teachers, students, and parents stay aligned on daily
              attendance, concept mastery, practice assessments, and official examination milestones.
            </p>
            <div className="grid sm:grid-cols-2 gap-4 pt-2">
              {[
                { title: "Learn with Clarity", desc: "Concept-first explanations tailored to every student's pace." },
                { title: "Practise Consistently", desc: "Topic-wise worksheets, question banks, and timed online tests." },
                { title: "Achieve Excellence", desc: "Regular evaluations, official marks cards, and remedial coaching." },
                { title: "Transparent Parent Connect", desc: "Real-time attendance alerts, fee receipts, and published results." },
              ].map((item) => (
                <div key={item.title} className="flex items-start gap-3 p-4 rounded-2xl bg-blue-50/70 border border-blue-100">
                  <CheckCircle2 className="w-5 h-5 text-royal-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-navy-900 text-sm">{item.title}</h4>
                    <p className="text-xs text-slate-600 mt-1">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 3. COURSES & 4. CLASSES 1–10 */}
      <section id="classes" className="py-16 bg-blue-50/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="text-xs font-bold uppercase tracking-widest text-royal-600">
              Classes 1–10
            </span>
            <h2 className="font-display text-3xl font-bold text-navy-900 mt-1">
              Structured Coaching for Every Grade
            </h2>
            <p className="text-sm text-slate-600 mt-2">
              Dedicated batches for Primary, Middle School, and High School Board preparation.
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {(data?.classes?.length ? data.classes : Array.from({ length: 10 }, (_, i) => ({ id: i + 1, name: `Class ${i + 1}`, section: "A" }))).map((c) => (
              <div
                key={c.id}
                className="bg-white rounded-2xl p-5 border border-slate-200 hover:border-royal-500 hover:shadow-lg transition text-center"
              >
                <div className="w-11 h-11 mx-auto rounded-xl bg-navy-900 text-gold-400 flex items-center justify-center font-extrabold">
                  {c.grade_level || c.id}
                </div>
                <h3 className="font-bold text-navy-900 mt-3">{c.name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">Section {c.section}</p>
                <div className="mt-3 text-xs font-semibold text-royal-600 bg-blue-50 rounded-full py-1 px-2.5 inline-block">
                  Guided Batch
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. SUBJECTS OFFERED & FACULTY */}
      <section id="courses" className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4 mb-10">
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-royal-600">
                Courses & Subjects Offered
              </span>
              <h2 className="font-display text-3xl font-bold text-navy-900 mt-1">
                Core Curriculum & Expert Tutors
              </h2>
            </div>
            <Link to="/login" className="text-sm font-semibold text-royal-600 hover:underline">
              Access Study & Test Portal →
            </Link>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {(data?.subjects || []).map((s) => (
              <div key={s.id} className="rounded-2xl border border-slate-200 p-6 hover:shadow-lg transition bg-white">
                <div className="flex items-center justify-between">
                  <div className="w-11 h-11 rounded-xl bg-blue-50 text-royal-600 flex items-center justify-center">
                    <BookOpen className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-amber-50 text-gold-600 border border-gold-400/40">
                    {s.code}
                  </span>
                </div>
                <h3 className="font-bold text-lg text-navy-900 mt-4">{s.name}</h3>
                <p className="text-sm text-slate-600 mt-1">{s.description}</p>
              </div>
            ))}
          </div>

          {/* Tutors Strip */}
          <div id="tutors" className="mt-14 bg-navy-900 rounded-3xl p-8 text-white">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="font-display text-2xl font-bold">Meet Our Dedicated Faculty</h3>
                <p className="text-sm text-blue-200">Experienced subject mentors guiding every batch</p>
              </div>
              <a href="#contact" className="px-5 py-2.5 rounded-full bg-gold-500 text-navy-950 font-bold text-sm">
                Book a Demo Class
              </a>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-white/10 rounded-2xl p-5 border border-white/10">
                <div className="text-xs font-bold text-gold-400 uppercase">Founder & Director</div>
                <div className="font-bold text-lg mt-1">{inst.director_name}</div>
                <div className="text-xs text-blue-200 mt-1">Academic Mentorship & Mathematics</div>
              </div>
              {(data?.teachers || []).map((t) => (
                <div key={t.id} className="bg-white/10 rounded-2xl p-5 border border-white/10">
                  <div className="text-xs font-bold text-gold-400 uppercase">{t.qualification || "Faculty"}</div>
                  <div className="font-bold text-lg mt-1">{t.name}</div>
                  <div className="text-xs text-blue-200 mt-1">{t.specialization}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 6. WHY CHOOSE AK TUITION & 10. STUDENT ACHIEVEMENTS */}
      <section className="py-16 bg-gradient-to-r from-navy-950 via-navy-900 to-royal-700 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="font-display text-3xl font-bold">Why Choose AK Tuition?</h2>
            <p className="text-sm text-blue-200 mt-2">
              A complete academic ecosystem combining personal mentorship with digital precision.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Users, stat: "15:1 Ratio", title: "Small Focused Batches", desc: "Individual attention for every learner." },
              { icon: ClipboardList, stat: "Weekly Tests", title: "Practice & Evaluation", desc: "Online MCQs & structured descriptive papers." },
              { icon: Award, stat: "Official Marks Cards", title: "Verified Results", desc: "Director-approved marks cards & PDF downloads." },
              { icon: GraduationCap, stat: "100% Transparency", title: "Parent Portal & Alerts", desc: "Attendance tracking, fees & instant updates." },
            ].map((w) => {
              const Icon = w.icon;
              return (
                <div key={w.title} className="bg-white/10 backdrop-blur rounded-2xl p-6 border border-white/15">
                  <Icon className="w-8 h-8 text-gold-400" />
                  <div className="text-xl font-extrabold text-gold-300 mt-3">{w.stat}</div>
                  <h3 className="font-bold text-base mt-1">{w.title}</h3>
                  <p className="text-xs text-blue-100 mt-1.5">{w.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 7. UPCOMING EXAMINATIONS, 8. LATEST NEWS & 9. UPCOMING EVENTS */}
      <section id="examinations" className="py-16 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-3 gap-8">
          {/* Upcoming Examinations */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-5 h-5 text-royal-600" />
              <h3 className="font-display font-bold text-lg text-navy-900">Upcoming Examinations</h3>
            </div>
            <div className="space-y-3">
              {(data?.upcoming_examinations || []).length === 0 ? (
                <p className="text-sm text-slate-500">No upcoming examinations scheduled yet.</p>
              ) : (
                data.upcoming_examinations.map((ex) => (
                  <div key={ex.id} className="p-3.5 rounded-xl bg-blue-50/70 border border-blue-100">
                    <div className="font-bold text-navy-900 text-sm">{ex.name}</div>
                    <div className="text-xs text-royal-700 font-medium mt-0.5">{ex.class_name}</div>
                    <div className="text-xs text-slate-600 mt-1">
                      {ex.start_date} to {ex.end_date}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Latest News */}
          <div id="news" className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Newspaper className="w-5 h-5 text-gold-600" />
              <h3 className="font-display font-bold text-lg text-navy-900">Latest News & Notices</h3>
            </div>
            <div className="space-y-3">
              {(newsItems.length ? newsItems : announcements).slice(0, 4).map((a) => (
                <div key={a.id} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-navy-900 text-gold-400">
                    {a.category.replace("_", " ")}
                  </span>
                  <div className="font-bold text-navy-900 text-sm mt-1.5">{a.title}</div>
                  <p className="text-xs text-slate-600 mt-1">{a.content}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming Events */}
          <div id="events" className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-royal-600" />
              <h3 className="font-display font-bold text-lg text-navy-900">Upcoming Events</h3>
            </div>
            <div className="space-y-3">
              {(eventItems.length ? eventItems : announcements).slice(0, 4).map((a) => (
                <div key={a.id} className="p-3.5 rounded-xl bg-amber-50/60 border border-gold-400/40">
                  <div className="flex items-center justify-between text-[11px] font-semibold text-gold-600">
                    <span>{a.category.replace("_", " ")}</span>
                    {a.event_date && <span>{a.event_date}</span>}
                  </div>
                  <div className="font-bold text-navy-900 text-sm mt-1">{a.title}</div>
                  <p className="text-xs text-slate-600 mt-1">{a.content}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 12. CONTACT INFORMATION */}
      <section id="contact" className="py-16 bg-blue-50/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-5 space-y-4">
            <span className="text-xs font-bold uppercase tracking-widest text-royal-600">Contact Us</span>
            <h2 className="font-display text-3xl font-bold text-navy-900">Get in Touch With AK Tuition</h2>
            <p className="text-sm text-slate-600">
              Have questions about admissions, class timings, or subjects? Send us a message or visit our campus.
            </p>
            <div className="space-y-3 pt-2 text-sm">
              <div className="flex items-center gap-3">
                <MapPin className="w-5 h-5 text-royal-600" />
                <span>{inst.address}</span>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="w-5 h-5 text-royal-600" />
                <span>{inst.phone}</span>
              </div>
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-royal-600" />
                <span>{inst.email}</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 bg-white rounded-3xl p-6 sm:p-8 shadow-md border border-slate-200">
            <form onSubmit={handleContact} className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Full Name</label>
                <input
                  required
                  value={contact.name}
                  onChange={(e) => setContact({ ...contact, name: e.target.value })}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
                  placeholder="Parent or Student Name"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Phone Number</label>
                <input
                  required
                  value={contact.phone}
                  onChange={(e) => setContact({ ...contact, phone: e.target.value })}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
                  placeholder="+91 98XXXXXXXX"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Email (Optional)</label>
                <input
                  type="email"
                  value={contact.email}
                  onChange={(e) => setContact({ ...contact, email: e.target.value })}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
                  placeholder="name@example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Interested Class</label>
                <input
                  value={contact.student_class}
                  onChange={(e) => setContact({ ...contact, student_class: e.target.value })}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
                  placeholder="e.g. Class 10"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-600 mb-1">Message</label>
                <textarea
                  required
                  rows={3}
                  value={contact.message}
                  onChange={(e) => setContact({ ...contact, message: e.target.value })}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
                  placeholder="Tell us which subjects or batch you are looking for..."
                />
              </div>
              <div className="sm:col-span-2 flex flex-wrap items-center justify-between gap-3">
                <button
                  type="submit"
                  className="px-6 py-2.5 rounded-full bg-navy-900 hover:bg-royal-600 text-white font-semibold text-sm transition"
                >
                  Send Inquiry
                </button>
                {contactStatus && <span className="text-xs font-semibold text-emerald-700">{contactStatus}</span>}
              </div>
            </form>
          </div>
        </div>
      </section>

      {/* 13. FOOTER */}
      <footer className="bg-navy-950 text-blue-100 py-12 px-4 sm:px-6 border-t-4 border-gold-500">
        <div className="max-w-7xl mx-auto grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <img src="/ak-tuition-logo.png" alt="AK Tuition Logo" className="w-12 h-12 object-contain" />
              <div>
                <div className="font-display font-bold text-white text-lg">AK TUITION</div>
                <div className="text-xs text-gold-400">Learn • Practise • Achieve</div>
              </div>
            </div>
            <p className="text-xs text-blue-200/80">
              AKTP PORTAL — Centralized Educational Management System directed by {inst.director_name}.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-white text-sm mb-3">Quick Links</h4>
            <ul className="space-y-1.5 text-xs">
              <li><a href="#about" className="hover:text-gold-400">About Us</a></li>
              <li><a href="#classes" className="hover:text-gold-400">Classes 1–10</a></li>
              <li><a href="#courses" className="hover:text-gold-400">Subjects Offered</a></li>
              <li><a href="#examinations" className="hover:text-gold-400">Examinations</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-white text-sm mb-3">AKTP Portals</h4>
            <ul className="space-y-1.5 text-xs">
              <li><Link to="/login/admin" className="hover:text-gold-400">Administrator Login</Link></li>
              <li><Link to="/login/teacher" className="hover:text-gold-400">Teacher Login</Link></li>
              <li><Link to="/login/student" className="hover:text-gold-400">Student Login</Link></li>
              <li><Link to="/login/parent" className="hover:text-gold-400">Parent Login</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-white text-sm mb-3">Campus Office</h4>
            <p className="text-xs text-blue-200/80">{inst.address}</p>
            <p className="text-xs text-gold-400 mt-2">{inst.phone}</p>
            <p className="text-xs text-blue-200 mt-1">{inst.email}</p>
          </div>
        </div>
        <div className="max-w-7xl mx-auto mt-8 pt-6 border-t border-white/10 text-center text-xs text-blue-300/70">
          © {new Date().getFullYear()} AK Tuition • AKTP PORTAL. All Rights Reserved.
        </div>
      </footer>
    </div>
  );
}
