# 🐍 Pipeline Batch Bovespa — Tech Challenge Fase 2

Pipeline de dados completo para extração, processamento e análise de ações da B3, construído na AWS com Python, S3, Lambda, Glue, EventBridge e Athena.

---

## 📁 Estrutura do Projeto

```
tech-challenge-fase2/
│
├── scripts/
│   ├── tc_scraping.py          # Scraping via yfinance + upload S3
│   ├── tc_lambda.py            # Gatilho automático S3 → Glue
│   ├── tc_lambda_scraping.py   # Scraping via Lambda (acionado pelo EventBridge)
│   └── tc-etl-bovespa1.py       # ETL Spark + catalogação Glue
├── docs/
│   ├── arquitetura_pipeline.html   # Diagrama visual da arquitetura
│   └── CONFIGURACAO_AWS.md         # Passo a passo de configuração na AWS
└── README.md
```

---

## 🏗️ Arquitetura

```
EventBridge (todo dia às 22h — horário de Brasília)
    → Lambda de scraping (tc-lambda-scraping)
        → S3 raw/ (Parquet particionado por data e ticker)
            → Lambda gatilho (tc-lambda-bovespa)
                → AWS Glue Job PySpark (tc-etl-bovespa1)
                    → S3 refined/ (Parquet particionado)
                        → Glue Catalog (tabela catalogada)
                            → Athena (consultas SQL)
```

---

## 📋 Requisitos Atendidos

| Requisito | Descrição | Script |
|-----------|-----------|--------|
| REQ 1 | Scraping diário de ações da B3 via yfinance | `tc_scraping.py` |
| REQ 2 | Dados brutos no S3 em Parquet com partição diária | `tc_scraping.py` |
| REQ 3 | Bucket S3 aciona Lambda automaticamente | `tc_lambda.py` |
| REQ 4 | Lambda inicia o Glue Job | `tc_lambda.py` |
| REQ 5-A | Agrupamento mensal por ticker (média, máx, mín, volume) | `tc-etl-bovespa1.py` |
| REQ 5-B | Renomeação de colunas para português | `tc-etl-bovespa1.py` |
| REQ 5-C | Cálculos de data: MM5, variação diária, amplitude | `tc-etl-bovespa1.py` |
| REQ 6 | Dados refinados em `refined/` particionado por data e ticker | `tc-etl-bovespa1.py` |
| REQ 7 | Catalogação automática no Glue Catalog | `tc-etl-bovespa1.py` |
| REQ 8 | Dados consultáveis via SQL no Athena | Glue Catalog |

---

## ➕ Funcionalidade Extra

| Recurso | Descrição |
|---------|-----------|
| **EventBridge Schedule** | Agendamento diário às 22h (horário de Brasília) para execução automática do scraping |
| **Lambda de Scraping** | Função Lambda que executa o scraping sem depender de execução local |

---

## 🎯 Ativos Monitorados

| Ticker | Empresa |
|--------|---------|
| PETR4 | Petrobras |
| VALE3 | Vale |
| ITUB4 | Itaú Unibanco |
| BBDC4 | Bradesco |
| ABEV3 | Ambev |

---

## ⚙️ Configurações AWS

| Recurso | Nome/Valor |
|---------|-----------|
| Bucket S3 | `techchallenge-bovespa-pipeline1` |
| Pasta Raw | `s3://techchallenge-bovespa-pipeline1/raw/` |
| Pasta Refined | `s3://techchallenge-bovespa-pipeline1/refined/` |
| Pasta Athena | `s3://techchallenge-bovespa-pipeline1/athena-results/` |
| Pasta Scripts | `s3://techchallenge-bovespa-pipeline1/scripts/` |
| Lambda Gatilho | `tc-lambda-bovespa` |
| Lambda Scraping | `tc-lambda-scraping` |
| Glue Job | `tc-etl-bovespa1` |
| Glue Version | 5.0 |
| Worker Type | G.1X — 2 workers |
| Banco Glue | `tc_bovespa_db` |
| Tabela Glue | `tc_acoes_refinadas` |
| EventBridge | `tc-scraping-diario` (cron: `0 22 * * ? *`) |
| Região | `us-east-1` |

