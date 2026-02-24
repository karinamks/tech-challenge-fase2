# 🛠️ Passo a Passo — Configuração AWS
## Tech Challenge Fase 2 | Pipeline Batch Bovespa

---

## PRÉ-REQUISITOS

- Conta AWS Academy ativa com laboratório iniciado
- AWS CLI configurado (ou usar o console web)
- Python 3.11+ com as libs: `yfinance`, `pandas`, `boto3`, `pyarrow`

---

## PASSO 1 — Criar o Bucket S3

1. Acesse **AWS Console → S3 → Create bucket**
2. Configure:
   - **Bucket name:** `techchallenge-bovespa-pipeline`
   - **Region:** `us-east-1`
   - **Block public access:** ✅ Deixar bloqueado (padrão)
3. Clique em **Create bucket**
4. Dentro do bucket, crie manualmente as pastas:
   - `raw/`
   - `refined/`

> ✅ REQ 2 preparado.

---

## PASSO 2 — Executar o Scraping

1. No terminal local (ou no Cloud9/EC2), instale as dependências:
```bash
pip install yfinance pandas boto3 pyarrow
```

2. Configure as credenciais AWS:
```bash
aws configure
# Preencha: Access Key, Secret Key, Region (us-east-1), Output (json)
```

> Se estiver no AWS Academy, copie as credenciais do painel "AWS Details" → "AWS CLI".

3. Execute o script:
```bash
python tc_scraping.py
```

4. Verifique no S3 se a estrutura `raw/data_particao=.../ticker=.../dados.parquet` foi criada.

> ✅ REQ 1 e REQ 2 concluídos.

---

## PASSO 3 — Criar o Glue Job

1. Acesse **AWS Console → AWS Glue → ETL Jobs → Create job**
2. Selecione **Script editor** → **Upload script** → suba o arquivo `tc_glue_job.py`
3. Configure:
   - **Job name:** `tc-etl-bovespa`
   - **IAM Role:** selecione uma role com permissões para S3 e Glue (ex: `AWSGlueServiceRole`)
   - **Glue version:** Glue 4.0
   - **Language:** Python 3
   - **Worker type:** G.1X
   - **Number of workers:** 2
4. Clique em **Save**
5. Para testar, clique em **Run** e aguarde o status **Succeeded**
6. Verifique:
   - Pasta `refined/` populada no S3
   - Banco `tc_bovespa_db` e tabela `tc_acoes_refinadas` criados no Glue Catalog

> ✅ REQ 5, REQ 6 e REQ 7 concluídos.

---

## PASSO 4 — Criar a Função Lambda

1. Acesse **AWS Console → Lambda → Create function**
2. Configure:
   - **Function name:** `tc-lambda-bovespa`
   - **Runtime:** Python 3.11
   - **Permissions:** selecione ou crie uma role com permissão `glue:StartJobRun`
3. Na aba **Code**, cole o conteúdo do arquivo `tc_lambda.py`
4. Clique em **Deploy**

### Adicionar Trigger S3

5. Clique em **Add trigger**
6. Configure:
   - **Source:** S3
   - **Bucket:** `techchallenge-bovespa-pipeline`
   - **Event type:** `PUT`
   - **Prefix:** `raw/`
7. Clique em **Add**

### Verificar permissão da role Lambda

A role da Lambda precisa ter a seguinte política inline (ou equivalente):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "glue:StartJobRun",
      "Resource": "*"
    }
  ]
}
```

> ✅ REQ 3 e REQ 4 concluídos.

---

## PASSO 5 — Verificar o Glue Catalog

1. Acesse **AWS Console → AWS Glue → Databases**
2. Confirme que o banco `tc_bovespa_db` existe
3. Clique no banco → **Tables** → confirme a tabela `tc_acoes_refinadas`
4. Clique na tabela e verifique as colunas no schema

> ✅ REQ 7 confirmado.

---

## PASSO 6 — Consultar via Athena

1. Acesse **AWS Console → Athena → Query editor**
2. No painel lateral, selecione:
   - **Data source:** AwsDataCatalog
   - **Database:** `tc_bovespa_db`
3. Configure o **Query result location** (necessário na primeira vez):
   - Clique em **Settings → Manage**
   - Defina: `s3://techchallenge-bovespa-pipeline/athena-results/`
4. Execute a query de teste:

```sql
SELECT
    data_pregao,
    ticker,
    preco_fechamento,
    media_movel_5d,
    variacao_diaria_pct
FROM tc_acoes_refinadas
WHERE ticker = 'PETR4'
ORDER BY data_pregao DESC
LIMIT 10;
```

> ✅ REQ 8 concluído.

---

## PASSO 7 — Teste do Fluxo Completo (End-to-End)

Para confirmar que tudo funciona junto:

1. Execute novamente o `tc_scraping.py`
2. Aguarde ~1 minuto
3. Acesse **Lambda → Monitor → Logs** e confirme que a função foi disparada
4. Acesse **Glue → Jobs → tc-etl-bovespa → Run history** e confirme um novo run **Succeeded**
5. Execute uma query no Athena e confirme que os dados mais recentes aparecem

---

## ⚠️ Problemas Comuns

| Problema | Solução |
|----------|---------|
| Lambda não dispara | Verificar se o trigger S3 está com prefixo `raw/` correto |
| Glue Job com erro de permissão | Adicionar `AmazonS3FullAccess` e `AWSGlueServiceRole` à role |
| Athena sem resultado | Executar `MSCK REPAIR TABLE tc_acoes_refinadas` manualmente |
| Credenciais AWS Academy expiradas | Reiniciar o laboratório e atualizar as credenciais |
| Tabela não aparece no Catalog | Verificar se o Glue Job rodou com sucesso até o final |
