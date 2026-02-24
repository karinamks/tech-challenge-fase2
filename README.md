# 🐍 Pipeline Batch Bovespa — Tech Challenge Fase 2

Pipeline de dados completo para extração, processamento e análise de ações da B3, construído na AWS com Python, S3, Lambda, Glue e Athena.

---

## 📁 Estrutura do Projeto

```
pipeline-bovespa/
│
├── tc_scraping.py          # REQ 1-2: Scraping via yfinance + upload S3
├── tc_lambda.py            # REQ 3-4: Gatilho automático via Lambda
├── tc_glue_job.py          # REQ 5-6-7: ETL Spark + catalogação Glue
└── README.md               # Este arquivo
```

---

## 🏗️ Arquitetura

```
Python (yfinance)
    → S3 raw/ (Parquet particionado)
        → Lambda (gatilho S3)
            → AWS Glue Job (PySpark ETL)
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
| REQ 5-A | Agrupamento mensal por ticker (média, máx, mín, volume) | `tc_glue_job.py` |
| REQ 5-B | Renomeação de colunas para português | `tc_glue_job.py` |
| REQ 5-C | Cálculos de data: MM5, variação diária, amplitude | `tc_glue_job.py` |
| REQ 6 | Dados refinados em `refined/` particionado por data e ticker | `tc_glue_job.py` |
| REQ 7 | Catalogação automática no Glue Catalog | `tc_glue_job.py` |
| REQ 8 | Dados consultáveis via SQL no Athena | Glue Catalog |

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
| Bucket S3 | `techchallenge-bovespa-pipeline` |
| Pasta Raw | `s3://techchallenge-bovespa-pipeline/raw/` |
| Pasta Refined | `s3://techchallenge-bovespa-pipeline/refined/` |
| Glue Job | `tc-etl-bovespa` |
| Banco Glue | `tc_bovespa_db` |
| Tabela Glue | `tc_acoes_refinadas` |
| Região | `us-east-1` |

---

## 🚀 Como Executar

### 1. Scraping (local ou EC2)

```bash
pip install yfinance pandas boto3 pyarrow
python tc_scraping.py
```

> Necessário ter credenciais AWS configuradas (`aws configure` ou IAM Role).

### 2. Lambda
- Deploy via console AWS ou AWS CLI
- Configurar trigger S3 no bucket `techchallenge-bovespa-pipeline`, prefixo `raw/`
- Runtime: Python 3.11
- Handler: `tc_lambda.lambda_handler`
- Permissão necessária: `glue:StartJobRun`

### 3. Glue Job
- Upload do `tc_glue_job.py` no S3 ou diretamente no console Glue
- Runtime: Glue 4.0 (Spark)
- Worker Type: G.1X — 2 workers
- Permissões necessárias: `s3:GetObject`, `s3:PutObject`, `glue:*`

---

## 🗂️ Estrutura de Partições no S3

### Raw
```
raw/
└── data_particao=2025-01-15/
    ├── ticker=PETR4/
    │   └── dados.parquet
    ├── ticker=VALE3/
    │   └── dados.parquet
    └── ...
```

### Refined
```
refined/
└── data_particao=2025-01-15/
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

## 🔍 Exemplo de Query Athena

```sql
-- Fechamento e média móvel dos últimos 30 dias — PETR4
SELECT
    data_pregao,
    ticker,
    preco_fechamento,
    media_movel_5d,
    variacao_diaria_pct,
    amplitude_diaria
FROM tc_bovespa_db.tc_acoes_refinadas
WHERE ticker = 'PETR4'
ORDER BY data_pregao DESC
LIMIT 30;
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
ORDER BY ticker, ano_mes DESC;
```

---

## 👥 Tech Challenge — Fase 2 | PosTech FIAP
