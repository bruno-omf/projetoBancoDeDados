# api/persistence/repositories/conversao_repository.py

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.engine import Connection

class ConversaoRepository:
    """
    Acesso a dados para operações de Conversão (Registro na CONVERSAO e updates em SALDO_CARTEIRA).
    A conexão/transação é fornecida pelo Service.
    """

    def registrar_conversao_e_atualizar_saldos(
        self,
        conn: Connection,
        endereco_carteira: str,
        id_moeda_origem: int,
        id_moeda_destino: int,
        valor_origem: Decimal,
        valor_destino: Decimal,
        taxa_percentual: Decimal,
        taxa_valor: Decimal,
        cotacao_utilizada: Decimal,
    ) -> None:
        """
        Registra a conversão e atualiza o saldo de origem (débito) e destino (crédito)
        em uma única transação atômica.
        """
        data_hora = datetime.now()
        
        # 1. INSERT na tabela CONVERSAO
        insert_conversao = text("""
            INSERT INTO CONVERSAO (
                endereco_carteira, id_moeda_origem, id_moeda_destino, 
                valor_origem, valor_destino, taxa_percentual, taxa_valor, cotacao_utilizada, data_hora
            ) VALUES (
                :endereco, :id_origem, :id_destino, 
                :valor_origem, :valor_destino, :taxa_percentual, :taxa_valor, :cotacao, :data_hora
            )
        """)
        
        conn.execute(
            insert_conversao,
            {
                "endereco": endereco_carteira,
                "id_origem": id_moeda_origem,
                "id_destino": id_moeda_destino,
                "valor_origem": valor_origem, # Valor total debitado (incluindo taxa)
                "valor_destino": valor_destino, # Valor líquido creditado
                "taxa_percentual": taxa_percentual,
                "taxa_valor": taxa_valor,
                "cotacao": cotacao_utilizada,
                "data_hora": data_hora,
            },
        )

        # 2. UPDATE Saldo de Origem (DÉBITO)
        # O débito é o valor_origem (que inclui a taxa, garantindo que o saldo seja zerado corretamente)
        update_saldo_origem = text("""
            UPDATE SALDO_CARTEIRA
            SET saldo = saldo - :valor_debito, data_atualizacao = :data_hora
            WHERE endereco_carteira = :endereco AND id_moeda = :id_origem
        """)

        conn.execute(
            update_saldo_origem,
            {
                "valor_debito": valor_origem, 
                "data_hora": data_hora,
                "endereco": endereco_carteira,
                "id_origem": id_moeda_origem,
            },
        )

        # 3. UPDATE Saldo de Destino (CRÉDITO)
        # O crédito é o valor_destino (o valor líquido após a conversão)
        update_saldo_destino = text("""
            UPDATE SALDO_CARTEIRA
            SET saldo = saldo + :valor_credito, data_atualizacao = :data_hora
            WHERE endereco_carteira = :endereco AND id_moeda = :id_destino
        """)

        conn.execute(
            update_saldo_destino,
            {
                "valor_credito": valor_destino,
                "data_hora": data_hora,
                "endereco": endereco_carteira,
                "id_destino": id_moeda_destino,
            },
        )