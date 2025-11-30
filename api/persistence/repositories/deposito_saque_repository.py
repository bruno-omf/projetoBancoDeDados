# api/persistence/repositories/deposito_saque_repository.py

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text # <--- CRÍTICO: IMPORT DO TEXT
from sqlalchemy.engine import Connection
from api.persistence.db import get_connection

class DepositoSaqueRepository:
    
    # MÉTODO 1: get_id_moeda (Onde o erro 500 está ocorrendo)
    def get_id_moeda(self, codigo_moeda: str) -> int | None:
        """Busca o id_moeda a partir do código (ex: 'BTC')."""
        # A query deve ser envolvida por text() e usar parâmetros nomeados (:codigo)
        query = text("SELECT id_moeda FROM MOEDA WHERE codigo = :codigo") 
        with get_connection() as conn:
            # O .execute() recebe a query e um dicionário de parâmetros
            result = conn.execute(query, {"codigo": codigo_moeda}).fetchone()
            return result[0] if result else None

    # MÉTODO 2: verifica_carteira_existe
    def verifica_carteira_existe(self, endereco_carteira: str) -> bool:
        """Verifica se a carteira existe antes de processar qualquer movimento."""
        query = text("SELECT 1 FROM CARTEIRA WHERE endereco_carteira = :endereco AND status = 'ATIVA'")
        with get_connection() as conn:
            result = conn.execute(query, {"endereco": endereco_carteira}).fetchone()
            return result is not None

    def buscar_hash_privada_ativo(self, endereco_carteira: str) -> str | None:
        """Busca o hash da chave privada de uma carteira ATIVA."""
        query = text("""
            SELECT hash_chave_privada
            FROM CARTEIRA
            WHERE endereco_carteira = :endereco AND status = 'ATIVA'
        """)
        with get_connection() as conn:
            result = conn.execute(query, {"endereco": endereco_carteira}).fetchone()
            return result[0] if result else None

    # MÉTODO 3: registrar_movimento_e_atualizar_saldo
    def registrar_movimento_e_atualizar_saldo(
        self,
        conn: Connection,
        endereco_carteira: str,
        id_moeda: int,
        valor: Decimal,
        taxa_valor: Decimal,
        tipo: str,
        valor_operacional: Decimal,
    ) -> None:
        """Registra o movimento (Depósito/Saque) e atualiza o saldo na mesma transação."""
        data_hora = datetime.now()

        # 1. INSERT na tabela DEPOSITO_SAQUE
        # data_horario é o nome correto da coluna (visto no seu DDL)
        insert_movimento = text("""
            INSERT INTO DEPOSITO_SAQUE 
            (endereco_carteira, id_moeda, tipo, valor, taxa_valor, data_horario) 
            VALUES (:endereco, :id_moeda, :tipo, :valor, :taxa_valor, :data_hora)
        """)
        conn.execute(
            insert_movimento,
            {
                "endereco": endereco_carteira,
                "id_moeda": id_moeda,
                "tipo": tipo,
                "valor": valor,
                "taxa_valor": taxa_valor,
                "data_hora": data_hora,
            },
        )

        # 2. UPDATE na tabela SALDO_CARTEIRA 
        update_saldo = text("""
            UPDATE SALDO_CARTEIRA
            SET saldo = saldo + :valor_operacional, data_atualizacao = :data_hora
            WHERE endereco_carteira = :endereco AND id_moeda = :id_moeda
        """)

        result = conn.execute(
            update_saldo,
            {
                "valor_operacional": valor_operacional,
                "data_hora": data_hora,
                "endereco": endereco_carteira,
                "id_moeda": id_moeda,
            },
        )

        if result.rowcount == 0:
            raise ValueError("Falha ao atualizar saldo. Carteira ou Moeda não inicializada.")

    def buscar_saldo_disponivel(self, endereco_carteira: str, id_moeda: int, conn: Connection) -> Decimal:
        """Busca o saldo atual de uma moeda na carteira."""
        query = text("""
            SELECT saldo
            FROM SALDO_CARTEIRA
            WHERE endereco_carteira = :endereco AND id_moeda = :id_moeda
        """)
        result = conn.execute(query, {"endereco": endereco_carteira, "id_moeda": id_moeda}).fetchone()

        return Decimal(result[0]) if result else Decimal("0.00000000")