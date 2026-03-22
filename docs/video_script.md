# Video Script — Smart Inventory Assistant
### Introductory Camera Video (Final Year Project)

---

> **Format:** Sit in front of camera, speak naturally and confidently. Estimated duration: 3–4 minutes.
> **Tone:** Enthusiastic + technical but accessible. This is a "coming soon" product demo intro.

---

## [INTRO — 0:00 to 0:25]

**[Look directly at camera, smile]**

> "Hey everyone — my name is Sayandip, and today I want to walk you through my final year project:
> the **Smart Inventory Assistant** — an AI-powered inventory management system
> that I'm building as a production-grade product.
>
> This is not just a college project. This is a real product. And I want to show you exactly what I'm building,
> why I'm building it, and what it will look like when it's fully deployed."

---

## [THE PROBLEM — 0:25 to 0:55]

**[Lean slightly forward, serious tone]**

> "So here's the problem I'm solving.
>
> Think about hospitals, clinics, warehouses, or any organization that manages physical stock —
> medicines, equipment, supplies.
>
> Most of them are still tracking inventory in Excel files. Managers don't know
> when stock is critically low until it's already out. Requisition approvals happen over WhatsApp.
> There's no visibility, no data, no intelligence.
>
> That's exactly what I'm fixing."

---

## [THE SOLUTION — 0:55 to 1:50]

**[Sit up straight, confident delivery]**

> "Smart Inventory Assistant is a full-stack web application with four core features:
>
> **First — Real-time inventory tracking.**
> Every location in your organization can log daily stock movements — items received and issued —
> and the system automatically calculates your current closing stock for every item, at every location.
>
> **Second — Requisition management.**
> Staff can raise requisition requests directly on the platform.
> Managers get those requests, can approve or reject them, and the stock levels update automatically.
> No more WhatsApp chains.
>
> **Third — Analytics dashboard.**
> Admins get a live dashboard: a heatmap showing stock health across all locations,
> critical alerts for items about to run out, reorder recommendations calculated automatically.
>
> **And fourth — the AI Assistant.**
> There's an AI chatbot built into the platform that you can simply ask questions like:
> 'What items are critically low right now?' or 'What should I order today?'
> — and it queries your actual inventory data and gives you a real answer.
> It even understands voice input."

---

## [ARCHITECTURE — 1:50 to 2:40]

**[Slightly more technical, but keep it clear]**

> "Now let me quickly show you the architecture — because this is where it gets interesting as an engineer.
>
> The system is a **modular monolith backend** built with FastAPI and Python.
> It's organized into four clean layers:
> — the API layer handles all the HTTP routing and validation
> — the Application layer has all the business logic
> — the Domain layer has pure calculations with no framework dependencies
> — and the Infrastructure layer handles the database and AI memory
>
> For the database, I'm using **SQLite in development** and will move to **PostgreSQL on AWS** in production.
>
> For AI memory, I'm using **ChromaDB** — a vector database that lets the AI remember previous conversations
> and pull in relevant context using semantic search. This is called RAG — Retrieval Augmented Generation.
>
> The AI tools are built on **LangChain**, and the language model is powered by **Groq** —
> one of the fastest LLM inference engines available right now.
>
> For the frontend, I'm using **React with Vite** — it's fast, component-based, very modern."

---

## [ROLES & ACCESS — 2:40 to 3:05]

**[Conversational tone]**

> "The system has full role-based access control.
>
> An **Admin** can manage users, approve or override anything, and see all analytics.
> A **Manager** can approve or reject requisitions and monitor stock across locations.
> **Staff** can create requisitions and log daily inventory entries.
> **Viewers** have read-only access — perfect for auditors or senior leadership who just want to see the data.
>
> Every action is tracked in an audit log — who did what and when."

---

## [DEPLOYMENT & WHAT'S COMING — 3:05 to 3:40]

**[Excited tone — this is the 'coming soon' part]**

> "Now here's what's coming next.
>
> The full production version will be deployed on **AWS ECS with Fargate** — that's serverless containers —
> with a **PostgreSQL database on AWS RDS**, auto-scaling, HTTPS, and a full GitHub Actions CI/CD pipeline.
>
> I'm also building a **free tier** — so small clinics, NGOs, and organizations that can't afford
> expensive inventory software can use this for free.
>
> This is a fully deployed product — not just a demo."

---

## [OUTRO — 3:40 to 4:00]

**[Smile, relaxed closing]**

> "If you're a developer, a healthcare organization, or just someone interested in what we're building —
> stay tuned.
>
> The product is coming soon.
>
> Thanks for watching."

---

## Production Notes

| Element | Suggestion |
|---------|-----------|
| **Background** | Clean desk or subtle dark background — professional |
| **Lighting** | Ring light or natural window light from the front |
| **Dress** | Smart casual (collar shirt works well) |
| **Camera** | Phone or laptop camera is fine — keep it steady |
| **Screen recording** | Optional: cut to a quick 10-second dashboard preview when mentioning analytics |
| **Music** | Light ambient/lo-fi under the intro and outro, silent during speaking |
| **Caption** | Add subtitles for accessibility |
