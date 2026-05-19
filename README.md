# Automação do Diário Eletrônico — 2º Trimestre 2026

Conjunto de scripts Python/Selenium para automatizar o lançamento e a extração de aulas no [DED Mais](https://dedmais.educacao.mg.gov.br/), o diário eletrônico da rede estadual de Minas Gerais.

---

## Scripts

### `lancador.py` — Lançamento de aulas *(versão atual)*

Script principal. Lê a planilha `planejamento.xlsx` e lança automaticamente as aulas no diário eletrônico, turma por turma, com detecção automática de sessão e prevenção de duplicatas.

**Fluxo:**

1. Carrega as aulas da aba `preencher` e converte as datas para `DD/MM/YYYY`
2. Abre o Chrome (Selenium Manager — sem dependência de driver externo) e detecta sessão ativa pela URL; aguarda login manual se necessário
3. Faz scroll na lista de cards para disparar o lazy loading e salva os metadados de cada turma
4. Para cada turma com aulas no Excel:
   - Clica no card da turma e abre a aba Aulas
   - Faz scraping das datas já lançadas no site
   - Remove de ambas as tabelas (local e global) as datas que já existem no site
   - Lança apenas as aulas novas
5. Retorna à lista de cards via URL ao final de cada turma

**Como usar:**

```
python lancador.py
```

---

### `diario_ded.py` — Extração de aulas

Percorre todas as turmas do diário eletrônico e exporta as aulas já lançadas para uma planilha Excel formatada. Útil para backup ou conferência do que está no site.

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

### `lancamento.py` — Lançamento de aulas *(legado)*

Versão anterior do script de lançamento. Mantida como referência. Usa `webdriver-manager` para gerenciar o ChromeDriver e exige login manual com CAPTCHA. Prefira `lancador.py`.

---

## Planilha de entrada (`planejamento.xlsx`)

| Aba | Conteúdo |
| --- | --- |
| `preencher` | Aulas a lançar: Turma, Disciplina, Data, ConteúdoLecionado, etc. |
| `Turmas e materias` | Lista das combinações turma+matéria+turno que o professor leciona |

---

## Requisitos

```
pip install -r requirements.txt
```

Dependências principais: `selenium`, `pandas`, `openpyxl`

> `lancador.py` usa o Selenium Manager nativo (Selenium 4.6+) — não é necessário instalar `webdriver-manager`.

---

## Observações

- O login é sempre manual (CAPTCHA exige intervenção humana)
- `lancador.py` é idempotente: pode ser interrompido e reexecutado sem duplicar lançamentos
- Navegação de volta entre turmas é feita via URL, não pelo botão voltar do site (mais confiável)
- Arquivos de contexto (`*_contxt.txt`) e planilhas (`*.xlsx`) estão no `.gitignore`
