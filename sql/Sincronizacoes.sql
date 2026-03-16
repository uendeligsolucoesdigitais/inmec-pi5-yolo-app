CREATE TABLE `Sincronizacoes` (
  `idSincronizacoes` int NOT NULL AUTO_INCREMENT,
  `Controle` varchar(100) DEFAULT NULL,
  `ModuloId` varchar(45) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT NULL,
  `Serial` varchar(45) CHARACTER SET latin1 COLLATE latin1_swedish_ci DEFAULT NULL,
  `Data` datetime DEFAULT NULL,
  PRIMARY KEY (`idSincronizacoes`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
