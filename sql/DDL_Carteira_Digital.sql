-- =========================================================
--  Script de criação da base, usuário,
--  Projeto: Carteira Digital
--  Banco:   MySQL 8+
-- =========================================================

-- 1) Criação da base de homologação
CREATE DATABASE IF NOT EXISTS wallet_homolog
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;

-- 2) Criação do usuário restrito para a API
--    (ajuste a senha conforme necessário)
CREATE USER IF NOT EXISTS 'wallet_api_homolog'@'%'
    IDENTIFIED BY 'api123';

-- 3) Grants: apenas DML (sem CREATE/DROP/ALTER)
GRANT SELECT, INSERT, UPDATE, DELETE
    ON wallet_homolog.*
    TO 'wallet_api_homolog'@'%';

FLUSH PRIVILEGES;

-- 4) Usar a base
USE wallet_homolog;

-- =========================================================
--  Tabelas (Aluno deve fazer o modelo)
-- =========================================================

-- MINI-SPRINT 2: Criação das tabelas básicas da carteira digital

-- Tabela CARTEIRA
CREATE TABLE IF NOT EXISTS CARTEIRA (
    endereco_carteira VARCHAR(64) NOT NULL PRIMARY KEY, -- chave publica que vai ser gerada na API
    hash_chave_privada VARCHAR(255) NOT NULL, -- hash da chave privada, nao se deve colocar o texto puro
    data_criacao DATETIME NOT NULL,
    status ENUM('ATIVA', 'BLOQUEADA') NOT NULL DEFAULT 'ATIVA' -- status da carteira
);

-- Tabela MOEDA
CREATE TABLE IF NOT EXISTS MOEDA (
    id_moeda SMALLINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE, -- BTC, USD, BRL, etc
    nome VARCHAR(50) NOT NULL,
    tipo ENUM('CRYPTO', 'FIAT') NOT NULL
);

-- Tabela SALDO_CARTEIRA
CREATE TABLE IF NOT EXISTS SALDO_CARTEIRA (
    endereco_carteira VARCHAR(64) NOT NULL,
    id_moeda SMALLINT NOT NULL,
    saldo DECIMAL(18,8) NOT NULL DEFAULT 0.00000000, -- o saldo da moeda na carteira é criado previamente com "zero". O (18,8) significa que o saldo pode ter até 18 digitos, sendo 8 deles decimais
    data_atualizacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (endereco_carteira, id_moeda), -- chave primaria composta: cada carteira so pode ter um saldo por moeda
    
    FOREIGN KEY (endereco_carteira) REFERENCES CARTEIRA(endereco_carteira)
        ON DELETE CASCADE ON UPDATE CASCADE, -- se a carteira for deletada, o saldo associado também deve ser deletado
    FOREIGN KEY (id_moeda) REFERENCES MOEDA(id_moeda)
        ON DELETE RESTRICT ON UPDATE CASCADE -- nao pode deletar uma moeda se tiver saldo associado
);

-- Populando a tabela MOEDA com os dados iniciais que o professor pede na mini-sprint 2
INSERT IGNORE INTO MOEDA (codigo, nome, tipo) VALUES
    ('BTC', 'Bitcoin', 'CRYPTO'),
    ('ETH', 'Ethereum', 'CRYPTO'),
    ('SOL', 'Solana', 'CRYPTO'),
    ('USD', 'Dolar Americano', 'FIAT'),
    ('BRL', 'Real Brasileiro', 'FIAT');

-- MINI-SPRINT 3: Criação da tabela de movimentações (depósitos e saques)

-- Tabela DEPOSITO_SAQUE
CREATE TABLE IF NOT EXISTS DEPOSITO_SAQUE (
    id_movimento BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    endereco_carteira VARCHAR(64) NOT NULL,
    id_moeda SMALLINT NOT NULL,
    tipo ENUM('DEPOSITO', 'SAQUE') NOT NULL,
    valor DECIMAL(18,8) NOT NULL,
    taxa_valor DECIMAL(18,8) NOT NULL,
    data_horario DATETIME NOT NULL,

    FOREIGN KEY (endereco_carteira) REFERENCES CARTEIRA(endereco_carteira)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_moeda) REFERENCES MOEDA(id_moeda)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE INDEX idx_deposito_saque_carteira ON DEPOSITO_SAQUE(endereco_carteira);

-- MINI-SPRINT 4: Criação da tabela de conversões
CREATE TABLE IF NOT EXISTS CONVERSAO (
    id_conversao BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    endereco_carteira VARCHAR(64) NOT NULL,
    id_moeda_origem SMALLINT NOT NULL,
    id_moeda_destino SMALLINT NOT NULL,
    valor_origem DECIMAL(18,8) NOT NULL,
    valor_destino DECIMAL(18,8) NOT NULL,
    taxa_percentual DECIMAL(5,4) NOT NULL, -- Taxa percentual aplicada (ex: 0.02)
    taxa_valor DECIMAL(18,8) NOT NULL, -- Valor real da taxa
    cotacao_utilizada DECIMAL(18,8) NOT NULL, -- Cotação usada (Moeda Destino / Moeda Origem)
    data_hora DATETIME NOT NULL,
    
    -- Chaves Estrangeiras
    FOREIGN KEY (endereco_carteira) REFERENCES CARTEIRA(endereco_carteira)
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    FOREIGN KEY (id_moeda_origem) REFERENCES MOEDA(id_moeda)
        ON DELETE RESTRICT ON UPDATE CASCADE,
        
    FOREIGN KEY (id_moeda_destino) REFERENCES MOEDA(id_moeda)
        ON DELETE RESTRICT ON UPDATE CASCADE
        
    -- Regra de Negócio Crítica: Não se pode converter de uma moeda para ela mesma.
    -- NÃO FUNCIONA DE JEITO ALGUM!!! JÁ TENTEI DE TUDO.
    -- CONSTRAINT chk_moedas_diferentes CHECK (id_moeda_origem <> id_moeda_destino)
);


-- Mini-Sprint 5: Criação da tabela de trasferências

CREATE TABLE IF NOT EXISTS TRANSFERENCIA (
    id_transferencia BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    endereco_origem VARCHAR(64) NOT NULL,
    endereco_destino VARCHAR(64) NOT NULL,
    id_moeda SMALLINT NOT NULL,
    valor DECIMAL(18,8) NOT NULL,
    taxa_valor DECIMAL(18,8) NOT NULL,
    data_hora DATETIME NOT NULL,

    FOREIGN KEY (endereco_origem) REFERENCES CARTEIRA(endereco_carteira)
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    FOREIGN KEY (endereco_destino) REFERENCES CARTEIRA(endereco_carteira)
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    FOREIGN KEY (id_moeda) REFERENCES MOEDA(id_moeda)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE INDEX idx_transferencia_origem ON TRANSFERENCIA(endereco_origem);
CREATE INDEX idx_transferencia_destino ON TRANSFERENCIA(endereco_destino);