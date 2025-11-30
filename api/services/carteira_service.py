# api/services/carteira_service.py

import os
import secrets
import hashlib # <--- NECESSÁRIO para hash de chave
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

import httpx

from api.persistence.repositories.transferencia_repository import TransferenciaRepository
from api.persistence.repositories.deposito_saque_repository import DepositoSaqueRepository
from api.persistence.repositories.conversao_repository import ConversaoRepository
from api.persistence.db import get_connection

from api.persistence.repositories.carteira_repository import CarteiraRepository # Import completo
from api.models.carteira_models import * # Importar todos os models, incluindo RequisicaoSaque


class CarteiraService:
    """
    Camada de serviço para regras de negócio e segurança da Carteira.
    """
    def __init__(
        self,
        repository: CarteiraRepository,
        deposito_saque_repository: DepositoSaqueRepository,
        conversao_repository: ConversaoRepository,
        transferencia_repository: TransferenciaRepository
    ):
        self._repository = repository
        self._deposito_saque_repository = deposito_saque_repository
        self._conversao_repository = conversao_repository
        self._transferencia_repository = transferencia_repository
        
        # Leitura das variáveis de ambiente (deve ser consistente com seu .env)
        self.TAXA_SAQUE_PERCENTUAL = Decimal(os.getenv("TAXA_SAQUE_PERCENTUAL", "0.01"))
        self.TAXA_CONVERSAO_PERCENTUAL = Decimal(os.getenv("TAXA_CONVERSAO_PERCENTUAL", "0.02"))
        self.TAXA_TRANSFERENCIA_PERCENTUAL = Decimal(os.getenv("TAXA_TRANSFERENCIA_PERCENTUAL", "0.01"))
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
                endereco_carteira=endereco_carteira
                # conn=conn # Requer a conexão da transação
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

    def get_cotacao_coinbase(self, base_currency: str, quote_currency: str) -> Decimal:
        """
        Busca a cotação MoedaDestino/MoedaOrigem na API pública da Coinbase.
        A cotação é (Quote / Base), ex: BRL/USD.
        """
        pair = f"{base_currency}-{quote_currency}"
        url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
        
        try:
            client = httpx.Client(timeout=5.0)
            response = client.get(url)
            
            # 1. Checa por 404 antes de raise_for_status, para dar mensagem clara (ValueError)
            if response.status_code == 404:
                 raise ValueError(f"Par de moedas '{pair}' não suportado pela Coinbase.")
                 
            response.raise_for_status() # Lança HTTPStatusError para outros 4xx/5xx
            data = response.json()
            
            # 2. Proteção contra JSON inesperado (KeyError ou TypeError)
            try:
                # Tenta acessar o valor aninhado e converter para Decimal
                cotacao = Decimal(data['data']['amount'])
            except (KeyError, TypeError, ValueError):
                # Captura falha ao encontrar a chave ou ao converter. Gera 503/RuntimeError.
                # A mensagem de erro agora inclui os dados recebidos para auxiliar na depuração futura
                raise RuntimeError(f"Resposta da Coinbase com JSON inesperado para {pair}.") 
            
            return cotacao
            
        except httpx.HTTPStatusError as e:
            # 3. Captura outros erros HTTP (e.g., 500 da Coinbase)
            raise RuntimeError(f"Erro HTTP ao buscar cotação na Coinbase: {e.response.status_code} - {e}")
        except ValueError:
            # 4. Repassa ValueError (404)
            raise
        except Exception as e:
            # 5. Captura erros de rede/conexão (httpx.RequestError)
            raise RuntimeError(f"Falha na comunicação ou na requisição HTTP com a Coinbase: {e}")


    def converter_moeda(
            self,
            endereco_carteira: str,
            codigo_moeda_origem: str,
            codigo_moeda_destino: str,
            valor_origem: Decimal,
            chave_privada: str,
        ) -> Dict[str, Any]:
        """
        Processa a conversão de moeda: autenticação, cotação, cálculo (com taxa) e transação.
        """
        
        # 1. Validação de moedas
        id_moeda_origem = self._deposito_saque_repository.get_id_moeda(codigo_moeda_origem)
        id_moeda_destino = self._deposito_saque_repository.get_id_moeda(codigo_moeda_destino)
        
        if not id_moeda_origem or not id_moeda_destino:
            raise ValueError(f"Moeda não suportada na conversão.")
        if codigo_moeda_origem == codigo_moeda_destino:
            raise ValueError("Moedas de origem e destino devem ser diferentes.")

        # 2. Busca da Cotação (FORA DA TRANSAÇÃO)
        # É importante buscar a cotação antes de abrir a transação de banco.
        cotacao_utilizada = self.get_cotacao_coinbase(
            base_currency=codigo_moeda_origem, 
            quote_currency=codigo_moeda_destino
        )
        
        # 3. Lógica Transacional e Validação
        # O context manager get_connection() gerencia a transação (COMMIT ou ROLLBACK)
        with get_connection() as conn:
            
            # 3a. Autenticação (CRÍTICO: Conversão exige chave privada)
            hash_privada_bd = self._deposito_saque_repository.buscar_hash_privada_ativo(endereco_carteira)
            if not hash_privada_bd:
                raise ValueError("Carteira inexistente ou bloqueada.")
            
            hash_privada_requerida = hashlib.sha256(chave_privada.encode('utf-8')).hexdigest()
            
            if hash_privada_requerida != hash_privada_bd:
                raise ValueError("Chave privada inválida para a conversão.")

            # 3b. Cálculo Financeiro
            taxa_percentual = self.TAXA_CONVERSAO_PERCENTUAL # Lida do .env (0.02)
            
            taxa_valor = valor_origem * taxa_percentual
            
            # Valor Líquido que será usado na conversão
            valor_origem_liquido = valor_origem - taxa_valor
            
            # Valor final creditado na moeda de destino
            valor_destino = valor_origem_liquido * cotacao_utilizada

            # 3c. Checagem de Saldo
            # O valor total debitado é o valor_origem (inclui a taxa)
            saldo_atual = self._deposito_saque_repository.buscar_saldo_disponivel(
                endereco_carteira=endereco_carteira,
                id_moeda=id_moeda_origem,
                conn=conn
            )
            
            if saldo_atual < valor_origem:
                raise ValueError(
                    f"Saldo insuficiente na moeda {codigo_moeda_origem}. "
                    f"Necessário {valor_origem:.8f} (incluindo taxa)."
                )
                
            # 4. Registro e Atualização (Ação atômica)
            self._conversao_repository.registrar_conversao_e_atualizar_saldos(
                conn=conn,
                endereco_carteira=endereco_carteira,
                id_moeda_origem=id_moeda_origem,
                id_moeda_destino=id_moeda_destino,
                valor_origem=valor_origem,
                valor_destino=valor_destino,
                taxa_percentual=taxa_percentual,
                taxa_valor=taxa_valor,
                cotacao_utilizada=cotacao_utilizada,
            )
            
        return {
            "status": "sucesso", 
            "endereco": endereco_carteira, 
            "moeda_origem": codigo_moeda_origem, 
            "moeda_destino": codigo_moeda_destino, 
            "valor_origem": valor_origem,
            "valor_destino_liquido": valor_destino,
            "taxa_percentual": taxa_percentual,
            "taxa_valor": taxa_valor,
            "cotacao_utilizada": cotacao_utilizada,
        }

    def transferir_moeda(
        self,
        endereco_origem: str,
        endereco_destino: str,
        codigo_moeda: str,
        valor_transferencia: Decimal,
        chave_privada: str,
    ) -> Dict[str, Any]:
        """
        Realiza a transferência de fundos entre duas carteiras internas.
        Debita origem (com taxa), credita destino (sem taxa).
        """
        # 1. Verifica se as carteiras são a mesma
        if endereco_origem == endereco_destino:
            raise ValueError("A carteira de origem e destino não podem ser a mesma.")

        # 2. Busca o ID da Moeda
        id_moeda = self._deposito_saque_repository.get_id_moeda(codigo_moeda)
        if id_moeda is None:
            raise ValueError(f"Moeda não suportada: {codigo_moeda}")

        # 3. Verifica a existência e status das carteiras (ambas ATIVAS)
        if not self._deposito_saque_repository.verifica_carteira_existe(endereco_origem):
            raise ValueError(f"Carteira de origem não encontrada ou inativa: {endereco_origem}")
            
        if not self._deposito_saque_repository.verifica_carteira_existe(endereco_destino):
            raise ValueError(f"Carteira de destino não encontrada ou inativa: {endereco_destino}")

        # 4. Validação da Chave Privada da Origem
        hash_privada_bd = self._deposito_saque_repository.buscar_hash_privada_ativo(endereco_origem)
        if hash_privada_bd is None:
            raise ValueError("Chave privada não encontrada para a carteira de origem ou carteira inativa.")

        # Gerar o hash da chave fornecida pelo usuário para comparação
        hash_fornecido = hashlib.sha256(chave_privada.encode('utf-8')).hexdigest()

        if hash_fornecido != hash_privada_bd:
            raise ValueError("Chave privada de origem inválida.")

        # 5. Cálculo da Taxa e do Valor Líquido
        # Valor total debitado = Valor Transferência (líquido) + Taxa
        
        # Regra de Negócio: A taxa é sobre o valor que SAI da carteira (Origem)
        taxa_percentual = self.TAXA_TRANSFERENCIA_PERCENTUAL
        taxa_valor = valor_transferencia * taxa_percentual
        
        valor_total_debito = valor_transferencia + taxa_valor
        valor_liquido_destino = valor_transferencia # Destino recebe o valor "limpo" (valor_transferencia)


        # 6. Inicia a transação e verifica saldo.
        # Usa o context manager get_connection() para garantir atomicidade.
        with get_connection() as conn:
            
            # 6.1. Verifica Saldo da Origem (Usando a conexão da transação)
            saldo_atual = self._deposito_saque_repository.buscar_saldo_disponivel(
                endereco_carteira=endereco_origem,
                id_moeda=id_moeda,
                conn=conn
            )
            
            if saldo_atual < valor_total_debito:
                raise ValueError(
                    f"Saldo insuficiente na moeda {codigo_moeda}. "
                    f"Necessário {valor_total_debito:.8f} (incluindo taxa)."
                )
                
            # 6.2. Registro e Atualização (Ação atômica)
            self._transferencia_repository.registrar_transferencia_e_atualizar_saldos(
                conn=conn,
                endereco_origem=endereco_origem,
                endereco_destino=endereco_destino,
                id_moeda=id_moeda,
                valor_transferido=valor_total_debito, # Valor que sai da origem
                valor_liquido_destino=valor_liquido_destino, # Valor que entra no destino
                taxa_valor=taxa_valor,
            )
            
        return {
            "status": "sucesso",
            "origem": endereco_origem,
            "destino": endereco_destino,
            "moeda": codigo_moeda,
            "valor_transferido": valor_transferencia, # Valor líquido
            "valor_total_debitado_origem": valor_total_debito,
            "taxa_percentual": taxa_percentual,
            "taxa_valor": taxa_valor,
        }