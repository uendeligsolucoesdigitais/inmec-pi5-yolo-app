CREATE TABLE `Registros` (
  `idRegistros` int NOT NULL AUTO_INCREMENT,
  `Data` varchar(45) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT NULL,
  `Operacao` varchar(45) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT NULL,
  `Classe` varchar(45) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT NULL,
  `Conformidade` varchar(1) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT NULL,
  `Massa` varchar(1) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT 's',
  `Serial` varchar(45) DEFAULT NULL,
  `Imagem` varchar(100) DEFAULT NULL,
  `Temperatura` double DEFAULT NULL,
  `Umidade` double DEFAULT NULL,
  `Luminosidade` double DEFAULT NULL,
  `Manual` int DEFAULT NULL,
  `Pressao` double DEFAULT NULL,
  `DataUp` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`idRegistros`)
) ENGINE=InnoDB AUTO_INCREMENT=3407 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
