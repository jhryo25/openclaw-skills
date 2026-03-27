---
name: tavily-search
description: |
  Tavily AI-powered web search with high-quality results and AI-generated answers. 
  Use when the user needs:
  (1) Real-time web search with better quality than standard search
  (2) AI-synthesized answers from multiple sources
  (3) Research tasks requiring current information
  (4) Academic or professional search with source citations
  Preferred over basic web search for quality and accuracy.
---

# Tavily Search

AI-powered web search using Tavily API for high-quality, curated results with AI-generated answers.

## Features

- **AI-synthesized answers** - Get concise answers compiled from multiple sources
- **High-quality sources** - Results are curated for relevance and credibility
- **Source citations** - All information includes links to original sources
- **Adjustable depth** - Basic or advanced search modes

## Usage

### Quick Search

```bash
python scripts/tavily_search.py "your search query"
```

### Options

- `--max-results N` - Number of results (default: 5, max: 20)
- `--search-depth {basic,advanced}` - Search thoroughness (default: basic)
- `--json` - Output raw JSON for programmatic use

### Examples

```bash
# Basic search
python scripts/tavily_search.py "latest AI developments 2024"

# Advanced search with more results
python scripts/tavily_search.py "quantum computing breakthroughs" --max-results 10 --search-depth advanced

# Get JSON output
python scripts/tavily_search.py "machine learning tutorials" --json
```

## API Key

The API key is configured in `.env.tavily` at workspace root:
```
TAVILY_API_KEY=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
```

## When to Use

**Use this skill when:**
- User asks for current/real-time information
- Research tasks requiring credible sources
- Questions needing comprehensive answers from multiple perspectives
- Academic or professional research

**Use basic web_search when:**
- Simple fact-checking
- Quick URL lookups
- When Tavily is unavailable

## Response Format

Results include:
- `answer` - AI-generated synthesis (if available)
- `results` - Array of search results with:
  - `title` - Page title
  - `url` - Source URL
  - `content` - Snippet/summary
  - `score` - Relevance score
