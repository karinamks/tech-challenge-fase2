"""
Script: tc_lambda_scraping.py
Descrição: Lambda agendada pelo EventBridge que executa o scraping
           de dados da B3 via yfinance e salva no S3.
"""

import json
import subprocess
import sys
import boto3
import io
from datetime import datetime, timedelta

def lambda_handler(event, context):
    # Instala dependências em runtime
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "yfinance", "pandas", "pyarrow", "-q"
    ])
    
    import yfinance as yf
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    BUCKET_NAME = "techchallenge-bovespa-pipeline1"
    PREFIX_RAW  = "raw"
    TICKERS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA"]
    
    END_DATE   = datetime.today()
    START_DATE = END_DATE - timedelta(days=30)
    
    s3_client = boto3.client("s3")
    
    for ticker in TICKERS:
        print(f"Baixando {ticker}...")
        df = yf.download(ticker, 
                        start=START_DATE.strftime("%Y-%m-%d"),
                        end=END_DATE.strftime("%Y-%m-%d"), 
                        progress=False)
        
        if df.empty:
            print(f"Sem dados para {ticker}")
            continue
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].astype(str)
        
        ticker_codigo = ticker.replace(".SA", "")
        df["ticker"] = ticker_codigo
        df["data_extracao"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        df["data_particao"] = df["date"].astype(str).str[:10]
        
        for data_particao, grupo in df.groupby("data_particao"):
            buffer = io.BytesIO()
            grupo.to_parquet(buffer, index=False, engine="pyarrow")
            buffer.seek(0)
            
            s3_key = f"{PREFIX_RAW}/data_particao={data_particao}/ticker={ticker_codigo}/dados.parquet"
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=buffer.getvalue()
            )
            print(f"✅ Salvo: s3://{BUCKET_NAME}/{s3_key}")
    
    return {
        "statusCode": 200,
        "body": json.dumps("Scraping finalizado com sucesso!")
    }