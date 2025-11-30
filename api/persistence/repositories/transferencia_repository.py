# api/persistence/repositories/transferencia_repository.py

from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Connection

class TransferenciaRepository:
    """
    Acesso a dados para operações de Transferência (Registro na TRANSFERENCIA e updates em SALDO_CARTEIRA).
    A conexão/transação é fornecida pelo Service.
    """

    def registrar_transferencia_e_atualizar_saldos(
        self,
        conn: Connection,
        endereco_origem: str,
        endereco_destino: str,
        id_moeda: int,
        valor_transferido: Decimal,
        valor_liquido_destino: Decimal,
        taxa_valor: Decimal,
    ) -> None:
        """
        Registra a transferência e atualiza o saldo de origem (débito com taxa) e destino (crédito sem taxa)
        em uma única transação atômica.
        """
        data_hora = datetime.now()
        
        # 1. INSERT na tabela TRANSFERENCIA
        insert_transferencia = text("""
            INSERT INTO TRANSFERENCIA (
                endereco_origem, endereco_destino, id_moeda, 
                valor, taxa_valor, data_hora
            ) VALUES (
                :endereco_origem, :endereco_destino, :id_moeda, 
                :valor, :taxa_valor, :data_hora
            )
        """)

        conn.execute(
            insert_transferencia,
            {
                "endereco_origem": endereco_origem,
                "endereco_destino": endereco_destino,
                "id_moeda": id_moeda,
                "valor": valor_transferido, # Valor total (líquido + taxa)
                "taxa_valor": taxa_valor,
                "data_hora": data_hora,
            },
        )

        # 2. UPDATE Saldo de Origem (DÉBITO do valor total = valor + taxa)
        update_saldo_origem = text("""
            UPDATE SALDO_CARTEIRA
            SET saldo = saldo - :valor_total_debito, data_atualizacao = :data_hora
            WHERE endereco_carteira = :endereco_origem AND id_moeda = :id_moeda
        """)

        result_origem = conn.execute(
            update_saldo_origem,
            {
                "valor_total_debito": valor_transferido, # Valor líquido + taxa
                "data_hora": data_hora,
                "endereco_origem": endereco_origem,
                "id_moeda": id_moeda,
            },
        )
        
        if result_origem.rowcount == 0:
            raise ValueError(f"Falha ao debitar saldo de origem. Carteira ou Moeda não inicializada ou saldo insuficiente na origem: {endereco_origem}.")


        # 3. UPDATE Saldo de Destino (CRÉDITO do valor líquido)
        update_saldo_destino = text("""
            UPDATE SALDO_CARTEIRA
            SET saldo = saldo + :valor_credito, data_atualizacao = :data_hora
            WHERE endereco_carteira = :endereco_destino AND id_moeda = :id_moeda
        """)

        result_destino = conn.execute(
            update_saldo_destino,
            {
                "valor_credito": valor_liquido_destino, # Apenas o valor líquido
                "data_hora": data_hora,
                "endereco_destino": endereco_destino,
                "id_moeda": id_moeda,
            },
        )
        
        if result_destino.rowcount == 0:
            # Esta verificação é crucial, pois o destino TAMBÉM precisa ter o saldo inicializado.
            raise ValueError(f"Falha ao creditar saldo de destino. Carteira ou Moeda não inicializada no destino: {endereco_destino}.")