import { useState } from "react";
import ChatWindow from "../components/ChatWindow";
import VoiceMic from "../components/VoiceMic";
import { assistantVisuals } from "../data/portalContent";

// ---------------------------------------------------------------------------
// Static content — same as original
// ---------------------------------------------------------------------------

const quickHelp = [
  "एक बार में अपनी पूरी जानकारी बताएं।",
  "आप बोलकर या लिखकर जवाब दे सकते हैं।",
  "सहायक आपकी बात समझकर सही योजना बताएगा।",
];

const assistantSupport = [
  {
    title: "शुरू करने से पहले",
    text: "उम्र, कमाई, वर्ग, बैंक खाता और घर की थोड़ी जानकारी पास रखें।",
  },
  {
    title: "आवाज साफ न आए तो",
    text: "आप नीचे लिखकर भी वही जवाब भेज सकते हैं।",
  },
  {
    title: "इससे क्या फायदा है",
    text: "अपनी बात बताने से सही योजना तक पहुंचना आसान हो जाता है।",
  },
];

const assistantFaqs = [
  {
    title: "क्या मैं बोल सकता हूँ?",
    text: "हाँ। आप माइक से बोल सकते हैं, या नीचे लिख भी सकते हैं।",
  },
  {
    title: "सवाल कैसे पूछे जाते हैं?",
    text: "आप अपनी जानकारी बताएं और सहायक आपके लिए योजना ढूंढेगा।",
  },
  {
    title: "अगर बात समझ न आए तो?",
    text: "दोबारा कोशिश करें। जरूरत हो तो लिखकर जवाब दें।",
  },
];

const assistantHeroStats = [
  { label: "क्या पूछा जाए", value: "योजना, हक, मदद" },
  { label: "जवाब कैसे दें", value: "बोलकर या लिखकर" },
  { label: "बात करने का तरीका", value: "आसान और सीधा" },
];

// ---------------------------------------------------------------------------
// Proxy routes (Vite proxies /chat → localhost:8000/chat, same for /reset)
// ---------------------------------------------------------------------------
const CHAT_URL  = "/chat/";
const RESET_URL = "/reset/";

