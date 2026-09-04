import os
import json
import urllib.request
import urllib.error


def generate_ai_tutor_response(mode: str, user_prompt: str) -> dict:
    """
    OpenAI API yoki o'rnatilgan aqlli AI Tutor dvigateli orqali foydalanuvchiga javob va ta'limiy feedback qaytaradi.
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()

    system_prompts = {
        "english": (
            "You are an expert IT & Business English Coach for software engineers and tech entrepreneurs. "
            "Respond to the user in clean, natural English. "
            "After your main response, ALWAYS provide a structured 'FEEDBACK & CORRECTIONS' section in Uzbek/English "
            "with: 1. Grammar corrections 2. Professional Vocabulary upgrades 3. Pronunciation tips for key terms."
        ),
        "coding": (
            "You are a Senior Software Architect and Tech Lead. "
            "Help the user improve their programming skills, clean code, software architecture (Django, Python, JS, DBs), and algorithm design. "
            "Provide clean code snippets, architectural recommendations, and explain trade-offs clearly in Uzbek & English."
        ),
        "business": (
            "You are a successful Software Business Consultant and Negotiation Mentor for tech founders and senior freelancers. "
            "Provide actionable advice on client acquisition, pricing strategy, project estimation, contracts, and software monetization. "
            "Give step-by-step strategies in Uzbek & English with real-life scenario scripts."
        )
    }

    system_prompt = system_prompts.get(mode, system_prompts["english"])

    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1200
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                reply = res_body["choices"][0]["message"]["content"]
                return {
                    "reply": reply,
                    "provider": "OpenAI (GPT-4o-mini)"
                }
        except Exception as e:
            # Fallback to local intelligent mentor if API fails
            pass

    # Intelligent Fallback Learning Engine (No API key needed!)
    prompt_lower = user_prompt.lower()
    
    if mode == "english":
        reply = f"Great input! Let's analyze and practice this topic.\n\n"
        reply += f"💬 **Interactive Response:**\n"
        reply += f"Thank you for sharing your thoughts on: \"{user_prompt[:100]}\". In professional IT environments, clear communication is essential when dealing with clients, code reviews, and remote teams.\n\n"
        reply += f"💡 **Recommended Tech & Business Phrases for this topic:**\n"
        reply += f"• **'To align expectations'** — Talablarni bir xillashtirish (Ex: 'Let's schedule a call to align expectations on the project scope.')\n"
        reply += f"• **'Deliverable'** — Topshirilishi kerak bo'lgan tayyor mahsulot/modul (Ex: 'The main deliverable for sprint 1 is the user authentication.')\n"
        reply += f"• **'Bottleneck'** — Jarayonni sekinlashtiruvchi omil (Ex: 'Database indexing is the primary bottleneck in our API.')\n\n"
        reply += f"🎯 **Grammar & Fluency Tip:**\n"
        reply += f"When speaking to international clients, use polite modal verbs (`Could we...`, `Would it be possible to...`, `I would recommend...`) to sound executive and professional."
        return {"reply": reply, "provider": "AI Learning Assistant"}

    elif mode == "coding":
        reply = f"🛠️ **Dasturlash va Arxitektura bo'yicha Maslahat:**\n\n"
        reply += f"Foydalanuvchi so'rovi: \"{user_prompt[:100]}\"\n\n"
        reply += f"📐 **Kodni Yaxshilash va Clean Architecture Tamoyillari:**\n"
        reply += f"1. **Single Responsibility Principle (SRP):** Har bir model, view va servis faqat bitta aniq vazifa uchun mas'ul bo'lishi kerak.\n"
        reply += f"2. **Fat Models, Thin Views (Django Best Practice):** Biznes mantiqini (hisob-kitoblar, status o'zgartirish) `models.py` yoki `services.py` fayllarga ko'chiring, view faqat so'rov va javobni boshqarsin.\n"
        reply += f"3. **Database Performance:** `select_related()` (ForeignKey uchun) va `prefetch_related()` (ManyToMany uchun) ishlatib N+1 so'rovlar muammosini oldini oling.\n\n"
        reply += f"💻 **Kod Strukturasi Namunasi:**\n```python\n# Good Practice: Encapsulated Business Logic\nclass Invoice(models.Model):\n    def calculate_total_profit(self):\n        return self.amount - self.expenses\n```"
        return {"reply": reply, "provider": "AI Architecture Advisor"}

    else: # business
        reply = f"💼 **Biznes va Daromad Rivojlantirish Strategiyasi:**\n\n"
        reply += f"Mavzu: \"{user_prompt[:100]}\"\n\n"
        reply += f"🚀 **Mijozlar bilan Ishlash va Narxni Oshirish Usullari:**\n"
        reply += f"1. **Value-Based Pricing (Qiymatga Asoslangan Narx):** Kod yozgan soatingizga emas, loyiha mijozga qancha daromad yoki tejamkorlik keltirishiga qarab narx belgilang.\n"
        reply += f"2. **Discovery Call (Dastlabki Audit):** Mijozga darhol narx aytmang. Avval ularning biznes muammosini tinglang va yechim paketini (MVP, Pro, Enterprise) taklif qiling.\n"
        reply += f"3. **Retainer Agreements (Oylik Obuna):** Texnik xizmat ko'rsatish, server monitoringi va yangilanishlar uchun oylik belgilangan to'lov (masalan $300-$1000/oy) joriy qiling."
        return {"reply": reply, "provider": "AI Business Mentor"}
