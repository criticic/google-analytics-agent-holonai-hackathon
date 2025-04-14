# HOLON x KBI AI AGENTS HACKATHON 2025

## Track 4: AI Business Intelligence Agent : Smart Dashboards for Decision-Making

## Problem

SMEs in Asia rely on fragmented, hard-to-use tools to make decisions. Business owners and managers often struggle to get timely answers from platforms like Google Analytics or internal systems. Dashboards exist but don’t speak the user’s language literally or contextually.

## Goal

Build a multilingual BI(Business Intelligence) agent that:

- Connects to Google Analytics (mock or real)
- Accepts queries in chatbot format
- Uses predefined + evolving question sets to answer business queries
- Surfaces actionable insights from connected agents (ads, accounting, etc.)
- Returns responses in English, Mandarin, or Cantonese

## MVP Scope

### Inputs

- Google Analytics (mock data or API output in JSON) <https://support.google.com/analytics/answer/7586738?hl=en>
- Optional: outputs from other agents (ads optimizer, accounting summaries)

### Agent Capabilities

- Accept user questions via a simple chat interface
- Match user questions to a predefined library (e.g., "What was my bounce rate last month?")
- Expand/improvise these queries using LLM-based NLP
- Return data-driven insights with supporting charts or text summaries

### Outputs

- Chat-like interface for business queries
- Data visualization + natural language summaries
- Multilingual response support

## Agentic Nature

Your BI agent should:

- Select the best dataset + question template based on intent
- Offer follow-up questions for deeper insight
- Learn which types of questions are being asked and evolve its suggestions
- Speak to non-technical users ("Your top page dropped 30% this week")

## Deliverables

- Public GitHub repo
- Chatbot UI demo (recorded or live)
- Screenshot of at least 5 predefined query+response flows
- 1 auto-generated multilingual summary report
- 1-pager PDF on prompt mapping + architecture

📢 Don’t just build a dashboard — build a multilingual data advisor that thinks,
recommends, and explains.
