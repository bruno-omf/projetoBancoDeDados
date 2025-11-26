from typing import Literal, Optional
from datetime import  datetime
from pydantic import BaseModel
from decimal import Decimal


class Carteira(BaseModel):
    endereco_carteira: str
    data_criacao: datetime
    status: Literal["ATIVA","BLOQUEADA"]

class CarteiraCriada(Carteira):
    chave_privada: str

class Saldo(BaseModel):
    codigo_moeda: str
    nome_moeda: str
    saldo: Decimal
    data_atualizacao: datetime

class DepositoRequest(BaseModel):
    valor: Decimal
    codigo_moeda: str

class SaqueRequest(BaseModel):
    valor: Decimal
    codigo_moeda: str
    chave_privada: str