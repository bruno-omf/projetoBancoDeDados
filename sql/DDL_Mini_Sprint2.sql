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
    data_atualizacao DATETIME NOT NULL,

    PRIMARY KEY (endereco_carteira, id_moeda), -- chave primaria composta: cada carteira so pode ter um saldo por moeda
    
    FOREIGN KEY (endereco_carteira) REFERENCES CARTEIRA(endereco_carteira)
        ON DELETE CASCADE ON UPDATE CASCADE, -- se a carteira for deletada, o saldo associado também deve ser deletado
    FOREIGN KEY (id_moeda) REFERENCES MOEDA(id_moeda)
        ON DELETE RESTRICT ON UPDATE CASCADE -- nao pode deletar uma moeda se tiver saldo associado
);