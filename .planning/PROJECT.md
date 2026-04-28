# Sistema RAG de Suporte Técnico — Cancella Informática

## What This Is

Assistente de suporte técnico Nível 1 baseado em RAG (Retrieval-Augmented Generation) para a Cancella Informática LTDA. Clientes B2B acessam um widget de chat que responde dúvidas técnicas com base exclusivamente nos manuais e especificações técnicas da empresa — sem alucinações, sem esperar um técnico humano. Administradores fazem upload de PDFs que alimentam a base vetorial de conhecimento.

## Core Value

Responder dúvidas técnicas repetitivas de forma instantânea e precisa, liberando o único técnico de Nível 1 da Cancella para trabalho de alta complexidade em infraestrutura e redes.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Usuário B2B pode enviar dúvidas técnicas e receber respostas via widget de chat
- [ ] Sistema mantém contexto do histórico dentro de uma mesma sessão
- [ ] Respostas citam a fonte e permitem download do manual técnico original (PDF)
- [ ] Usuário pode avaliar cada resposta com feedback binário (útil/não útil)
- [ ] Admin pode fazer upload de PDFs para ingerir novos documentos na base de conhecimento
- [ ] Usuários precisam se autenticar para acessar o chat (logs identificados para auditoria)
- [ ] Sistema opera 24/7 com latência máxima de 5 segundos por resposta
- [ ] Toda execução é on-premise via Docker — sem dependência de armazenamento em nuvem

### Out of Scope

- Fine-tuning ou treinamento de modelos — RAG com documentação existente resolve o problema sem retreinamento
- App mobile — widget web responsivo é suficiente para atendimento B2B no cenário atual
- Escalamento automático para Nível 2 — encaminhamento humano permanece manual por ora
- Suporte multilíngue — base de conhecimento e clientela são integralmente em português

## Context

Cancella Informática LTDA foi fundada em 1995 por Danton Cancella (stakeholder principal e validador do projeto), especialista em infraestrutura de rede e servidores, atendendo mercado B2B com clientes corporativos dependentes da continuidade operacional de datacenters.

**Situação-problema:** 4-5 chamados de Nível 1 por dia. 60% do tempo do técnico consumido por dúvidas repetitivas cuja resposta já está documentada em manuais internos. A "fricção informacional" faz o cliente B2B preferir o contato humano imediato a buscar nos manuais estáticos — gerando latência de resposta, sobrecarga qualitativa e subutilização de mão de obra especializada.

**Risco técnico identificado:** documentos legados com baixa qualidade de OCR podem exigir pré-processamento de imagem/limpeza de texto antes da vetorização.

**Contexto acadêmico:** Projeto VI — Práticas Extensionistas, PUC Minas (fevereiro a julho de 2026).
Equipe: Guilhermino Lucas Chaves Araújo, Luis Fernando da Rocha Cancella, André Luiz Santos Moreira da Silva.

## Constraints

- **Stack**: Python 3.11+, FastAPI, LangGraph, PostgreSQL 16+ + pgvector, React + Tailwind — decidido em spec
- **LLM Gateway**: OpenRouter — flexibilidade de modelo, custo flexível, chamadas de API externas
- **Infraestrutura**: On-premise nos servidores da Cancella (Windows/Linux), Docker + Docker Compose
- **Concorrência**: 3-4 usuários simultâneos (cenário atual de atendimento)
- **Timeline**: Entrega até julho de 2026 (prazo acadêmico)
- **Arquitetura**: Monolito MVC — simplicidade de manutenção para equipe pequena e escopo acadêmico

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| RAG em vez de GPT puro | Instrução errada em infraestrutura gera prejuízo real — RAG garante respostas 100% fundamentadas nos manuais | — Pending |
| PostgreSQL + pgvector | Unifica armazenamento relacional e vetorial em uma única instância, sem infraestrutura adicional | — Pending |
| LangGraph para orquestração | Gerencia nós de decisão e valida se a resposta está no contexto antes de responder — previne alucinações | — Pending |
| OpenRouter como LLM gateway | Evita lock-in em único provedor, permite trocar modelo sem alterar código | — Pending |
| Monolito MVC | Simplifica deploy e manutenção para equipe de 3 pessoas e servidor único on-premise | — Pending |
| On-premise + Docker | Soberania dos dados técnicos da Cancella + compatibilidade com infraestrutura existente | — Pending |
| Login obrigatório | Auditoria técnica por usuário identificado (RNF-02) e controle de acesso à base de conhecimento | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-10 after initialization*
