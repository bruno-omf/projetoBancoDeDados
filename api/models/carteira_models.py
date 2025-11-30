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

class RequisicaoConversao(BaseModel):
    """Dados necessários para realizar uma Conversão."""
    codigo_moeda_origem: str = Field(description="Código da moeda a ser debitada (ex: BTC, USD)")
    codigo_moeda_destino: str = Field(description="Código da moeda a ser creditada (ex: ETH, BRL)")
    valor_origem: Decimal = Field(gt=0, decimal_places=8, description="Valor na moeda de origem a ser convertido. Deve ser maior que zero.")
    chave_privada: str = Field(min_length=32, max_length=64, description="Chave privada para autenticação da Conversão.")

class RequisicaoTransferencia(BaseModel):
    """Dados necessários para realizar uma Transferência."""
    codigo_moeda: str = Field(description="Código da moeda a ser transferida (ex: BTC, USD)")
    valor: Decimal = Field(gt=0, decimal_places=8, description="Valor a ser transferido. Deve ser maior que zero.")
    endereco_destino: str = Field(description="Endereço da carteira destino para a transferência.")
    chave_privada: str = Field(min_length=32, max_length=64, description="Chave privada para autenticação da Transferência.")