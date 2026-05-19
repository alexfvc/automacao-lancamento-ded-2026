# Automação do Diário Eletrônico — 2º Trimestre 2026

Conjunto de scripts Python/Selenium para automatizar o lançamento e a extração de aulas no [DED Mais](https://dedmais.educacao.mg.gov.br/), o diário eletrônico da rede estadual de Minas Gerais.

---

## Scripts

### `lancamento.py` — Lançamento de aulas

Lê a planilha `planejamento.xlsx` e lança automaticamente as aulas no diário eletrônico, turma por turma.

**Fluxo:**

1. Carrega as aulas da aba `preencher` e as 21 combinações turma+matéria da aba `Turmas e materias`
2. Abre o Chrome e aguarda o professor fazer login e resolver o CAPTCHA manualmente
3. Executa um diagnóstico comparando os cards do site com o Excel (verifica se todas as turmas estão mapeadas)
4. Para cada turma, verifica as aulas já lançadas no site (evita duplicatas) e lança apenas as novas
5. Ao final de cada turma, retorna à lista de cards via URL

**Como usar:**

```
python lancamento.py
```

---

### `diario_ded.py` — Extração de aulas

Percorre todas as turmas do diário eletrônico e exporta as aulas já lançadas para uma planilha Excel formatada.

**Fluxo:**

1. Abre o Chrome e detecta automaticamente se há sessão ativa (caso contrário, aguarda login manual)
2. Realiza scroll para carregar todos os cards (lazy loading)
3. Para cada turma, navega até a aba de aulas e coleta data + conteúdo lecionado
4. Exporta tudo para `diario_conteudos_2026.xlsx` com cabeçalho formatado e colunas dimensionadas

**Como usar:**

```
python diario_ded.py
```

---

## Planilha de entrada (`planejamento.xlsx`)

| Aba                 | Conteúdo                                                          |
| ------------------- | ----------------------------------------------------------------- |
| `preencher`         | Aulas a lançar: Turma, Disciplina, Data, ConteúdoLecionado, etc.  |
| `Turmas e materias` | Lista das combinações turma+matéria+turno que o professor leciona |

---

## Requisitos

```
pip install -r requirements.txt
```

Dependências principais: `selenium`, `webdriver-manager`, `pandas`, `openpyxl`

---

## Observações

- O login é sempre manual (CAPTCHA exige intervenção humana)
- O script `lancamento.py` é idempotente: pode ser interrompido e reexecutado sem duplicar lançamentos
- Navegação de volta entre turmas é feita via URL, não pelo botão voltar do site (mais confiável)
