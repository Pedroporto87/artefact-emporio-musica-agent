# 🎵 Empório da Música — Agente de Atendimento

> Agente de atendimento por mensagens de texto para a Empório da Música (Case Técnico - Artefact)

## Status

🚧 **Em Desenvolvimento** — Estrutura inicial criada, implementação em progresso.

## Estrutura do Projeto

```
.
├── README.md                    # Este arquivo
├── requirements.txt             # Dependências Python
├── .env.example                 # Configuração de exemplo
├── .gitignore
├── data/                        # Dados fornecidos (CSVs + PDF) — NÃO EDITAR
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entrypoint CLI (em breve)
│   ├── agent.py                 # Loop do agente ReAct (em breve)
│   ├── prompts.py               # System prompt + persona (em breve)
│   ├── data_loader.py           # Carga e limpeza de CSVs (em breve)
│   ├── policies.py              # Extração/consulta do PDF (em breve)
│   └── tools/                   # Ferramentas do agente
│       ├── __init__.py
│       ├── products.py          # Busca de produtos (em breve)
│       ├── orders.py            # Consulta de pedidos (em breve)
│       └── policies.py          # Consulta de políticas (em breve)
├── tests/                       # Testes determinísticos (em breve)
├── examples/                    # 3–5 conversas reais (em breve)
└── docs/
    └── ai_workflow.md           # Log do workflow (em atualização)
```

## Próximos Passos

- [ ] Extrair e analisar PDF de políticas
- [ ] Implementar `data_loader.py`
- [ ] Implementar ferramentas (`src/tools/`)
- [ ] Implementar agent loop
- [ ] Criar CLI interativa
- [ ] Gerar exemplos de conversas
- [ ] Escrever README completo

---

**Desenvolvido com Claude + Claude Code**
