# api/routers/carteira_router.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from api.services.carteira_service import CarteiraService
from api.persistence.repositories.carteira_repository import CarteiraRepository
from api.persistence.repositories.deposito_saque_repository import DepositoSaqueRepository
from api.persistence.repositories.conversao_repository import ConversaoRepository
from api.persistence.repositories.transferencia_repository import TransferenciaRepository
# Importar os Models de Requisição e Resposta (RequisicaoSaque é essencial)
from api.models.carteira_models import (
    Carteira,
    CarteiraCriada,
    Saldo,
    RequisicaoDeposito,
    RequisicaoSaque,
    RequisicaoConversao,
    RequisicaoTransferencia
)


router = APIRouter(prefix="/carteiras", tags=["carteiras"])


def get_carteira_service() -> CarteiraService:
    # CRÍTICO: Passar os dois repositórios
    carteira_repo = CarteiraRepository()
    deposito_saque_repo = DepositoSaqueRepository()
    conversao_repo = ConversaoRepository()
    transferencia_repo = TransferenciaRepository()

    return CarteiraService(carteira_repo, deposito_saque_repo, conversao_repo, transferencia_repo)


@router.post("", response_model=CarteiraCriada, status_code=201)
def criar_carteira(
    service: CarteiraService = Depends(get_carteira_service),
) -> CarteiraCriada:
    """
    Cria uma nova carteira. O body é opcional .
    Retorna endereço e chave privada (apenas nesta resposta).
    """
    try:
        return service.criar_carteira()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[Carteira])
def listar_carteiras(service: CarteiraService = Depends(get_carteira_service)):
    return service.listar()


@router.get("/{endereco_carteira}", response_model=Carteira)
def buscar_carteira(
    endereco_carteira: str,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.buscar_por_endereco(endereco_carteira)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{endereco_carteira}", response_model=Carteira)
def bloquear_carteira(
    endereco_carteira: str,
    service: CarteiraService = Depends(get_carteira_service),
):
    try:
        return service.bloquear(endereco_carteira)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{endereco_carteira}/saldos", response_model=List[Saldo])
def buscar_saldos(
    endereco_carteira: str,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Retorna a lista de saldos (moeda e valor) para a carteira.
    """
    try:
        return service.buscar_saldos(endereco_carteira)
    except ValueError as e:
        # Erro de Carteira não encontrada.
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{endereco_carteira}/depositos", status_code=200)
def realizar_deposito(
    endereco_carteira: str,
    requisicao: RequisicaoDeposito,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Registra um depósito na carteira especificada.
    Não exige chave privada e não aplica taxa.
    """
    try:
        return service.depositar(
            endereco_carteira=endereco_carteira,
            codigo_moeda=requisicao.codigo_moeda,
            valor=requisicao.valor,
        )
    except ValueError as e:
        # Erros como Carteira inexistente ou Moeda não suportada
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Erro genérico (DB ou lógica não capturada)
        raise HTTPException(status_code=500, detail="Erro interno ao processar depósito.")


@router.post("/{endereco_carteira}/saques", status_code=200)
def realizar_saque(
    endereco_carteira: str,
    requisicao: RequisicaoSaque,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Registra um saque na carteira. Exige chave privada e aplica taxa.
    """
    try:
        return service.sacar(
            endereco_carteira=endereco_carteira,
            codigo_moeda=requisicao.codigo_moeda,
            valor=requisicao.valor,
            chave_privada=requisicao.chave_privada,
        )
    except ValueError as e:
        # Erros como Saldo Insuficiente, Chave Inválida, Carteira Inexistente
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Erro genérico (DB ou lógica não capturada)
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar: {type(e).__name__} - {str(e)}")
        # Antes: raise HTTPException(status_code=500, detail="Erro interno ao processar saque.")


@router.post("/{endereco_carteira}/conversoes", status_code=200)
def realizar_conversao(
    endereco_carteira: str,
    requisicao: RequisicaoConversao,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Realiza a conversão de fundos entre duas moedas.
    Exige chave privada da carteira, busca cotação na Coinbase e aplica taxa.
    """
    try:
        return service.converter_moeda(
            endereco_carteira=endereco_carteira,
            codigo_moeda_origem=requisicao.codigo_moeda_origem,
            codigo_moeda_destino=requisicao.codigo_moeda_destino,
            valor_origem=requisicao.valor_origem,
            chave_privada=requisicao.chave_privada,
        )
    except ValueError as e:
        # Erros 400: Saldo Insuficiente, Chave Inválida, Moeda Não Suportada (Coinbase)
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Erros 503: Falha de comunicação com a Coinbase
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar: {type(e).__name__} - {str(e)}")
        # Antes: raise HTTPException(status_code=500, detail="Erro interno ao processar saque.")

@router.post("/{endereco_origem}/transferencias", status_code=200)
def realizar_transferencia(
    endereco_origem: str,
    requisicao: RequisicaoTransferencia,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Realiza a transferência de fundos entre duas carteiras.
    Exige chave privada da carteira de origem, debita com taxa e credita destino sem taxa.
    """
    try:
        return service.transferir_moeda(
            endereco_origem=endereco_origem,
            endereco_destino=requisicao.endereco_destino,
            codigo_moeda=requisicao.codigo_moeda,
            valor_transferencia=requisicao.valor,
            chave_privada=requisicao.chave_privada,
        )
    except ValueError as e:
        # Erros 400: Saldo Insuficiente, Chave Inválida, Carteira Inexistente, Moeda Não Suportada.
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Erro genérico (DB ou lógica não capturada)
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar transferência: {str(e)}")