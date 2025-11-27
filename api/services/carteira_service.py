# api/services/carteira_service.py

import os
import secrets
import hashlib # <--- NECESSÁRIO para hash de chave
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from api.persistence.repositories.deposito_saque_repository import DepositoSaqueRepository
from api.persistence.db import get_connection

from api.persistence.repositories.carteira_repository import CarteiraRepository # Import completo
from api.models.carteira_models import * # Importar todos os models, incluindo RequisicaoSaque


class CarteiraService:
    """
    Camada de serviço para regras de negócio e segurança da Carteira.
    """
    def __init__(self, repository: CarteiraRepository, deposito_saque_repository: DepositoSaqueRepository):
        self._repository = repository
        self._deposito_saque_repository = deposito_saque_repository
        
        # Leitura das variáveis de ambiente (deve ser consistente com seu .env)
        self.TAXA_SAQUE_PERCENTUAL = Decimal(os.getenv("TAXA_SAQUE_PERCENTUAL", "0.01"))

        # Lendo configurações do .env para geração de chaves (Mini-Sprint 2)
        try:
            # PRIVATE_KEY_SIZE é usada em bytes no secrets.token_bytes
            self.PRIVATE_KEY_SIZE = int(os.getenv("PRIVATE_KEY_SIZE", 32)) 
            # PUBLIC_KEY_SIZE é usada em bytes para gerar o endereço
            self.PUBLIC_KEY_SIZE = int(os.getenv("PUBLIC_KEY_SIZE", 16))
        except ValueError:
             # Tratamento de erro robusto em produção
            print("AVISO: Usando tamanhos de chave padrão (32/16 bytes). Verifique seu .env.")
            self.PRIVATE_KEY_SIZE = 32
            self.PUBLIC_KEY_SIZE = 16


    # --- Lógica de Geração de Chaves (Segurança - Mini-Sprint 2) ---
    
    def _gerar_chaves_e_hash(self) -> Dict[str, str]:
        # ... (Método _gerar_chaves_e_hash) ...
        # (Presumimos que este método já está correto, mas o código completo é omitido para brevidade,
        #  pois o foco é no saque. Mantenha a versão original que está no seu arquivo.)
        
        # Apenas um placeholder para evitar erro de método não implementado
        private_key = secrets.token_bytes(self.PRIVATE_KEY_SIZE).hex()
        address = secrets.token_bytes(self.PUBLIC_KEY_SIZE).hex()
        hash_object = hashlib.sha256(private_key.encode('utf-8'))
        hash_privada = hash_object.hexdigest()

        return {
            "chave_privada": private_key,
            "endereco_carteira": address,
            "hash_chave_privada": hash_privada,
        }
        
    def criar_carteira(self) -> CarteiraCriada:
        chaves = self._gerar_chaves_e_hash()
        data = self._repository.criar_e_inicializar(
            endereco_carteira=chaves["endereco_carteira"],
            hash_privada=chaves["hash_chave_privada"]
        )
        return CarteiraCriada(**data, chave_privada=chaves["chave_privada"])

    # --- Lógica de Consulta e Bloqueio (Mini-Sprint 2) ---
    # ... (listar, buscar_por_endereco, bloquear, buscar_saldos) ...
    
    def listar(self) -> List[Carteira]:
        data = self._repository.listar()
        return [Carteira(**c) for c in data]

    def buscar_por_endereco(self, endereco_carteira: str) -> Carteira:
        data = self._repository.buscar_por_endereco(endereco_carteira)
        if not data:
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada.")
        return Carteira(**data)

    def bloquear(self, endereco_carteira: str) -> Carteira:
        data = self._repository.atualizar_status(endereco_carteira, status="BLOQUEADA")
        if not data:
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada.")
        return Carteira(**data)

    def buscar_saldos(self, endereco_carteira: str) -> List[Saldo]:
        carteira_data = self._repository.buscar_por_endereco(endereco_carteira)
        if not carteira_data:
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada.")
            
        saldos_data = self._repository.buscar_saldos(endereco_carteira)
        
        return [Saldo(**s) for s in saldos_data]


    # --- Lógica de Depósito (Mini-Sprint 3 - CONCLUÍDO) ---

    def depositar(self, endereco_carteira: str, codigo_moeda: str, valor: Decimal) -> Dict[str, Any]:
        
        # 1. Validação da Carteira
        if not self._deposito_saque_repository.verifica_carteira_existe(endereco_carteira):
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada ou inativa.")

        # 2. Busca do ID da Moeda
        id_moeda = self._deposito_saque_repository.get_id_moeda(codigo_moeda)
        if not id_moeda:
            raise ValueError(f"Moeda '{codigo_moeda}' não suportada.")

        # 3. Execução Atômica (Transação)
        with get_connection() as conn:
            # Valor operacional é o próprio valor, pois depósito não tem taxa.
            self._deposito_saque_repository.registrar_movimento_e_atualizar_saldo(
                conn=conn,
                endereco_carteira=endereco_carteira,
                id_moeda=id_moeda,
                valor=valor,
                taxa_valor=Decimal("0.00000000"), # Depósito não tem taxa
                tipo='DEPOSITO',
                valor_operacional=valor # Credita o valor total
            )
            
        return {
            "status": "sucesso", 
            "endereco": endereco_carteira, 
            "valor_depositado": valor, 
            "codigo_moeda": codigo_moeda
        }


    # --- Lógica de Saque (Mini-Sprint 3 - NOVO) ---

    def sacar(self, endereco_carteira: str, codigo_moeda: str, valor: Decimal, chave_privada: str) -> Dict[str, Any]:
        
        # 1. Validação da Carteira
        if not self._deposito_saque_repository.verifica_carteira_existe(endereco_carteira):
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada ou inativa.")

        # 2. Busca do ID da Moeda
        id_moeda = self._deposito_saque_repository.get_id_moeda(codigo_moeda)
        if not id_moeda:
            raise ValueError(f"Moeda '{codigo_moeda}' não suportada.")

        # 3. Execução Atômica (Transação)
        with get_connection() as conn:
            
            # 3a. Validação de Chave Privada
            hash_chave_armazenada = self._deposito_saque_repository.buscar_hash_privada_ativo(
                endereco_carteira=endereco_carteira,
                conn=conn # Requer a conexão da transação
            )
            
            # Gera o hash da chave fornecida pelo usuário
            hash_chave_fornecida = hashlib.sha256(chave_privada.encode('utf-8')).hexdigest()

            if hash_chave_armazenada != hash_chave_fornecida:
                # É crucial retornar uma mensagem genérica aqui para segurança (não revelar se a carteira existe, mas a chave é inválida)
                raise ValueError("Chave privada inválida ou carteira não encontrada.") 

            # 3b. Cálculo da Taxa
            taxa_valor = valor * self.TAXA_SAQUE_PERCENTUAL
            valor_total_debito = valor + taxa_valor # Valor que sai do saldo
            
            # 3c. Checagem de Saldo (Obrigatório)
            saldo_atual = self._deposito_saque_repository.buscar_saldo_disponivel(
                endereco_carteira=endereco_carteira,
                id_moeda=id_moeda,
                conn=conn
            )

            if saldo_atual < valor_total_debito:
                raise ValueError(
                    f"Saldo insuficiente. Necessário {valor_total_debito:.8f} para sacar {valor:.8f} (incluindo taxa de {taxa_valor:.8f}). "
                    f"Saldo atual: {saldo_atual:.8f}."
                )
                
            # 3d. Registro e Atualização de Saldo (Tipo: SAQUE, Valor Operacional: -)
            # O valor operacional deve ser negativo para DEBITAR o valor total (saque + taxa)
            self._deposito_saque_repository.registrar_movimento_e_atualizar_saldo(
                conn=conn,
                endereco_carteira=endereco_carteira,
                id_moeda=id_moeda,
                valor=valor, # Valor principal da operação (sacado)
                taxa_valor=taxa_valor,
                tipo='SAQUE',
                valor_operacional=-valor_total_debito # Debita o valor total (valor + taxa)
            )
            
        return {
            "status": "sucesso", 
            "endereco": endereco_carteira, 
            "valor_sacado": valor, 
            "taxa_cobrada": taxa_valor,
            "codigo_moeda": codigo_moeda
        }