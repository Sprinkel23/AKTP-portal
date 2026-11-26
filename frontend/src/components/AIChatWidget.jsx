import React, { useState } from "react";
import { Bot, Send, X, Sparkles } from "lucide-react";
import api from "../api/client";

const QUICK_PROMPTS = [
  "How to check result with USN & Captcha?",
  "Show my attendance & marks",
  "Upcoming exam dates",
  "Contact Director G. Akash",
];

export default function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello! I am AKTP AI Assistant. Ask me about exam results (/results), Statement of Marks cards, attendance, timetables, or study help.",
    },
  ]);

  const ask = async (questionText) => {
    const q = (questionText || input).trim();
    if (!q || sending) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setSending(true);
    try {
      const res = await api.post("/api/public/ai-assistant", { message: q });
      setMessages((prev) => [...prev, { role: "assistant", text: res.data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Unable to reach AKTP AI Assistant right now. Visit /results for exam results or contact +91 72042 09785.",
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="no-print fixed bottom-5 right-5 z-50">
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-3 rounded-full bg-[#0A2463] hover:bg-[#1E40AF] text-white shadow-xl border-2 border-[#D4AF37] text-xs sm:text-sm font-bold transition"
        >
          <Bot className="w-5 h-5 text-[#D4AF37]" />
          <span>AKTP AI Help Bot</span>
        </button>
      ) : (
        <div className="w-[330px] sm:w-[370px] bg-white rounded-2xl shadow-2xl border-2 border-[#0A2463] overflow-hidden flex flex-col max-h-[500px]">
          <div className="bg-[#0A2463] text-white px-4 py-3 flex items-center justify-between border-b-2 border-[#D4AF37]">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#D4AF37]" />
              <div>
                <div className="font-bold text-sm leading-tight">AKTP AI Academic Bot</div>
                <div className="text-[10px] text-blue-200">AK Tuition Official Assistant</div>
              </div>
            </div>
            <button type="button" onClick={() => setOpen(false)} className="p-1 rounded hover:bg-white/10" aria-label="Close AI assistant">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-3 space-y-2.5 overflow-y-auto flex-1 bg-slate-50 text-xs">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`p-2.5 rounded-xl whitespace-pre-line leading-relaxed ${
                  m.role === "user"
                    ? "bg-[#0A2463] text-white ml-8"
                    : "bg-white border border-slate-200 text-slate-800 mr-6 shadow-sm"
                }`}
              >
                {m.text}
              </div>
            ))}
            {sending && (
              <div className="p-2 rounded-xl bg-white border text-slate-500 mr-8 italic">
                Thinking...
              </div>
            )}
          </div>

          <div className="px-3 py-1.5 bg-white border-t flex flex-wrap gap-1">
            {QUICK_PROMPTS.map((qp) => (
              <button
                key={qp}
                type="button"
                onClick={() => ask(qp)}
                className="text-[10px] px-2 py-1 rounded-full bg-blue-50 text-[#0A2463] hover:bg-blue-100 font-semibold border border-blue-200"
              >
                {qp}
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask();
            }}
            className="p-2.5 bg-white border-t flex gap-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about results, attendance, exams..."
              className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs outline-none focus:border-[#0A2463]"
            />
            <button
              type="submit"
              disabled={sending}
              className="px-3 py-1.5 rounded-lg bg-[#0A2463] text-white text-xs font-bold inline-flex items-center gap-1 disabled:opacity-60"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