---

## 🚀 Como Executar

### 1. Pré-requisitos
```bash
pip install yfinance pandas boto3 pyarrow
aws configure  # configurar credenciais AWS
```

### 2. Scraping manual (local)
```bash
python scripts/tc_scraping.py
```

### 3. Scraping automático
O EventBridge `tc-scraping-diario` executa automaticamente todo dia às 22h via `tc-lambda-scraping` — sem necessidade de execução manual.

### 4. Glue Job
Após o scraping, a Lambda `tc-lambda-bovespa` dispara automaticamente o job `tc-etl-bovespa1` no Glue.

---

## 🗂️ Estrutura de Partições no S3

### Raw
```
raw/
└── data_particao=2026-02-27/
    ├── ticker=PETR4/
    │   └── dados.parquet
    ├── ticker=VALE3/
    │   └── dados.parquet
    └── ...
```

### Refined
```
refined/
└── data_particao=2026-02-27/
    ├── ticker=PETR4/
    │   └── part-00000.parquet
    ├── ticker=VALE3/
    │   └── part-00000.parquet
    └── ...
```

---

## 📊 Schema da Tabela Refinada

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| data_pregao | date | Data do pregão |
| ticker | string | Código da ação |
| preco_abertura | double | Preço de abertura |
| preco_fechamento | double | Preço de fechamento |
| preco_maximo | double | Máximo do dia |
| preco_minimo | double | Mínimo do dia |
| volume_negociado | long | Volume total negociado |
| media_movel_5d | double | Média móvel 5 dias |
| variacao_diaria_pct | double | Variação % abertura→fechamento |
| amplitude_diaria | double | Máximo − Mínimo |
| ano_mes | string | Ano-mês (yyyy-MM) |
| media_fechamento_mes | double | Média mensal de fechamento |
| maximo_mes | double | Máximo do mês |
| minimo_mes | double | Mínimo do mês |
| volume_total_mes | long | Volume total do mês |
| qtd_pregoes_mes | long | Pregões no mês |
| data_particao | string | Partição por data (yyyy-MM-dd) |

---

## 🔍 Queries Athena Utilizadas

```sql
-- Resumo geral por ticker: variação média, maior e menor preço
SELECT
    ticker,
    ROUND(AVG(variacao_diaria_pct), 4) AS media_variacao,
    ROUND(MAX(preco_maximo), 2) AS maior_preco,
    ROUND(MIN(preco_minimo), 2) AS menor_preco
FROM tc_bovespa_db.tc_acoes_refinadas
GROUP BY ticker
ORDER BY media_variacao DESC;
```

```sql
-- Comparativo mensal entre todos os ativos
SELECT
    ticker,
    ano_mes,
    media_fechamento_mes,
    maximo_mes,
    minimo_mes,
    volume_total_mes,
    qtd_pregoes_mes
FROM tc_bovespa_db.tc_acoes_refinadas
GROUP BY ticker, ano_mes, media_fechamento_mes,
         maximo_mes, minimo_mes, volume_total_mes, qtd_pregoes_mes
ORDER BY ticker, ano_mes;
```

```sql
-- Visão completa diária — base para o dashboard
SELECT
    ticker,
    data_pregao,
    preco_fechamento,
    preco_abertura,
    preco_maximo,
    preco_minimo,
    volume_negociado,
    media_movel_5d,
    variacao_diaria_pct,
    amplitude_diaria,
    ano_mes,
    media_fechamento_mes,
    volume_total_mes
FROM tc_bovespa_db.tc_acoes_refinadas
ORDER BY ticker, data_pregao;
```

---

## 👥 Tech Challenge — Fase 2 | PosTech FIAP
