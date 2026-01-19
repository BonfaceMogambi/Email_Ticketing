-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: localhost    Database: sacco_tickets
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `analytics`
--

DROP TABLE IF EXISTS `analytics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `analytics` (
  `id` int NOT NULL AUTO_INCREMENT,
  `metric_name` varchar(255) DEFAULT NULL,
  `metric_value` float DEFAULT NULL,
  `recorded_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `period` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `analytics`
--

LOCK TABLES `analytics` WRITE;
/*!40000 ALTER TABLE `analytics` DISABLE KEYS */;
/*!40000 ALTER TABLE `analytics` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ticket_history`
--

DROP TABLE IF EXISTS `ticket_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int DEFAULT NULL,
  `changed_by` varchar(255) DEFAULT NULL,
  `change_type` varchar(100) DEFAULT NULL,
  `old_value` text,
  `new_value` text,
  `change_notes` text,
  `changed_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_changed_at` (`changed_at`),
  CONSTRAINT `ticket_history_ibfk_1` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ticket_history`
--

LOCK TABLES `ticket_history` WRITE;
/*!40000 ALTER TABLE `ticket_history` DISABLE KEYS */;
/*!40000 ALTER TABLE `ticket_history` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tickets`
--

DROP TABLE IF EXISTS `tickets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tickets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `message_id` varchar(255) DEFAULT NULL,
  `subject` text,
  `sender_email` varchar(255) DEFAULT NULL,
  `sender_name` varchar(255) DEFAULT NULL,
  `body` longtext,
  `assigned_to` varchar(255) DEFAULT NULL,
  `status` varchar(50) DEFAULT 'open',
  `priority` varchar(50) DEFAULT 'medium',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `assigned_at` datetime DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `resolved_by` varchar(255) DEFAULT NULL,
  `resolution_notes` text,
  `admin_notes` text,
  `avg_sentiment` float DEFAULT '0',
  `sentiment_score` float DEFAULT '0',
  `urgency_level` float DEFAULT '0',
  `ai_insights` float DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `message_id` (`message_id`),
  KEY `idx_status` (`status`),
  KEY `idx_assigned_to` (`assigned_to`),
  KEY `idx_priority` (`priority`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tickets`
--

LOCK TABLES `tickets` WRITE;
/*!40000 ALTER TABLE `tickets` DISABLE KEYS */;
INSERT INTO `tickets` VALUES (1,'MSG12345','Login Issue','vee@example.com','Veronah Ayieko','I cannot log into my account.','bmogambi@co-opbank.co.ke','closed','medium','2025-09-24 11:04:25',NULL,'2025-09-24 12:33:23','bmogambi@co-opbank.co.ke','Resolved',NULL,0,0.1,1,0),(3,'MSG23456','Login Issue','vee@example.com','Joan Gakuu','I forgot my email.','bmogambi@co-opbank.co.ke','closed','High','2025-09-24 13:00:03','2025-09-24 14:07:16','2025-09-24 14:19:28','bmogambi@co-opbank.co.ke','Use password below to login','Kindly assist',0,0,0,0),(4,'MSG67890','Password Reset','john@example.com','John Doe','I forgot my password, please reset.','bmogambi@co-opbank.co.ke','closed','high','2025-09-24 15:29:42',NULL,'2025-09-24 15:32:40','bmogambi@co-opbank.co.ke','New Password: kenya',NULL,0,0,0,0),(5,'MSG62050','Password Reset','john@example.com','John Doe','Urgent: I forgot my password, please reset.','bmogambi@co-opbank.co.ke','closed','high','2025-09-24 15:37:56','2025-09-24 15:38:44','2025-09-24 15:39:33','bmogambi@co-opbank.co.ke','Done',NULL,0,0,0,0),(6,'MSG99320','User creation','john@example.com','Joel Dan','Please create user: jdan','bmogambi@co-opbank.co.ke','open','High','2025-09-25 08:16:15',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(7,'MSG96723','New creation','Bonny@fake.com','Bonny Geeks','Please create user: bonny','bmogambi@co-opbank.co.ke','closed','High','2025-09-26 16:58:25',NULL,'2025-09-29 11:16:50','bmogambi@co-opbank.co.ke','Created bonny',NULL,0,0,0,0),(9,'MSG92323','Error 911','Bonny@fake.com','Bonny Geeks','Please restore transactions','llesiit@co-opbank.co.ke','open','High','2025-09-26 17:18:56',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(10,'MSG2001','Error 911','bonny@fake.com','Bonny Geeks','Please restore transactions','bmogambi@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(11,'MSG2002','Login Failure','alice@fake.com','Alice Wanjiku','Unable to login to the system','llesiit@co-opbank.co.ke','open','Medium','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(12,'MSG2003','Transaction Timeout','james@fake.com','James Otieno','Payment request timed out','bnyakundi@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(13,'MSG2004','Email Not Delivered','carol@fake.com','Carol Njeri','Customer emails not going through','bmogambi@co-opbank.co.ke','closed','Low','2025-09-26 17:23:37',NULL,'2025-09-29 11:17:21','bmogambi@co-opbank.co.ke','Resent',NULL,0,0,0,0),(14,'MSG2005','Error 404','david@fake.com','David Kim','Resource not found during request','llesiit@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(15,'MSG2006','Approval Delay','mary@fake.com','Mary Achieng','Approvals taking too long','bnyakundi@co-opbank.co.ke','open','Medium','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(16,'MSG2007','Password Reset','steve@fake.com','Steve Mutua','I forgot my password and need reset','bmogambi@co-opbank.co.ke','open','Low','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(17,'MSG2008','Error 500','pauline@fake.com','Pauline Naliaka','Internal server error occurred','llesiit@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(18,'MSG2009','Slow Performance','eric@fake.com','Eric Mwangi','System is very slow today','bnyakundi@co-opbank.co.ke','open','Medium','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(19,'MSG2010','Card Declined','nancy@fake.com','Nancy Aoko','ATM card declined multiple times','bmogambi@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(20,'MSG2011','Error 121','john@fake.com','John Kariuki','Duplicate transaction error showing','llesiit@co-opbank.co.ke','open','Medium','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(21,'MSG2012','Queue Overflow','mercy@fake.com','Mercy Cherono','Too many requests queued','bnyakundi@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(22,'MSG2013','Balance Mismatch','george@fake.com','George Maina','Customer balance not matching','bmogambi@co-opbank.co.ke','closed','High','2025-09-26 17:23:37',NULL,'2025-09-29 11:17:08','bmogambi@co-opbank.co.ke','Forwarded to BAS',NULL,0,0,0,0),(23,'MSG2014','Fraud Alert','lucy@fake.com','Lucy Nduta','Suspicious transaction flagged','llesiit@co-opbank.co.ke','open','Critical','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(24,'MSG2015','Session Expired','brian@fake.com','Brian Kibet','Session expires too quickly','bnyakundi@co-opbank.co.ke','open','Low','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(25,'MSG2016','Payment Failed','rose@fake.com','Rose Atieno','Mobile money payment failed','bmogambi@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(26,'MSG2017','Network Error','mark@fake.com','Mark Otieno','Network connection lost during transaction','llesiit@co-opbank.co.ke','open','Medium','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(27,'MSG2018','Overdraft Error','agnes@fake.com','Agnes Mwende','Customer overdraft not processed','bnyakundi@co-opbank.co.ke','open','High','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(28,'MSG2019','Invalid PIN','patrick@fake.com','Patrick Koech','PIN rejected at ATM','bmogambi@co-opbank.co.ke','closed','Medium','2025-09-26 17:23:37',NULL,'2025-09-29 11:16:39','bmogambi@co-opbank.co.ke','Reset again. Please login',NULL,0,0,0,0),(29,'MSG2020','System Crash','susan@fake.com','Susan Wairimu','System crashed during batch process','llesiit@co-opbank.co.ke','open','Critical','2025-09-26 17:23:37',NULL,NULL,NULL,NULL,NULL,0,0,0,0),(30,'MSF34623','I dont understand','Bonny@fake.com','Bonny Geeks','Please restore transactions','llesiit@co-opbank.co.ke','open','High','2025-09-29 11:11:10',NULL,NULL,NULL,NULL,NULL,0,0,0,0);
/*!40000 ALTER TABLE `tickets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `role` varchar(100) DEFAULT 'Staff',
  `is_active` tinyint(1) DEFAULT '1',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `last_login` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_email` (`email`),
  KEY `idx_role` (`role`)
) ENGINE=InnoDB AUTO_INCREMENT=1291 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'bmogambi@co-opbank.co.ke','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','B. Mogambi','IT Staff',1,'2025-09-23 17:22:06','2025-09-29 11:12:53'),(2,'llesiit@co-opbank.co.ke','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','L. Lesiit','IT Staff',1,'2025-09-23 17:22:06','2025-09-26 17:13:37'),(3,'bnyakundi@co-opbank.co.ke','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','B. Nyakundi','IT Staff',1,'2025-09-23 17:22:06',NULL),(4,'eotieno@co-opbank.co.ke','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','E. Otieno','Admin',1,'2025-09-23 17:22:06','2025-09-24 14:06:46'),(5,'admin@sacco.co.ke','8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918','System Administrator','Admin',1,'2025-09-23 17:22:06','2025-09-29 11:12:36');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-09-29 12:19:53
