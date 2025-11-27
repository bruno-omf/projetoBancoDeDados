from typing import Literal
from datetime import  datetime
from pydantic import BaseModel, Field
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

class MovimentoBase(BaseModel):
    """Base para Depósito e Saque (o endereço da carteira virá do Path)"""
    codigo_moeda: str = Field(description="Código da moeda da operação (ex: BTC, USD)")
    valor: Decimal = Field(gt=0, decimal_places=8, description="Valor a ser movimentado. Deve ser maior que zero.")


class RequisicaoDeposito(MovimentoBase):
    """Dados necessários para realizar um Depósito."""
    pass # Depósito não exige campos extras além do Base.


class RequisicaoSaque(MovimentoBase):
    """Dados necessários para realizar um Saque."""
    chave_privada: str = Field(min_length=32, max_length=64, description="Chave privada para autenticação do Saque.")
    # Saques exigem validação da chave privada