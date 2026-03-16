"""
Tech Challenge - Fase 2
Script: tc_lambda.py
Descrição: Função Lambda que é acionada por eventos S3 (PUT de novos arquivos)
           e dispara o Job ETL no AWS Glue automaticamente.


"""

import json
import time
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GLUE_JOB_NAME    = "tc-etl-bovespa1"
LOCK_TABLE       = "tc-glue-job-lock"
LOCK_KEY         = "tc-etl-bovespa1"
LOCK_TTL_SECONDS = 3600  # expira em 1 h para não travar indefinidamente


# ---------------------------------------------------------------------------
# Helpers de lock distribuído
# ---------------------------------------------------------------------------

def _acquire_lock(dynamo) -> bool:
    """
    Tenta gravar o item de lock com ConditionExpression que impede substituição
    se ele já existir. Retorna True somente se esta invocação adquiriu o lock.
    """
    ttl = int(time.time()) + LOCK_TTL_SECONDS
    try:
        dynamo.put_item(
            TableName=LOCK_TABLE,
            Item={
                "job_name":  {"S": LOCK_KEY},
                "locked_at": {"N": str(int(time.time()))},
                "ttl":       {"N": str(ttl)},
            },
            ConditionExpression="attribute_not_exists(job_name)",
        )
        logger.info("    [LOCK] Lock adquirido com sucesso.")
        return True
    except dynamo.exceptions.ConditionalCheckFailedException:
        logger.info("    [LOCK] Lock já existe — outra invocação já disparou o job.")
        return False


def _release_lock(dynamo) -> None:
    """Remove o item de lock após o job ser iniciado."""
    try:
        dynamo.delete_item(
            TableName=LOCK_TABLE,
            Key={"job_name": {"S": LOCK_KEY}},
        )
        logger.info("    [LOCK] Lock liberado.")
    except Exception as exc:
        logger.warning(f"    [AVISO] Falha ao liberar lock: {exc}")


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """
    Acionado por eventos de escrita no bucket S3 (raw/).
    Garante disparo único do Glue Job via lock DynamoDB.
    """
    logger.info(">>> Lambda acionada — evento S3 recebido")
    logger.info(json.dumps(event))

    try:
        record  = event["Records"][0]
        bucket  = record["s3"]["bucket"]["name"]
        s3_key  = record["s3"]["object"]["key"]

        logger.info(f"    Bucket : {bucket}")
        logger.info(f"    Arquivo: {s3_key}")

        if not s3_key.startswith("raw/"):
            logger.info("    [IGNORADO] Arquivo fora da pasta raw/ — sem ação.")
            return {"statusCode": 200, "body": "Arquivo ignorado (fora de raw/)."}

    except (KeyError, IndexError) as exc:
        logger.error(f"    [ERRO] Falha ao processar evento S3: {exc}")
        raise

    dynamo = boto3.client("dynamodb")

    if not _acquire_lock(dynamo):
        return {
            "statusCode": 202,
            "body": json.dumps({
                "message": "Glue Job já será iniciado por outra invocação; disparo ignorado.",
                "glueJob":   GLUE_JOB_NAME,
                "s3Bucket":  bucket,
                "s3Key":     s3_key,
            }),
        }

    glue_client = boto3.client("glue")
    try:
        response   = glue_client.start_job_run(
            JobName=GLUE_JOB_NAME,
            Arguments={
                "--bucket":  bucket,
                "--s3_key":  s3_key,
            },
        )
        job_run_id = response["JobRunId"]
        logger.info(f"    ✅ Glue Job iniciado com sucesso! JobRunId: {job_run_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message":   "Glue Job iniciado com sucesso.",
                "jobRunId":  job_run_id,
                "glueJob":   GLUE_JOB_NAME,
                "s3Bucket":  bucket,
                "s3Key":     s3_key,
            }),
        }

    except Exception as exc:
        logger.error(f"    [ERRO] Falha ao iniciar o Glue Job: {exc}")
        _release_lock(dynamo)
        raise

    finally:
        # Libera o lock imediatamente após o start_job_run para que o próximo
        # ciclo de scraping possa disparar normalmente.
        # O Glue verifica concorrência internamente; o lock aqui resolve apenas
        # a race condition entre invocações simultâneas da mesma Lambda.
        try:
            _release_lock(dynamo)
        except Exception:
            pass
