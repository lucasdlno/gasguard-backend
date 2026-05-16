from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from pydantic import BaseModel


# 1. Configuração do PostgreSQL (Altere 'suasenha' e 'gasguard' para os seus dados)
DATABASE_URL = "postgresql://neondb_owner:npg_0dzel3sJKGIF@ep-restless-tree-apthtfcz.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Tabela do Banco de Dados
class LeituraGas(Base):
    __tablename__ = "leituras"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    gas_level_percentage = Column(Float)
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Cria a tabela automaticamente se não existir
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Permite que o Angular acesse essa API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 3. Formato que o Arduino vai mandar
class LeituraArduino(BaseModel):
    id_dispositivo: str
    nivel_gas: float

# ROTA 1: O Arduino manda os dados para cá (POST)
@app.post("/api/sensor-data")
def receber_dados_arduino(dados: LeituraArduino, db: Session = Depends(get_db)):
    # Define se é perigo ou seguro baseado no nível
    status = "Perigo" if dados.nivel_gas > 2.0 else "Seguro"
    
    nova_leitura = LeituraGas(
        device_id=dados.id_dispositivo,
        gas_level_percentage=dados.nivel_gas,
        status=status
    )
    db.add(nova_leitura)
    db.commit()
    return {"mensagem": "Dados salvos com sucesso!"}

# ROTA 2: O Angular lê os dados por aqui (GET)
@app.get("/api/status")
def ler_status_angular(db: Session = Depends(get_db)):
    # Pega a última leitura cadastrada no banco
    ultima_leitura = db.query(LeituraGas).order_by(LeituraGas.id.desc()).first()
    
    if not ultima_leitura:
        return {"device_name": "Aguardando sensor...", "gas_level_percentage": 0, "status": "Seguro"}
    
    return {
        "device_name": ultima_leitura.device_id,
        "gas_level_percentage": ultima_leitura.gas_level_percentage,
        "status": ultima_leitura.status
    }