const INITIAL_MESSAGE = {
  sender: "bot",
  text: "स्वागत है। कृपया अपनी जानकारी बताइए — जैसे उम्र, कमाई, वर्ग, किसान हैं या नहीं। मैं आपके लिए सही योजना ढूंढने की कोशिश करूंगा।",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AssistantPage() {
  const [messages, setMessages]     = useState([INITIAL_MESSAGE]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading]   = useState(false);

  // Count only user messages sent so far
  const sentCount = messages.filter((m) => m.sender === "user").length;

  const addMessage = (sender, text) =>
    setMessages((prev) => [...prev, { sender, text }]);

  // ------------------------------------------------------------------
  // Core: send user text → Django backend → show agent reply
  // ------------------------------------------------------------------
  const sendToBackend = async (userMessage) => {
    const msg = userMessage.trim();
    if (!msg || isLoading) return;

    addMessage("user", msg);
    setIsLoading(true);

    try {
      const response = await fetch(CHAT_URL, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message: msg }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();

      // Only show the reply from the agent — nothing else
      if (data.reply) {
        addMessage("bot", data.reply);
      }
    } catch (err) {
      console.error("[chat error]", err);
      addMessage("bot", "माफ़ करें, कुछ त्रुटि हुई। कृपया दोबारा प्रयास करें।");
    } finally {
      setIsLoading(false);
    }
  };

  // ------------------------------------------------------------------
  // Reset: clear Django session profile + restart local chat
  // ------------------------------------------------------------------
  const resetConversation = async () => {
    try {
      await fetch(RESET_URL, { method: "POST" });
    } catch {
      // best-effort — proceed even if reset call fails
    }
    setMessages([INITIAL_MESSAGE]);
    setInputValue("");
    setIsLoading(false);
  };

  // ------------------------------------------------------------------
  // Handlers
  // ------------------------------------------------------------------
  const handleSubmit = (event) => {
    event.preventDefault();
    sendToBackend(inputValue);
    setInputValue("");
  };

  // VoiceMic fires this when it has a final transcript
  const handleSpeech = (transcript) => {
    sendToBackend(transcript);
  };

  // ------------------------------------------------------------------
  // Render — identical visual structure to original AssistantPage
  // ------------------------------------------------------------------
  return (
    <div className="page-fade px-4 py-8 md:px-6">
      <div className="mx-auto max-w-6xl space-y-8">

        {/* ── Hero ─────────────────────────────────────────────────── */}
        <section className="section-rise hero-shell overflow-hidden rounded-[36px] border border-[#d7dee8] px-6 py-8 shadow-sm md:px-10">
          <div className="grid gap-8 lg:grid-cols-[1fr_0.95fr] lg:items-center">
            <div>
              <h1 className="text-4xl font-bold text-[#153a64] md:text-5xl">
                हिंदी वॉइस योजना सहायक
              </h1>
              <p className="mt-5 max-w-3xl text-lg leading-9 text-[#516274]">
                यह पेज बात करने के लिए बना है। अपनी जानकारी बताइए और सहायक
                आपके लिए सही सरकारी योजना ढूंढेगा।
              </p>

              <div className="mt-6 grid gap-3 md:grid-cols-3">
                {quickHelp.map((item, index) => (
                  <div
                    key={item}
                    className={`glass-card rounded-2xl p-5 text-base leading-8 text-[#5b6878] shadow-sm stagger-${index + 1}`}
                  >
                    {item}
                  </div>
                ))}
              </div>

              {/* Message counter replaces the old step-progress pill */}
              <div className="mt-6 inline-block rounded-full bg-[#eaf4ff] px-6 py-3 text-base font-semibold text-[#153a64]">
                {sentCount === 0
                  ? "बात अभी शुरू नहीं हुई"
                  : `${sentCount} संदेश भेजे गए`}
              </div>

              <div className="mt-8 grid gap-4 md:grid-cols-3">
                {assistantHeroStats.map((item, index) => (
                  <div
                    key={item.label}
                    className={`soft-panel rounded-[22px] p-5 shadow-sm stagger-${(index % 3) + 1}`}
                  >
                    <p className="text-sm font-semibold text-[#5b6878]">{item.label}</p>
                    <p className="mt-3 text-lg font-bold text-[#153a64]">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {assistantVisuals.map((item, index) => (
                <article
                  key={item.title}
                  className={`image-feature-card overflow-hidden rounded-[28px] border border-white/70 bg-white/85 shadow-lg ${
                    index === 0 ? "md:col-span-2" : ""
                  }`}
                >
                  <div className="image-wrap h-52 md:h-56">
                    <img
                      src={item.image}
                      alt={item.title}
                      className="h-full w-full object-cover"
                    />
                  </div>
                  <div className="p-5">
                    <h2 className="text-2xl font-bold text-[#153a64]">{item.title}</h2>
                    <p className="mt-3 text-base leading-8 text-[#5b6878]">{item.text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── Chat Window ──────────────────────────────────────────── */}
        <section className="section-rise rounded-[32px] border border-[#d7dee8] bg-white px-4 py-6 shadow-sm md:px-6">
          <ChatWindow messages={messages} />

          <div className="soft-panel mx-auto mt-8 max-w-4xl rounded-[24px] border border-[#dbe4ee] p-6 shadow-sm">
            {/* Voice mic — triggers sendToBackend with spoken transcript */}
            <VoiceMic onSpeech={handleSpeech} />

            {/* Text input */}
            <form
              onSubmit={handleSubmit}
              className="mt-6 flex flex-col gap-3 md:flex-row"
            >
              <input
                type="text"
                value={inputValue}
                onChange={(event) => setInputValue(event.target.value)}
                placeholder="यहां अपनी जानकारी लिखें…"
                disabled={isLoading}
                className="flex-1 rounded-full border border-[#c9d8e7] px-5 py-4 text-lg text-[#153a64] outline-none focus:border-[#1d4ed8] disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="rounded-full bg-[#153a64] px-7 py-4 text-base font-semibold text-white transition hover:bg-[#0f2a45] disabled:opacity-50"
              >
                {isLoading ? "प्रतीक्षा करें…" : "जवाब भेजें"}
              </button>
            </form>

            {/* Always-visible reset button */}
            <div className="mt-6 text-center">
              <button
                onClick={resetConversation}
                className="rounded-full bg-[#1d4ed8] px-7 py-4 text-base font-semibold text-white transition hover:bg-[#153a64]"
              >
                नई बात शुरू करें
              </button>
            </div>
          </div>
        </section>

        {/* ── Support Cards ────────────────────────────────────────── */}
        <section className="section-rise rounded-[32px] border border-[#d7dee8] bg-white px-6 py-8 shadow-sm md:px-8">
          <div className="grid gap-4 md:grid-cols-3">
            {assistantSupport.map((item, index) => (
              <div
                key={item.title}
                className={`glass-card rounded-[24px] p-5 shadow-sm stagger-${(index % 3) + 1}`}
              >
                <h3 className="text-xl font-bold text-[#153a64]">{item.title}</h3>
                <p className="mt-3 text-base leading-8 text-[#5b6878]">{item.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── FAQ Section ──────────────────────────────────────────── */}
        <section className="section-rise rounded-[32px] border border-[#d7dee8] bg-white px-6 py-8 shadow-sm md:px-8">
          <h2 className="text-3xl font-bold text-[#153a64]">वॉइस सहायक की आसान बातें</h2>
          <div className="mt-6 grid gap-5 md:grid-cols-3">
            {assistantFaqs.map((item, index) => (
              <div
                key={item.title}
                className={`soft-panel rounded-[24px] p-5 shadow-sm stagger-${(index % 3) + 1}`}
              >
                <h3 className="text-xl font-bold text-[#153a64]">{item.title}</h3>
                <p className="mt-3 text-base leading-8 text-[#5b6878]">{item.text}</p>
              </div>
            ))}
          </div>
        </section>

      </div>
    </div>
  );
}
