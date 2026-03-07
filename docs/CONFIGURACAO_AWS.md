# 🛠️ Passo a Passo — Configuração AWS
## Tech Challenge Fase 2 | Pipeline Batch Bovespa
### Essa configuração se aplica somente para usuários da conta AWS Academy

---

## PRÉ-REQUISITOS

- Conta AWS Academy ativa com laboratório iniciado
- AWS CLI instalado e configurado
- Python 3.11+ com as libs: `yfinance`, `pandas`, `boto3`, `pyarrow`

> ⚠️ As credenciais do AWS Academy expiram a cada sessão de 4 horas. Sempre atualize com `aws configure` ao iniciar um novo lab.

---

## PASSO 1 — Configurar Credenciais AWS

1. No AWS Academy, clique em **AWS Details → Show** (ao lado de AWS CLI)
2. Copie as três linhas com `aws_access_key_id`, `aws_secret_access_key` e `aws_session_token`
3. No CMD/terminal:
```bash
aws configure
# Preencha: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)

aws configure set aws_session_token SEU_TOKEN_AQUI
```
4. Teste:
```bash
aws s3 ls
```

---

## PASSO 2 — Criar o Bucket S3

```bash
aws s3 mb s3://techchallenge-bovespa-pipeline1 --region us-east-1

aws s3api put-object --bucket techchallenge-bovespa-pipeline1 --key raw/
aws s3api put-object --bucket techchallenge-bovespa-pipeline1 --key refined/
aws s3api put-object --bucket techchallenge-bovespa-pipeline1 --key athena-results/
aws s3api put-object --bucket techchallenge-bovespa-pipeline1 --key scripts/
```

Upload dos scripts para o S3:
```bash
aws s3 cp scripts/tc_glue_job_v3.py s3://techchallenge-bovespa-pipeline1/scripts/
aws s3 cp scripts/tc_lambda.py s3://techchallenge-bovespa-pipeline1/scripts/
aws s3 cp scripts/tc_scraping.py s3://techchallenge-bovespa-pipeline1/scripts/
```

> ✅ REQ 2 preparado.

---

## PASSO 3 — Criar o Glue Job

1. Console AWS → **AWS Glue → ETL Jobs → Script editor**
2. Engine: **Spark** → Upload script → selecione `tc_glue_job_v3.py`
3. Clique em **Create** e configure na aba **Job details**:
   - **Job name:** `tc-etl-bovespa`
   - **IAM Role:** `LabRole`
   - **Glue version:** Glue 5.0
   - **Worker type:** G.1X
   - **Number of workers:** 2
4. Clique em **Save**

> ✅ REQ 5, REQ 6 e REQ 7 preparados.

---

## PASSO 4 — Criar a Lambda de Gatilho

1. Console AWS → **Lambda → Create function**
2. Configure:
   - **Function name:** `tc-lambda-bovespa`
   - **Runtime:** Python 3.11
   - **Execution role:** Use existing role → **LabRole**
3. Cole o conteúdo de `tc_lambda.py` no editor de código
4. Clique em **Deploy**

### Adicionar Trigger S3
5. Clique em **Add trigger**
6. Configure:
   - **Source:** S3
   - **Bucket:** `techchallenge-bovespa-pipeline1`
   - **Event type:** PUT
   - **Prefix:** `raw/`
7. Marque a caixa de confirmação → **Add**

> ✅ REQ 3 e REQ 4 concluídos.

---

## PASSO 5 — Criar a Lambda de Scraping

1. Console AWS → **Lambda → Create function**
2. Configure:
   - **Function name:** `tc-lambda-scraping`
   - **Runtime:** Python 3.11
   - **Execution role:** Use existing role → **LabRole**
3. Cole o conteúdo de `tc_lambda_scraping.py` no editor
4. Clique em **Deploy**
5. Vá em **Configuration → General configuration → Edit**:
   - **Memory:** 512 MB
   - **Timeout:** 5 min 0 sec
6. Clique em **Save**

---

## PASSO 6 — Criar o EventBridge Schedule

1. Console AWS → **EventBridge → Schedules → Create schedule**
2. Configure:
   - **Schedule name:** `tc-scraping-diario`
   - **Occurrence:** Recurring schedule
   - **Schedule type:** Cron-based
   - **Cron:** `0 22 * * ? *`
   - **Timezone:** America/Sao_Paulo
   - **Flexible time window:** Off
3. Clique em **Next**
4. **Target:** AWS Lambda → Invoke → selecione `tc-lambda-scraping`
5. Clique em **Next**
6. Em **Permissions → Execution role:** Use existing role → **LabRole**
7. Clique em **Next → Create schedule**

---

## PASSO 7 — Configurar o Athena

1. Console AWS → **Athena → Launch query editor**
2. Clique em **Edit settings**
3. **Query result location:** `s3://techchallenge-bovespa-pipeline1/athena-results/`
4. Clique em **Save**

---

## PASSO 8 — Executar o Pipeline pela Primeira Vez

1. Execute o scraping manualmente:
```bash
python scripts/tc_scraping.py
```
2. Aguarde os arquivos aparecerem em `s3://.../raw/`
3. A Lambda dispara automaticamente o Glue Job
4. Acompanhe em **Glue → Jobs → tc-etl-bovespa → Runs** — aguarde **Succeeded**
5. Verifique no **Glue Catalog → Databases → tc_bovespa_db → tc_acoes_refinadas**
6. Teste no Athena:
```sql
SELECT ticker, data_pregao, preco_fechamento, media_movel_5d
FROM tc_acoes_refinadas
WHERE ticker = 'PETR4'
ORDER BY data_pregao DESC
LIMIT 10;
```

---

## ⚠️ Problemas Comuns

| Problema | Solução |
|----------|---------|
| `AccessDenied` no S3 | Atualizar credenciais AWS Academy (`aws configure`) |
| Lambda não dispara | Verificar se o trigger S3 tem prefixo `raw/` e evento `PUT` |
| Glue Job `ConcurrentRunsExceeded` | Aguardar — a Lambda já disparou o job automaticamente |
| Athena sem resultado | Executar `MSCK REPAIR TABLE tc_acoes_refinadas` manualmente |
| EventBridge sem permissão para criar role | Em Permissions, usar **LabRole** existente em vez de criar nova |
| Credenciais AWS Academy expiradas | Reiniciar sessão do lab e rodar `aws configure` novamente |
