# api/routers/carteira_router.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from api.services.carteira_service import CarteiraService
from api.persistence.repositories.carteira_repository import CarteiraRepository
# Importar os Models de Requisição e Resposta (RequisicaoSaque é essencial)
from api.models.carteira_models import Carteira, CarteiraCriada, Saldo, RequisicaoDeposito, RequisicaoSaque 
from api.persistence.repositories.deposito_saque_repository import DepositoSaqueRepository

router = APIRouter(prefix="/carteiras", tags=["carteiras"])


def get_carteira_service() -> CarteiraService:
    # CRÍTICO: Passar os dois repositórios
    carteira_repo = CarteiraRepository()
    deposito_saque_repo = DepositoSaqueRepository()
    return CarteiraService(carteira_repo, deposito_saque_repo)


@router.post("", response_model=CarteiraCriada, status_code=201)
def criar_carteira(
    service: CarteiraService = Depends(get_carteira_service),
)->CarteiraCriada:
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
        
@router.get(
    "/{endereco_carteira}/saldos", 
    response_model=List[Saldo]
)
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
            valor=requisicao.valor
        )
    except ValueError as e:
        # Erros como Carteira inexistente ou Moeda não suportada
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
            chave_privada=requisicao.chave_privada
        )
    except ValueError as e:
        # Erros como Saldo Insuficiente, Chave Inválida, Carteira Inexistente
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Erro genérico (DB ou lógica não capturada)
        raise HTTPException(status_code=500, detail="Erro interno ao processar saque.")