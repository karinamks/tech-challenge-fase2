"""
Tech Challenge - Fase 2
Script: tc_lambda.py
Descrição: Função Lambda que é acionada por eventos S3 (PUT de novos arquivos)
           e dispara o Job ETL no AWS Glue automaticamente.
"""

import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Nome do Glue Job — deve ser o mesmo nome cadastrado na AWS
GLUE_JOB_NAME = "tc-etl-bovespa"


def lambda_handler(event, context):
    """
    Handler principal da Lambda.
    Acionado por eventos de escrita no bucket S3 (raw/).
    """
    logger.info(">>> Lambda acionada — evento S3 recebido")
    logger.info(json.dumps(event))

    # Extrai informações do evento S3
    try:
        record    = event["Records"][0]
        bucket    = record["s3"]["bucket"]["name"]
        s3_key    = record["s3"]["object"]["key"]

        logger.info(f"    Bucket : {bucket}")
        logger.info(f"    Arquivo: {s3_key}")

        # Só dispara o Glue se o arquivo estiver na pasta raw/
        if not s3_key.startswith("raw/"):
            logger.info("    [IGNORADO] Arquivo fora da pasta raw/ — sem ação.")
            return {"statusCode": 200, "body": "Arquivo ignorado (fora de raw/)."}

    except (KeyError, IndexError) as e:
        logger.error(f"    [ERRO] Falha ao processar evento S3: {e}")
        raise

    # Aciona o Glue Job
    glue_client = boto3.client("glue")

    try:
        response = glue_client.start_job_run(
            JobName=GLUE_JOB_NAME,
            Arguments={
                "--bucket":  bucket,
                "--s3_key":  s3_key,
            }
        )

        job_run_id = response["JobRunId"]
        logger.info(f"    ✅ Glue Job iniciado com sucesso! JobRunId: {job_run_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message":    "Glue Job iniciado com sucesso.",
                "jobRunId":   job_run_id,
                "glueJob":    GLUE_JOB_NAME,
                "s3Bucket":   bucket,
                "s3Key":      s3_key,
            })
        }

    except Exception as e:
        logger.error(f"    [ERRO] Falha ao iniciar o Glue Job: {e}")
        raise
