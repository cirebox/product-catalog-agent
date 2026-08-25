# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added
- LangGraph StateGraph para roteamento de mensagens
- RAG Service com ChromaDB + sentence-transformers
- SQLite Service para persistência de sessões
- Intent classifier com 13 intents de lingerie
- 4 agentes especializados (Catalog, Sales, Support, General)
- Response templates em PT-BR
- FastAPI server com endpoint `/v1/chat`
- Catálogo de 63 produtos de lingerie (CSV)
- Documentos para RAG (FAQ, política de trocas, guia de medidas)
- OpenRouter integration (free models)
- Dockerfile multi-stage
- docker-compose.yml com volumes para persistência
- Testes unitários (intent classifier, RAG service)
- CI/CD pipeline (GitHub Actions)
- Documentação (README, ARCHITECTURE, ADR, CHANGELOG)

### Changed
- Substituído FAISS por ChromaDB para vector store
- Adicionado SQLite para dados relacionais (sessões, histórico)
- Configurado OpenRouter como LLM provider (modelos gratuitos)

### Fixed
- (nenhum bug corrigido ainda)

## [0.1.0] - 2026-08-25

### Added
- Projeto inicial com estrutura base
- Copia de boilerplate do vamu-agent
