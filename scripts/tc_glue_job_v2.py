import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Inicialização do Glue e Spark
args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Configurações de compatibilidade para leitura de Parquet com timestamp
spark.conf.set("spark.sql.parquet.int96RebaseModeInRead", "CORRECTED")
spark.conf.set("spark.sql.parquet.datetimeRebaseModeInRead", "CORRECTED")
spark.conf.set("spark.sql.parquet.int96RebaseModeInWrite", "CORRECTED")
spark.conf.set("spark.sql.parquet.datetimeRebaseModeInWrite", "CORRECTED")
spark.conf.set("spark.sql.legacy.parquet.nanosAsLong", "true")

job = Job(glueContext)
job.init(args["JOB_NAME"], args)

BUCKET_NAME  = "techchallenge-bovespa-pipeline"
RAW_PATH     = f"s3://{BUCKET_NAME}/raw/"
REFINED_PATH = f"s3://{BUCKET_NAME}/refined/"
DATABASE     = "tc_bovespa_db"
TABLE_NAME   = "tc_acoes_refinadas"

# Leitura dos dados brutos da camada raw (Requisito 2)
df_raw = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [RAW_PATH], "recurse": True},
    format="parquet",
    format_options={"mergeSchema": "true"}
).toDF()

# Converte colunas timestamp para string para evitar incompatibilidade de tipos
df = df_raw
for field in df.schema.fields:
    if str(field.dataType) in ["TimestampNTZType()", "TimestampType()"]:
        df = df.withColumn(field.name, F.col(field.name).cast("string"))

df = df.toDF(*[c.lower() for c in df.columns])

# Requisito 5-B: Renomeando colunas
df = df \
    .withColumnRenamed("open",   "preco_abertura") \
    .withColumnRenamed("close",  "preco_fechamento") \
    .withColumnRenamed("high",   "preco_maximo") \
    .withColumnRenamed("low",    "preco_minimo") \
    .withColumnRenamed("volume", "volume_negociado") \
    .withColumnRenamed("date",   "data_pregao")

# Tipagem correta das colunas
df = df \
    .withColumn("data_pregao",      F.to_date(F.col("data_pregao").cast("string"))) \
    .withColumn("preco_abertura",   F.col("preco_abertura").cast("double")) \
    .withColumn("preco_fechamento", F.col("preco_fechamento").cast("double")) \
    .withColumn("preco_maximo",     F.col("preco_maximo").cast("double")) \
    .withColumn("preco_minimo",     F.col("preco_minimo").cast("double")) \
    .withColumn("volume_negociado", F.col("volume_negociado").cast("long")) \
    .dropna(subset=["data_pregao", "preco_fechamento", "ticker"])

# Requisito 5-C: Cálculos baseados em data
janela = Window.partitionBy("ticker").orderBy("data_pregao").rowsBetween(-4, 0)

df = df \
    .withColumn("media_movel_5d",
                F.round(F.avg("preco_fechamento").over(janela), 4)) \
    .withColumn("variacao_diaria_pct",
                F.round(((F.col("preco_fechamento") - F.col("preco_abertura"))
                          / F.col("preco_abertura")) * 100, 4)) \
    .withColumn("amplitude_diaria",
                F.round(F.col("preco_maximo") - F.col("preco_minimo"), 4)) \
    .withColumn("ano_mes",
                F.date_format("data_pregao", "yyyy-MM"))

# Requisito 5-A: Agrupamento e sumarização mensal por ticker
df_resumo = df.groupBy("ticker", "ano_mes").agg(
    F.round(F.avg("preco_fechamento"), 4).alias("media_fechamento_mes"),
    F.round(F.max("preco_maximo"), 4).alias("maximo_mes"),
    F.round(F.min("preco_minimo"), 4).alias("minimo_mes"),
    F.sum("volume_negociado").alias("volume_total_mes"),
    F.count("data_pregao").alias("qtd_pregoes_mes")
)

df_final = df.join(df_resumo, on=["ticker", "ano_mes"], how="left") \
             .withColumn("data_particao", F.date_format("data_pregao", "yyyy-MM-dd"))

# Requisito 6: Salvando dados refinados no S3 particionado por data e ticker
df_final.write \
    .mode("overwrite") \
    .partitionBy("data_particao", "ticker") \
    .parquet(REFINED_PATH)

# Requisito 7: Catalogação automática no Glue Catalog
# FIX: Usar CREATE TABLE sem especificar partições no DDL
# O MSCK REPAIR TABLE descobre as partições automaticamente
spark.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
spark.sql(f"DROP TABLE IF EXISTS {DATABASE}.{TABLE_NAME}")
spark.sql(f"""
    CREATE TABLE {DATABASE}.{TABLE_NAME}
    USING PARQUET
    LOCATION '{REFINED_PATH}'
""")
spark.sql(f"MSCK REPAIR TABLE {DATABASE}.{TABLE_NAME}")

job.commit()