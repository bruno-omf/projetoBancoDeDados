import os
import secrets
import hashlib
from typing import Dict, Any, Optional, List

from sqlalchemy import text
from api.persistence.db import get_connection
from datetime import datetime


class CarteiraRepository:
    """
    Acesso a dados da carteira usando SQLAlchemy Core + SQL puro.
    """

    def criar_e_inicializar(self, endereco_carteira: str, hash_privada: str) -> Dict[str, Any]:
        """
        Salva a carteira no banco (apenas hash da privada) e inicializa
        os saldos em zero para todas as moedas, em uma única transação.
        """
        data_criacao = datetime.now()
        
        # O context manager get_connection() gerencia a transação (commit/rollback)
        with get_connection() as conn: 
            
            # 1. INSERIR NA CARTEIRA
            conn.execute(
                text("""
                    INSERT INTO CARTEIRA (endereco_carteira, hash_chave_privada, data_criacao, status)
                    VALUES (:endereco, :hash_privada, :data_criacao, 'ATIVA')
                """),
                {
                    "endereco": endereco_carteira, 
                    "hash_privada": hash_privada,
                    "data_criacao": data_criacao
                },
            )

            # 2. BUSCAR TODOS OS IDs DE MOEDA
            # Este SELECT garante que a inicialização de saldos cubra todas as moedas cadastradas.
            moedas = conn.execute(
                text("SELECT id_moeda FROM MOEDA")
            ).fetchall()
            
            if not moedas:
                # O ideal seria levantar um erro se não houver moedas, mas
                # para o escopo do projeto, assumimos que elas estão lá.
                pass 
            
            # 3. INSERIR SALDO ZERO PARA CADA MOEDA
            saldos_a_inserir = [
                {
                    "endereco": endereco_carteira, 
                    "id_moeda": id_moeda[0], 
                    "data_atualizacao": data_criacao
                } 
                for id_moeda in moedas
            ]
            
            # Execução em lote para inicializar todos os saldos em 0.00
            if saldos_a_inserir:
                conn.execute(
                    text("""
                        INSERT INTO SALDO_CARTEIRA (endereco_carteira, id_moeda, saldo, data_atualizacao)
                        VALUES (:endereco, :id_moeda, 0.00, :data_atualizacao)
                    """),
                    saldos_a_inserir
                )


            # 4. SELECT para retornar a carteira criada
            # Removido 'hash_chave_privada' do SELECT, pois é um campo sensível.
            row = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status
                      FROM CARTEIRA
                     WHERE endereco_carteira = :endereco
                """),
                {"endereco": endereco_carteira},
            ).mappings().first()

        # O retorno aqui é apenas o objeto Carteira (sem a chave privada)
        return dict(row) if row else None
    
    # --- MÉTODOS EXISTENTES ATUALIZADOS ---

    def buscar_por_endereco(self, endereco_carteira: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            # Removido hash_chave_privada do SELECT.
            row = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status
                      FROM CARTEIRA
                     WHERE endereco_carteira = :endereco
                """),
                {"endereco": endereco_carteira},
            ).mappings().first()

        return dict(row) if row else None

    def listar(self) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            # Removido hash_chave_privada do SELECT.
            rows = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status
                      FROM CARTEIRA
                """)
            ).mappings().all()

        return [dict(r) for r in rows]

    def atualizar_status(self, endereco_carteira: str, status: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            conn.execute(
                text("""
                    UPDATE CARTEIRA
                       SET status = :status
                     WHERE endereco_carteira = :endereco
                """),
                {"status": status, "endereco": endereco_carteira},
            )

            # Removido hash_chave_privada do SELECT.
            row = conn.execute(
                text("""
                    SELECT endereco_carteira,
                           data_criacao,
                           status
                      FROM CARTEIRA
                     WHERE endereco_carteira = :endereco
                """),
                {"endereco": endereco_carteira},
            ).mappings().first()

        return dict(row) if row else None

    def buscar_saldos(self, endereco_carteira: str) -> List[Dict[str, Any]]:
        """
        Busca o saldo de todas as moedas para a carteira especificada, 
        incluindo o código e nome da moeda.
        """
        with get_connection() as conn:
            rows = conn.execute(
                text("""
                    SELECT sc.saldo, 
                           sc.data_atualizacao, 
                           m.codigo AS codigo_moeda, 
                           m.nome AS nome_moeda
                      FROM SALDO_CARTEIRA sc
                      JOIN MOEDA m ON sc.id_moeda = m.id_moeda
                     WHERE sc.endereco_carteira = :endereco
                     ORDER BY m.codigo
                """),
                {"endereco": endereco_carteira},
            ).mappings().all()

        return [dict(r) for r in rows]