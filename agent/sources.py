"""
Sources and shared taxonomy for the MarTech AI Decoder agent.

Edit FEEDS to taste — any RSS/Atom feed works. The scanner pulls candidates from
all of them, then the judge (an LLM) decides what actually matters.
"""

# RSS/Atom feeds the scanner reads. Verify each resolves in your environment;
# some publishers move their feed paths. Add/remove freely.
FEEDS = [
    {"source": "MarTech",          "url": "https://martech.org/feed/"},
    {"source": "MarTech · AI",     "url": "https://martech.org/topic/marketing-artificial-intelligence-ai/feed/"},
    {"source": "Solutions Review", "url": "https://solutionsreview.com/crm/feed/"},
    {"source": "chiefmartec",      "url": "https://chiefmartec.com/feed/"},
    {"source": "MarTech Series",   "url": "https://martechseries.com/feed/"},
    {"source": "Agile Brand",      "url": "https://agilebrandguide.com/feed/"},
]

# Keywords used to keep only AI-relevant items at scan time (cheap pre-filter
# before spending tokens on the judge).
AI_KEYWORDS = [
    "ai", "a.i.", "agent", "agentic", "genai", "generative", "llm", "gpt",
    "model", "machine learning", "automation", "personaliz", "decisioning",
    "copilot", "co-pilot", "rag", "geo ", "chatbot", "assistant",
]

# The fixed concept taxonomy. The judge may ONLY tag stories with these ids.
# Kept here so the agent and the page never drift apart — this dict is copied
# verbatim into the output JSON and read by the page.
CONCEPTS = {
    "cdp":     {"name": "CDP",                    "gloss": "Customer Data Platform — the unified store of who your customers are."},
    "perso":   {"name": "Personalization (1:1)",  "gloss": "Tailoring the message to the individual, not the segment."},
    "genai":   {"name": "Generative AI",          "gloss": "Models that produce content — copy, images, replies — from a prompt."},
    "agentic": {"name": "Agentic AI",             "gloss": "Systems that don't just generate, they decide and act toward a goal."},
    "decis":   {"name": "Agentic decisioning",    "gloss": "An agent choosing what to say, when, how often and on which channel — per person."},
    "bandit":  {"name": "Bandits / RL",           "gloss": "The maths that lets a system learn which choice wins by trying and measuring."},
    "cep":     {"name": "CEP",                    "gloss": "Customer Engagement Platform — where this messaging actually runs."},
    "geo":     {"name": "GEO",                    "gloss": "Generative Engine Optimization — being visible inside AI answers."},
    "govern":  {"name": "Governance",             "gloss": "The controls that make automated decisions safe, explainable and legible."},
}
