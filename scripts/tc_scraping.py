"""
Tech Challenge - Fase 2
Script: tc_scraping.py
Descrição: Baixa dados diários de ações da B3 via yfinance e salva no S3 em formato Parquet
           particionado por data.
"""

import yfinance as yf
import pandas as pd
import boto3
import io
from datetime import datetime, timedelta

BUCKET_NAME = "techchallenge-bovespa-pipeline"
PREFIX_RAW  = "raw"

TICKERS = [
    "PETR4.SA",
    "VALE3.SA",
    "ITUB4.SA",
    "BBDC4.SA",
    "ABEV3.SA",
]

END_DATE   = datetime.today()
START_DATE = END_DATE - timedelta(days=30)


def baixar_dados(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    print(f"  Baixando dados de {ticker}...")
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                     end=end.strftime("%Y-%m-%d"), progress=False)

    if df.empty:
        print(f"  [AVISO] Nenhum dado encontrado para {ticker}.")
        return pd.DataFrame()

    # Achata colunas MultiIndex caso existam
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df.reset_index()
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Converte todas as colunas de data/datetime para string
    # para evitar incompatibilidade de tipos no Glue/Parquet
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].astype(str)

    df["ticker"]        = ticker.replace(".SA", "")
    df["data_extracao"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    df["data_particao"] = df["date"].astype(str).str[:10]

    return df


def salvar_parquet_s3(df: pd.DataFrame, ticker: str, s3_client) -> None:
    ticker_codigo = ticker.replace(".SA", "")

    for data_particao, grupo in df.groupby("data_particao"):
        buffer = io.BytesIO()
        grupo.to_parquet(buffer, index=False, engine="pyarrow")
        buffer.seek(0)

        s3_key = (
            f"{PREFIX_RAW}/"
            f"data_particao={data_particao}/"
            f"ticker={ticker_codigo}/"
            f"dados.parquet"
        )

        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=buffer.getvalue()
        )
        print(f"  ✅ Salvo: s3://{BUCKET_NAME}/{s3_key}")


def main():
    print("=" * 60)
    print("Tech Challenge - Pipeline Bovespa | Scraping B3")
    print(f"Período: {START_DATE.strftime('%Y-%m-%d')} → {END_DATE.strftime('%Y-%m-%d')}")
    print("=" * 60)

    s3_client = boto3.client("s3")

    for ticker in TICKERS:
        print(f"\n[{ticker}]")
        df = baixar_dados(ticker, START_DATE, END_DATE)
        if df.empty:
            continue
        salvar_parquet_s3(df, ticker, s3_client)

    print("\n" + "=" * 60)
    print("✅ Scraping finalizado com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    main()
