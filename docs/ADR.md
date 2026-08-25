# ADR-001: Use LangGraph StateGraph for Agent Routing

## Status

Accepted

## Context

We need to build a conversational AI agent for lingerie product catalog customer service. The agent must:
- Handle multiple domains (catalog, sales, support)
- Route messages to specialized handlers
- Provide consistent PT-BR responses
- Be fast and predictable

## Decision

Use LangGraph StateGraph for agent routing with:
- Rule-based intent classifier (no LLM for classification)
- Template-based responses (no LLM for generation)
- FAISS for RAG (local vector search)

## Consequences

### Positive
- **Fast**: Intent classification <1ms, response generation <100ms
- **Predictable**: No LLM hallucination in routing or response templates
- **Low cost**: No API calls for classification or response generation
- **Testable**: Rule-based classifier is deterministic

### Negative
- **Limited flexibility**: Can only handle predefined intents
- **Template rigidity**: Responses follow fixed patterns
- **Maintenance**: New intents require code changes

### Mitigations
- RAG provides dynamic context within templates
- Agent handles can be extended for new domains
- Templates can be updated without code changes

---

# ADR-002: Use FAISS for Vector Store

## Status

Accepted

## Context

We need a vector store for RAG to search product catalog and documentation. Requirements:
- Local deployment (no external services)
- Fast search
- Simple setup
- Handle ~100 documents

## Decision

Use FAISS (Facebook AI Similarity Search) with sentence-transformers embeddings.

## Consequences

### Positive
- **Local**: No external dependencies or API calls
- **Fast**: In-memory search, <50ms for 100 documents
- **Simple**: Single Python package, no server setup
- **Proven**: Battle-tested at scale

### Negative
- **Persistence**: Requires manual save/load (solved in RAGService)
- **Memory**: Entire index in RAM (acceptable for 100 docs)
- **No metadata filtering**: Limited to similarity search

### Mitigations
- RAGService handles save/load automatically
- 100 docs fit easily in memory
- Metadata stored in Document objects for post-filtering

---

# ADR-003: Use Rule-Based Intent Classifier

## Status

Accepted

## Context

We need to classify user messages into intents for routing. Options:
1. LLM-based classification (e.g., OpenAI function calling)
2. ML-based classifier (e.g., scikit-learn)
3. Rule-based regex classifier

## Decision

Use rule-based regex classifier with 13 predefined intents.

## Consequences

### Positive
- **Fast**: <1ms classification
- **Predictable**: Same input always produces same output
- **No cost**: No API calls or model inference
- **Transparent**: Easy to understand and debug

### Negative
- **Limited**: Can only match predefined patterns
- **Maintenance**: New patterns require code changes
- **No learning**: Doesn't improve from data

### Mitigations
- RAG provides context for nuanced responses
- Patterns cover common Portuguese variations
- Can be upgraded to ML classifier later if needed

---

# ADR-004: Use Template-Based Responses

## Status

Accepted

## Context

We need to generate PT-BR responses for customer queries. Options:
1. LLM-generated responses (e.g., GPT-4)
2. Template-based with context injection
3. Hybrid (templates + LLM refinement)

## Decision

Use template-based responses with RAG context injection.

## Consequences

### Positive
- **Fast**: No LLM inference for response generation
- **Consistent**: Same intent produces same response structure
- **No hallucination**: Responses are deterministic
- **Brand control**: Fixed voice and tone

### Negative
- **Rigid**: Limited variation in responses
- **Context-dependent**: Quality depends on RAG results
- **No personalization**: Same response for all users

### Mitigations
- RAG context provides dynamic information
- Templates can be parameterized for variation
- Personalization can be added later via user profile
