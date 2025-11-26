import os
import secrets
import hashlib
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from api.persistence.repositories.carteira_repository import CarteiraRepository
from api.models.carteira_models import CarteiraCriada, Carteira, Saldo

class CarteiraService:
    """
    Camada de serviço para regras de negócio e segurança da Carteira.
    """
    def __init__(self, repository: CarteiraRepository):
        self._repository = repository
        
        # Lendo configurações do .env (deve ser feito de forma segura e única)
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


    # --- Lógica de Geração de Chaves (Segurança) ---
    
    def _gerar_chaves_e_hash(self) -> Dict[str, str]:
        """
        Gera chave privada, endereço (chave pública simplificada) e o hash.
        """
        # 1. Geração da Chave Privada (e conversão para hex)
        # secrets.token_bytes(N) gera N bytes aleatórios criptograficamente seguros.
        chave_privada_bytes = secrets.token_bytes(self.PRIVATE_KEY_SIZE)
        chave_privada_pura = chave_privada_bytes.hex() # 32 bytes = 64 caracteres hex
        
        # 2. Hashing da Chave Privada
        # O hash será armazenado no banco, NUNCA a chave pura.
        hash_chave_privada = hashlib.sha256(chave_privada_bytes).hexdigest()
        
        # 3. Geração do Endereço da Carteira (Chave Pública Simplificada)
        # Geramos um novo UUID, fazemos um hash dele e pegamos os N primeiros caracteres
        # conforme a especificação de PUBLIC_KEY_SIZE=16.
        # 16 bytes = 32 caracteres hexadecimais
        unique_id = str(uuid.uuid4()).encode('utf-8') 
        endereco_carteira = hashlib.sha256(unique_id).hexdigest()[:self.PUBLIC_KEY_SIZE * 2]
        
        return {
            "endereco_carteira": endereco_carteira, 
            "chave_privada_pura": chave_privada_pura, 
            "hash_chave_privada": hash_chave_privada
        }

    # --- Métodos do Router ---
    
    def criar_carteira(self) -> CarteiraCriada:
        """
        Gera as chaves, persiste a carteira e inicializa os saldos.
        Retorna a carteira criada, incluindo a chave privada.
        """
        
        # 1. Gerar dados de segurança
        chaves = self._gerar_chaves_e_hash()
        endereco = chaves["endereco_carteira"]
        hash_privada = chaves["hash_chave_privada"]
        chave_privada = chaves["chave_privada_pura"] # Guardada apenas para retorno
        
        # 2. Persistir a Carteira e inicializar Saldo (transação no Repository)
        # O método retorna o objeto da carteira (sem a chave privada)
        carteira_data = self._repository.criar_e_inicializar(
            endereco_carteira=endereco, 
            hash_privada=hash_privada
        )
        
        if not carteira_data:
            # Isso só deve acontecer se houver um erro de lógica no repository
             raise Exception("Falha na criação da carteira, repositório retornou vazio.")

        # 3. Montar o objeto de resposta, adicionando a chave privada
        return CarteiraCriada(
            **carteira_data, 
            chave_privada=chave_privada
        )

    # Métodos placeholder para métodos existentes no router (implementados de forma básica)
    
    def listar(self) -> List[Carteira]:
        # O Repositório deve ser ajustado para garantir que não retorna o hash
        data = self._repository.listar()
        return [Carteira(**c) for c in data]

    def buscar_por_endereco(self, endereco_carteira: str) -> Carteira:
        data = self._repository.buscar_por_endereco(endereco_carteira)
        if not data:
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada.")
        return Carteira(**data)

    def bloquear(self, endereco_carteira: str) -> Carteira:
        # A lógica de bloqueio de status deve ser aqui, mas o Repository já faz a parte de UPDATE
        data = self._repository.atualizar_status(endereco_carteira, status="BLOQUEADA")
        if not data:
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada.")
        return Carteira(**data)

    def buscar_saldos(self, endereco_carteira: str) -> List[Saldo]:
        """
        Busca a lista de saldos por moeda para um endereço de carteira.
        """
        # 1. Checagem de existência da Carteira
        # É uma boa prática de negócio checar se a carteira existe antes de buscar os saldos.
        carteira_data = self._repository.buscar_por_endereco(endereco_carteira)
        if not carteira_data:
            # Reusa o erro já definido no service
            raise ValueError(f"Carteira com endereço '{endereco_carteira}' não encontrada.")
            
        # 2. Busca de Saldos
        saldos_data = self._repository.buscar_saldos(endereco_carteira)
        
        # 3. Mapeamento para o modelo Pydantic
        return [Saldo(**s) for s in saldos_data]