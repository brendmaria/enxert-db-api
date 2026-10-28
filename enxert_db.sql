BEGIN TRANSACTION;
CREATE TABLE Atributos_Resistencia (
    id_atributo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_porta_enxerto INTEGER NOT NULL,
    resistencia_patogenos_solo TEXT,
    resistencia_doencas_parte_aerea TEXT,
    tolerancia_estresse_abiotico TEXT,
    efeito_porte_vigor TEXT,
    FOREIGN KEY(id_porta_enxerto) REFERENCES Plantas(id_planta)
);
INSERT INTO "Atributos_Resistencia" VALUES(1,2,'Resistente a Ralstonia solanacearum e fungos de solo','N/A','Resistente à seca','Vigoroso / Rústico');
INSERT INTO "Atributos_Resistencia" VALUES(2,5,'Resistente a murcha bacteriana e Fusarium','N/A','Alta eficiência hídrica','Equilibrado / Produtivo');
INSERT INTO "Atributos_Resistencia" VALUES(3,7,'Resistente a Phytophthora citrophthora (Gomose)','Memória de defesa (Priming)','Tolerante à seca','Vigoroso');
INSERT INTO "Atributos_Resistencia" VALUES(4,9,'Sensível à gomose em solos úmidos','N/A','Tolerante à seca','Vigoroso');
INSERT INTO "Atributos_Resistencia" VALUES(5,13,'Resistente aos nematoides Meloidogyne incognita e M. javanica','N/A','Adequada ancoragem radicular','Vigoroso');
INSERT INTO "Atributos_Resistencia" VALUES(6,16,'Resistente à fusariose e patógenos de solo','N/A','Resistente ao excesso de umidade e frio','Ananicante a Médio');
CREATE TABLE Biomarcadores (
    id_biomarcador INTEGER PRIMARY KEY AUTOINCREMENT,
    id_planta INTEGER NOT NULL,
    atividade_peroxidase TEXT,
    concentracao_fenois TEXT,
    presenca_prunasina BOOLEAN,
    acoplamento_plasmodesmal TEXT,
    FOREIGN KEY(id_planta) REFERENCES Plantas(id_planta)
);
INSERT INTO "Biomarcadores" VALUES(1,10,'Média / Balanceada','Normal / Estável',0,'Funcional');
INSERT INTO "Biomarcadores" VALUES(2,11,'Elevada','Muito Alta',1,'Deficiente / Não funcional');
INSERT INTO "Biomarcadores" VALUES(3,12,'Elevada','Muito Alta',1,'Deficiente / Não funcional');
INSERT INTO "Biomarcadores" VALUES(4,13,'Parecida com enxerto','Equilibrada',0,'Funcional');
CREATE TABLE Compatibilidade (
    id_compatibilidade INTEGER PRIMARY KEY AUTOINCREMENT,
    id_copa INTEGER NOT NULL,
    id_porta_enxerto INTEGER NOT NULL,
    status_compatibilidade TEXT CHECK(status_compatibilidade IN ('Compatível', 'Incompatibilidade Localizada', 'Incompatibilidade Translocada', 'Incompatível')),
    grau_pegamento_pct REAL,
    observacao_agronomica TEXT,
    FOREIGN KEY(id_copa) REFERENCES Plantas(id_planta),
    FOREIGN KEY(id_porta_enxerto) REFERENCES Plantas(id_planta)
);
INSERT INTO "Compatibilidade" VALUES(1,1,5,'Compatível',100.0,'Excelente pegamento, aumento significativo na massa média dos frutos e produtividade total.');
INSERT INTO "Compatibilidade" VALUES(2,1,4,'Compatível',95.8,'Ótimo equilíbrio vegetativo/produtivo e alta compatibilidade cambial.');
INSERT INTO "Compatibilidade" VALUES(3,1,2,'Compatível',94.1,'Alta taxa de sobrevivência, útil contra Ralstonia solanacearum, porém reduz ligeiramente diâmetro/massa de frutos.');
INSERT INTO "Compatibilidade" VALUES(4,1,3,'Compatível',96.6,'Boa taxa de pegamento, mas inibe enchimento de frutos e reduz produtividade comercial.');
INSERT INTO "Compatibilidade" VALUES(5,6,7,'Compatível',100.0,'Superior desenvolvimento inicial, maior número de folhas e altura da muda.');
INSERT INTO "Compatibilidade" VALUES(6,6,8,'Compatível',95.0,'Bom desenvolvimento vegetativo inicial e vigor equilibrado.');
INSERT INTO "Compatibilidade" VALUES(7,10,13,'Compatível',90.0,'Evolução cambial harmônica, níveis similares de peroxidase entre copa e cavalo.');
INSERT INTO "Compatibilidade" VALUES(8,10,11,'Incompatibilidade Translocada',0.0,'Incompatibilidade severa por translocação de compostos e alta atividade de peroxidase/fenóis.');
INSERT INTO "Compatibilidade" VALUES(9,10,12,'Incompatibilidade Translocada',0.0,'Falha de brotação dos enxertos decorrente do estresse oxidativo e acúmulo fenólico.');
INSERT INTO "Compatibilidade" VALUES(10,15,16,'Compatível',98.0,'Excelente resistência a Fusarium de solo, baixa temperatura e excesso de umidade.');
CREATE TABLE Metodos_Enxertia (
    id_metodo INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_metodo TEXT NOT NULL,
    descricao TEXT,
    tempo_cicatrizacao_dias INTEGER
);
INSERT INTO "Metodos_Enxertia" VALUES(1,'Garfagem de Topo / Fenda-Cheia','União por fenda no porta-enxerto com garfo cortado em cunha no enxerto.',14);
INSERT INTO "Metodos_Enxertia" VALUES(2,'Borbulhia T-Invertido','Inserção de uma gema vegetativa sob a casca cortada em forma de T invertido no porta-enxerto.',12);
INSERT INTO "Metodos_Enxertia" VALUES(3,'Enxertia por Aproximação','União física dos caules mantendo ambas as plantas com raízes até a cicatrização.',15);
INSERT INTO "Metodos_Enxertia" VALUES(4,'Perfuração Apical','Remoção do meristema do porta-enxerto e inserção do hipocótilo perfurado do enxerto.',10);
CREATE TABLE Plantas (
    id_planta INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_comum TEXT NOT NULL,
    nome_cientifico TEXT NOT NULL UNIQUE,
    ncbi_taxid INTEGER,
    familia TEXT NOT NULL,
    genero TEXT NOT NULL,
    papel_agronomico TEXT CHECK(papel_agronomico IN ('Enxerto', 'Porta-Enxerto', 'Ambos'))
);
INSERT INTO "Plantas" VALUES(1,'Tomateiro Janaína','Solanum lycopersicum',3649,'Solanaceae','Solanum','Enxerto');
INSERT INTO "Plantas" VALUES(2,'Jurubeba','Solanum paniculatum',4102,'Solanaceae','Solanum','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(3,'Joá','Solanum aculeatissimum',110275,'Solanaceae','Solanum','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(4,'Porta-Enxerto Castelpro','Solanum lycopersicum x S. habrochaites (Castelpro)',3649,'Solanaceae','Solanum','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(5,'Porta-Enxerto 15PEX00056','Solanum lycopersicum (15PEX00056)',3649,'Solanaceae','Solanum','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(6,'Laranjeira Pera D6','Citrus sinensis (Pera D6)',2711,'Rutaceae','Citrus','Enxerto');
INSERT INTO "Plantas" VALUES(7,'Tangerineira Sunki Tropical','Citrus sunki',555021,'Rutaceae','Citrus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(8,'Citrandarin San Diego','Citrus sunki x Poncirus trifoliata',2711,'Rutaceae','Citrus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(9,'Limoeiro Cravo','Citrus limonia',170929,'Rutaceae','Citrus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(10,'Pessegueiro Santa Rosa / Diamante','Prunus persica',3760,'Rosaceae','Prunus','Ambos');
INSERT INTO "Plantas" VALUES(11,'Ameixeira Marianna','Prunus marianna',3760,'Rosaceae','Prunus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(12,'Ameixeira Mirabolano','Prunus cerasifera',3765,'Rosaceae','Prunus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(13,'Pessegueiro Okinawa','Prunus persica (Okinawa)',3760,'Rosaceae','Prunus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(14,'Pessegueiro Capdeboscq','Prunus persica (Capdeboscq)',3760,'Rosaceae','Prunus','Porta-Enxerto');
INSERT INTO "Plantas" VALUES(15,'Melancia','Citrullus lanatus',3654,'Cucurbitaceae','Citrullus','Enxerto');
INSERT INTO "Plantas" VALUES(16,'Abóbora / Porongo','Cucurbita maxima',3661,'Cucurbitaceae','Cucurbita','Porta-Enxerto');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('Plantas',16);
INSERT INTO "sqlite_sequence" VALUES('Compatibilidade',10);
INSERT INTO "sqlite_sequence" VALUES('Biomarcadores',4);
INSERT INTO "sqlite_sequence" VALUES('Atributos_Resistencia',6);
INSERT INTO "sqlite_sequence" VALUES('Metodos_Enxertia',4);
COMMIT;
