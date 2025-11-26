from fastapi import APIRouter, HTTPException, Depends
from typing import List

from api.services.carteira_service import CarteiraService
from api.persistence.repositories.carteira_repository import CarteiraRepository
from api.models.carteira_models import Carteira, CarteiraCriada, Saldo, DepositoRequest, SaqueRequest


router = APIRouter(prefix="/carteiras", tags=["carteiras"])


def get_carteira_service() -> CarteiraService:
    repo = CarteiraRepository()
    return CarteiraService(repo)


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

# Endpoint: POST /carteiras/{endereco_carteira}/depositos
@router.post("/{endereco_carteira}/depositos", status_code=200)
def realizar_deposito(
    endereco_carteira: str,
    movimento: DepositoRequest,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Registra um depósito na carteira (sem taxa).
    Requisito: Valor creditado sem taxa.
    """
    try:
        saldo_atualizado = service.depositar(
            endereco_carteira=endereco_carteira,
            valor=movimento.valor,
            codigo_moeda=movimento.codigo_moeda
        )
        return {"mensagem": "Depósito realizado com sucesso.", "saldo_atualizado": saldo_atualizado}
    except ValueError as e:
        # Erro 400 se a carteira/moeda não for encontrada ou valor for inválido
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao realizar depósito: {str(e)}")


# Endpoint: POST /carteiras/{endereco_carteira}/saques
@router.post("/{endereco_carteira}/saques", status_code=200)
def realizar_saque(
    endereco_carteira: str,
    movimento: SaqueRequest,
    service: CarteiraService = Depends(get_carteira_service),
):
    """
    Registra um saque na carteira (com taxa e validação de chave privada).
    Requisito: Debita valor + taxa e validação obrigatória da chave privada (hash).
    """
    try:
        saldo_atualizado = service.sacar(
            endereco_carteira=endereco_carteira,
            valor=movimento.valor,
            codigo_moeda=movimento.codigo_moeda,
            chave_privada=movimento.chave_privada
        )
        return {"mensagem": "Saque realizado com sucesso.", "saldo_atualizado": saldo_atualizado}
    except ValueError as e:
        # Erros 400/403/404 (saldo insuficiente, chave inválida, carteira não encontrada)
        # 403 Forbidden é uma boa prática para falha de autenticação (chave privada inválida)
        status_code = 403 if 'chave' in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao realizar saque: {str(e)}")

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
        # Erro 404 se a carteira não for encontrada
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Outros erros de sistema/banco
        raise HTTPException(status_code=500, detail=f"Erro ao buscar saldos: {str(e)}")
