-- Populando a tabela MOEDA com os dados iniciais que o professor pede na mini-sprint 2
INSERT IGNORE INTO MOEDA (codigo, nome, tipo) VALUES
    ('BTC', 'Bitcoin', 'CRYPTO'),
    ('ETH', 'Ethereum', 'CRYPTO'),
    ('SOL', 'Solana', 'CRYPTO'),
    ('USD', 'Dolar Americano', 'FIAT'),
    ('BRL', 'Real Brasileiro', 'FIAT');
