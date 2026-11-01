# 📝 AI Workflow Log — Desafio Técnico Artefact

> Rastreamento de cada etapa: o que foi pedido, o que foi feito, o que foi revisado.

---

## Sábado, 01/11/2026

### Checkpoint 1: Análise de Dados + Plano de Ação

**O que foi pedido:**
- Explorar `data/` (CSVs + PDF)
- Resumir findings técnicos
- Propor plano detalhado com decisões, ferramentas, cronograma, riscos
- **Aguardar aprovação antes de implementar**

**O que foi feito:**
- ✅ Inspecionado 6 CSVs: products (65), categories (9), customers (50), orders (20), order_items (22), promotions (25)
- ✅ Levantado PDF políticas (~180 KB)
- ✅ Criado `resumo_dados.md` com análise técnica completa
- ✅ Criado `PLANO_ACAO.md` com:
  - Arquitetura: Function Calling + Claude 3.5 Haiku
  - 7 ferramentas do agente (search, details, promotions, alternatives, order_status, customer_orders, policies)
  - Suposições documentadas (7 itens)
  - Cronograma Sábado–Segunda
  - Riscos + mitigações
  - 8 checkpoints de commit

**Revisão/Aprovação (Pedro):**
- ✅ Aprova Function Calling + Haiku
- ✅ Aprova verificação de cliente em 3 vias: CPF ou (email + phone)
- ✅ Sem ferramentas proibidas; Python obrigatório (já esperado)
- ✅ Setup necessário + commits frequentes + push para repositório

**Decisões Tomadas:**
- Framework: **ReAct com Function Calling** (vs. RAG puro, SQL direto, agente sem tools)
- Modelo: **Claude 3.5 Haiku** (vs. GPT-4o-mini, Gemini Flash)
- Interface: **CLI interativa** (vs. Streamlit/Gradio como bônus)
- Dados: **Pandas + SQLite em memória** (vs. leitura em tempo real)
- PDF: **Injetar no prompt** se < 50K tokens; RAG leve se maior
- Histórico: **Memória por sessão** (upgrade para SQLite persistente depois)

**Próximo Passo:**
→ Checkpoint 2: Git init + estrutura de pastas + primeiro commit

---

### Checkpoint 2: Setup & Estrutura

**O que foi pedido:**
- Git init
- Estrutura de pastas conforme CLAUDE.md
- `.gitignore`, `.env.example`, `requirements.txt`
- Primeiro commit

**O que foi feito:**
- ✅ `git init` com config user (pedroporto46@gmail.com)
- ✅ `.gitignore` (venv, __pycache__, .env, *.db, *.log)
- ✅ `.env.example` (ANTHROPIC_API_KEY, LLM_MODEL opcional, DEBUG opcional)
- ✅ `requirements.txt` (anthropic, python-dotenv, pandas, pdfplumber, fuzzywuzzy, python-Levenshtein)
- ✅ Estrutura de pastas: src/, src/tools/, tests/, examples/, docs/
- ✅ `__init__.py` para pacotes Python
- ✅ README.md stub
- ✅ `docs/ai_workflow.md` (este arquivo)

**Revisão/Próximas Ações (em espera por Pedro):**
- [ ] Confirmar setup está OK
- [ ] Fazer primeiro commit: `init: estrutura do projeto`
- [ ] Push para repositório GitHub (criar repo e linkar)
- Depois: Extrair PDF + implementar data_loader

---

## Domingo, 02/11/2026 — A Preencher

(Reservado para Checkpoints 3–7: implementação completa)

---

## Segunda, 03/11/2026 — A Preencher

(Reservado para Checkpoint 8: exemplos + README final)

---

## Notas Gerais

- **Versão Python:** 3.9+ (sem pinning específico, usar latest stable)
- **Encoding:** UTF-8 (CSVs + PDF)
- **Idioma:** Português (Brasil) — código em inglês, prompts em PT-BR
- **Assistente de IA:** Claude (Anthropic) via Chat + Claude Code
- **Workflow real:** Claude Chat para planejamento/análise; Claude Code (VS Code extension) para implementação

---
