/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.14-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: chuosmart_db
-- ------------------------------------------------------
-- Server version	10.11.14-MariaDB-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `affiliates_affiliate`
--

DROP TABLE IF EXISTS `affiliates_affiliate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `affiliates_affiliate` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `affiliate_code` varchar(20) NOT NULL,
  `balance` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `phone_number` varchar(15) DEFAULT NULL,
  `payment_method` varchar(50) DEFAULT NULL,
  `payment_details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payment_details`)),
  `total_earnings` decimal(10,2) NOT NULL,
  `total_paid` decimal(10,2) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `affiliate_code` (`affiliate_code`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `affiliates_affiliate_user_id_5bd44b3e_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `affiliates_affiliate`
--

LOCK TABLES `affiliates_affiliate` WRITE;
/*!40000 ALTER TABLE `affiliates_affiliate` DISABLE KEYS */;
/*!40000 ALTER TABLE `affiliates_affiliate` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `affiliates_clicktracking`
--

DROP TABLE IF EXISTS `affiliates_clicktracking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `affiliates_clicktracking` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `referral_link` varchar(255) NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  `converted` tinyint(1) NOT NULL,
  `affiliate_id` bigint(20) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `affiliates_clicktrac_affiliate_id_eea54a80_fk_affiliate` (`affiliate_id`),
  KEY `affiliates_clicktracking_user_id_b44fc0ee_fk_auth_user_id` (`user_id`),
  CONSTRAINT `affiliates_clicktrac_affiliate_id_eea54a80_fk_affiliate` FOREIGN KEY (`affiliate_id`) REFERENCES `affiliates_affiliate` (`id`),
  CONSTRAINT `affiliates_clicktracking_user_id_b44fc0ee_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `affiliates_clicktracking`
--

LOCK TABLES `affiliates_clicktracking` WRITE;
/*!40000 ALTER TABLE `affiliates_clicktracking` DISABLE KEYS */;
/*!40000 ALTER TABLE `affiliates_clicktracking` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `affiliates_payoutrequest`
--

DROP TABLE IF EXISTS `affiliates_payoutrequest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `affiliates_payoutrequest` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `amount` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `requested_at` datetime(6) NOT NULL,
  `processed_at` datetime(6) DEFAULT NULL,
  `payment_method` varchar(50) NOT NULL,
  `payment_details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payment_details`)),
  `notes` longtext DEFAULT NULL,
  `affiliate_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `affiliates_payoutreq_affiliate_id_7ed03611_fk_affiliate` (`affiliate_id`),
  CONSTRAINT `affiliates_payoutreq_affiliate_id_7ed03611_fk_affiliate` FOREIGN KEY (`affiliate_id`) REFERENCES `affiliates_affiliate` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `affiliates_payoutrequest`
--

LOCK TABLES `affiliates_payoutrequest` WRITE;
/*!40000 ALTER TABLE `affiliates_payoutrequest` DISABLE KEYS */;
/*!40000 ALTER TABLE `affiliates_payoutrequest` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `affiliates_referral`
--

DROP TABLE IF EXISTS `affiliates_referral`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `affiliates_referral` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `object_id` int(10) unsigned DEFAULT NULL CHECK (`object_id` >= 0),
  `referral_type` varchar(20) NOT NULL,
  `referral_id` char(32) NOT NULL,
  `commission_earned` decimal(10,2) NOT NULL,
  `is_paid` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `converted_at` datetime(6) DEFAULT NULL,
  `purchase_amount` decimal(10,2) NOT NULL,
  `affiliate_id` bigint(20) NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `referred_user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `referral_id` (`referral_id`),
  KEY `affiliates_referral_affiliate_id_8a56ad1b_fk_affiliate` (`affiliate_id`),
  KEY `affiliates_referral_content_type_id_a5f4b0f4_fk_django_co` (`content_type_id`),
  KEY `affiliates_referral_referred_user_id_ef4ce5bf_fk_auth_user_id` (`referred_user_id`),
  CONSTRAINT `affiliates_referral_affiliate_id_8a56ad1b_fk_affiliate` FOREIGN KEY (`affiliate_id`) REFERENCES `affiliates_affiliate` (`id`),
  CONSTRAINT `affiliates_referral_content_type_id_a5f4b0f4_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `affiliates_referral_referred_user_id_ef4ce5bf_fk_auth_user_id` FOREIGN KEY (`referred_user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `affiliates_referral`
--

LOCK TABLES `affiliates_referral` WRITE;
/*!40000 ALTER TABLE `affiliates_referral` DISABLE KEYS */;
/*!40000 ALTER TABLE `affiliates_referral` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=301 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES
(1,'Can add log entry',1,'add_logentry'),
(2,'Can change log entry',1,'change_logentry'),
(3,'Can delete log entry',1,'delete_logentry'),
(4,'Can view log entry',1,'view_logentry'),
(5,'Can add permission',2,'add_permission'),
(6,'Can change permission',2,'change_permission'),
(7,'Can delete permission',2,'delete_permission'),
(8,'Can view permission',2,'view_permission'),
(9,'Can add group',3,'add_group'),
(10,'Can change group',3,'change_group'),
(11,'Can delete group',3,'delete_group'),
(12,'Can view group',3,'view_group'),
(13,'Can add user',4,'add_user'),
(14,'Can change user',4,'change_user'),
(15,'Can delete user',4,'delete_user'),
(16,'Can view user',4,'view_user'),
(17,'Can add content type',5,'add_contenttype'),
(18,'Can change content type',5,'change_contenttype'),
(19,'Can delete content type',5,'delete_contenttype'),
(20,'Can view content type',5,'view_contenttype'),
(21,'Can add session',6,'add_session'),
(22,'Can change session',6,'change_session'),
(23,'Can delete session',6,'delete_session'),
(24,'Can view session',6,'view_session'),
(25,'Can add site',7,'add_site'),
(26,'Can change site',7,'change_site'),
(27,'Can delete site',7,'delete_site'),
(28,'Can view site',7,'view_site'),
(29,'Can add group',8,'add_group'),
(30,'Can change group',8,'change_group'),
(31,'Can delete group',8,'delete_group'),
(32,'Can view group',8,'view_group'),
(33,'Can add push information',9,'add_pushinformation'),
(34,'Can change push information',9,'change_pushinformation'),
(35,'Can delete push information',9,'delete_pushinformation'),
(36,'Can view push information',9,'view_pushinformation'),
(37,'Can add subscription info',10,'add_subscriptioninfo'),
(38,'Can change subscription info',10,'change_subscriptioninfo'),
(39,'Can delete subscription info',10,'delete_subscriptioninfo'),
(40,'Can view subscription info',10,'view_subscriptioninfo'),
(41,'Can add banners',11,'add_banners'),
(42,'Can change banners',11,'change_banners'),
(43,'Can delete banners',11,'delete_banners'),
(44,'Can view banners',11,'view_banners'),
(45,'Can add customer',12,'add_customer'),
(46,'Can change customer',12,'change_customer'),
(47,'Can delete customer',12,'delete_customer'),
(48,'Can view customer',12,'view_customer'),
(49,'Can add product',13,'add_product'),
(50,'Can change product',13,'change_product'),
(51,'Can delete product',13,'delete_product'),
(52,'Can view product',13,'view_product'),
(53,'Can add order placed',14,'add_orderplaced'),
(54,'Can change order placed',14,'change_orderplaced'),
(55,'Can delete order placed',14,'delete_orderplaced'),
(56,'Can view order placed',14,'view_orderplaced'),
(57,'Can add cart',15,'add_cart'),
(58,'Can change cart',15,'change_cart'),
(59,'Can delete cart',15,'delete_cart'),
(60,'Can view cart',15,'view_cart'),
(61,'Can add blog',16,'add_blog'),
(62,'Can change blog',16,'change_blog'),
(63,'Can delete blog',16,'delete_blog'),
(64,'Can view blog',16,'view_blog'),
(65,'Can add subscription',17,'add_subscription'),
(66,'Can change subscription',17,'change_subscription'),
(67,'Can delete subscription',17,'delete_subscription'),
(68,'Can view subscription',17,'view_subscription'),
(69,'Can add subscription payment',18,'add_subscriptionpayment'),
(70,'Can change subscription payment',18,'change_subscriptionpayment'),
(71,'Can delete subscription payment',18,'delete_subscriptionpayment'),
(72,'Can view subscription payment',18,'view_subscriptionpayment'),
(73,'Can add newsletter subscriber',19,'add_newslettersubscriber'),
(74,'Can change newsletter subscriber',19,'change_newslettersubscriber'),
(75,'Can delete newsletter subscriber',19,'delete_newslettersubscriber'),
(76,'Can view newsletter subscriber',19,'view_newslettersubscriber'),
(77,'Can add account deletion request',20,'add_accountdeletionrequest'),
(78,'Can change account deletion request',20,'change_accountdeletionrequest'),
(79,'Can delete account deletion request',20,'delete_accountdeletionrequest'),
(80,'Can view account deletion request',20,'view_accountdeletionrequest'),
(81,'Can add user newsletter preference',21,'add_usernewsletterpreference'),
(82,'Can change user newsletter preference',21,'change_usernewsletterpreference'),
(83,'Can delete user newsletter preference',21,'delete_usernewsletterpreference'),
(84,'Can view user newsletter preference',21,'view_usernewsletterpreference'),
(85,'Can add Sent Email',22,'add_sentemail'),
(86,'Can change Sent Email',22,'change_sentemail'),
(87,'Can delete Sent Email',22,'delete_sentemail'),
(88,'Can view Sent Email',22,'view_sentemail'),
(89,'Can add Newsletter Test Send',23,'add_newslettertestsend'),
(90,'Can change Newsletter Test Send',23,'change_newslettertestsend'),
(91,'Can delete Newsletter Test Send',23,'delete_newslettertestsend'),
(92,'Can view Newsletter Test Send',23,'view_newslettertestsend'),
(93,'Can add Newsletter Send Log',24,'add_newslettersendlog'),
(94,'Can change Newsletter Send Log',24,'change_newslettersendlog'),
(95,'Can delete Newsletter Send Log',24,'delete_newslettersendlog'),
(96,'Can view Newsletter Send Log',24,'view_newslettersendlog'),
(97,'Can add talent',25,'add_talent'),
(98,'Can change talent',25,'change_talent'),
(99,'Can delete talent',25,'delete_talent'),
(100,'Can view talent',25,'view_talent'),
(101,'Can add comment',26,'add_comment'),
(102,'Can change comment',26,'change_comment'),
(103,'Can delete comment',26,'delete_comment'),
(104,'Can view comment',26,'view_comment'),
(105,'Can add like',27,'add_like'),
(106,'Can change like',27,'change_like'),
(107,'Can delete like',27,'delete_like'),
(108,'Can view like',27,'view_like'),
(109,'Can add chat message',28,'add_chatmessage'),
(110,'Can change chat message',28,'change_chatmessage'),
(111,'Can delete chat message',28,'delete_chatmessage'),
(112,'Can view chat message',28,'view_chatmessage'),
(113,'Can add unauthenticated chat message',29,'add_unauthenticatedchatmessage'),
(114,'Can change unauthenticated chat message',29,'change_unauthenticatedchatmessage'),
(115,'Can delete unauthenticated chat message',29,'delete_unauthenticatedchatmessage'),
(116,'Can view unauthenticated chat message',29,'view_unauthenticatedchatmessage'),
(117,'Can add activity log',30,'add_activitylog'),
(118,'Can change activity log',30,'change_activitylog'),
(119,'Can delete activity log',30,'delete_activitylog'),
(120,'Can view activity log',30,'view_activitylog'),
(121,'Can add choice',31,'add_choice'),
(122,'Can change choice',31,'change_choice'),
(123,'Can delete choice',31,'delete_choice'),
(124,'Can view choice',31,'view_choice'),
(125,'Can add course',32,'add_course'),
(126,'Can change course',32,'change_course'),
(127,'Can delete course',32,'delete_course'),
(128,'Can view course',32,'view_course'),
(129,'Can add course module',33,'add_coursemodule'),
(130,'Can change course module',33,'change_coursemodule'),
(131,'Can delete course module',33,'delete_coursemodule'),
(132,'Can view course module',33,'view_coursemodule'),
(133,'Can add lms profile',34,'add_lmsprofile'),
(134,'Can change lms profile',34,'change_lmsprofile'),
(135,'Can delete lms profile',34,'delete_lmsprofile'),
(136,'Can view lms profile',34,'view_lmsprofile'),
(137,'Can add program',35,'add_program'),
(138,'Can change program',35,'change_program'),
(139,'Can delete program',35,'delete_program'),
(140,'Can view program',35,'view_program'),
(141,'Can add question',36,'add_question'),
(142,'Can change question',36,'change_question'),
(143,'Can delete question',36,'delete_question'),
(144,'Can view question',36,'view_question'),
(145,'Can add Quiz',37,'add_quiz'),
(146,'Can change Quiz',37,'change_quiz'),
(147,'Can delete Quiz',37,'delete_quiz'),
(148,'Can view Quiz',37,'view_quiz'),
(149,'Can add quiz taker',38,'add_quiztaker'),
(150,'Can change quiz taker',38,'change_quiztaker'),
(151,'Can delete quiz taker',38,'delete_quiztaker'),
(152,'Can view quiz taker',38,'view_quiztaker'),
(153,'Can add essay_ question',39,'add_essay_question'),
(154,'Can change essay_ question',39,'change_essay_question'),
(155,'Can delete essay_ question',39,'delete_essay_question'),
(156,'Can view essay_ question',39,'view_essay_question'),
(157,'Can add mc question',40,'add_mcquestion'),
(158,'Can change mc question',40,'change_mcquestion'),
(159,'Can delete mc question',40,'delete_mcquestion'),
(160,'Can view mc question',40,'view_mcquestion'),
(161,'Can add t f_ question',41,'add_tf_question'),
(162,'Can change t f_ question',41,'change_tf_question'),
(163,'Can delete t f_ question',41,'delete_tf_question'),
(164,'Can view t f_ question',41,'view_tf_question'),
(165,'Can add semester',42,'add_semester'),
(166,'Can change semester',42,'change_semester'),
(167,'Can delete semester',42,'delete_semester'),
(168,'Can view semester',42,'view_semester'),
(169,'Can add course enrollment',43,'add_courseenrollment'),
(170,'Can change course enrollment',43,'change_courseenrollment'),
(171,'Can delete course enrollment',43,'delete_courseenrollment'),
(172,'Can view course enrollment',43,'view_courseenrollment'),
(173,'Can add course content',44,'add_coursecontent'),
(174,'Can change course content',44,'change_coursecontent'),
(175,'Can delete course content',44,'delete_coursecontent'),
(176,'Can view course content',44,'view_coursecontent'),
(177,'Can add student answer',45,'add_studentanswer'),
(178,'Can change student answer',45,'change_studentanswer'),
(179,'Can delete student answer',45,'delete_studentanswer'),
(180,'Can view student answer',45,'view_studentanswer'),
(181,'Can add grade',46,'add_grade'),
(182,'Can change grade',46,'change_grade'),
(183,'Can delete grade',46,'delete_grade'),
(184,'Can view grade',46,'view_grade'),
(185,'Can add instructor request',47,'add_instructorrequest'),
(186,'Can change instructor request',47,'change_instructorrequest'),
(187,'Can delete instructor request',47,'delete_instructorrequest'),
(188,'Can view instructor request',47,'view_instructorrequest'),
(189,'Can add content access',48,'add_contentaccess'),
(190,'Can change content access',48,'change_contentaccess'),
(191,'Can delete content access',48,'delete_contentaccess'),
(192,'Can view content access',48,'view_contentaccess'),
(193,'Can add Site Settings',49,'add_sitesettings'),
(194,'Can change Site Settings',49,'change_sitesettings'),
(195,'Can delete Site Settings',49,'delete_sitesettings'),
(196,'Can view Site Settings',49,'view_sitesettings'),
(197,'Can add Ad Exempt User',50,'add_adexemptuser'),
(198,'Can change Ad Exempt User',50,'change_adexemptuser'),
(199,'Can delete Ad Exempt User',50,'delete_adexemptuser'),
(200,'Can view Ad Exempt User',50,'view_adexemptuser'),
(201,'Can add payment method',51,'add_paymentmethod'),
(202,'Can change payment method',51,'change_paymentmethod'),
(203,'Can delete payment method',51,'delete_paymentmethod'),
(204,'Can view payment method',51,'view_paymentmethod'),
(205,'Can add certificate template',52,'add_certificatetemplate'),
(206,'Can change certificate template',52,'change_certificatetemplate'),
(207,'Can delete certificate template',52,'delete_certificatetemplate'),
(208,'Can view certificate template',52,'view_certificatetemplate'),
(209,'Can add student certificate',53,'add_studentcertificate'),
(210,'Can change student certificate',53,'change_studentcertificate'),
(211,'Can delete student certificate',53,'delete_studentcertificate'),
(212,'Can view student certificate',53,'view_studentcertificate'),
(213,'Can add module progress',54,'add_moduleprogress'),
(214,'Can change module progress',54,'change_moduleprogress'),
(215,'Can delete module progress',54,'delete_moduleprogress'),
(216,'Can view module progress',54,'view_moduleprogress'),
(217,'Can add Quiz Generation Job',55,'add_quizgenerationjob'),
(218,'Can change Quiz Generation Job',55,'change_quizgenerationjob'),
(219,'Can delete Quiz Generation Job',55,'delete_quizgenerationjob'),
(220,'Can view Quiz Generation Job',55,'view_quizgenerationjob'),
(221,'Can add Certificate Payment',56,'add_certificatepayment'),
(222,'Can change Certificate Payment',56,'change_certificatepayment'),
(223,'Can delete Certificate Payment',56,'delete_certificatepayment'),
(224,'Can view Certificate Payment',56,'view_certificatepayment'),
(225,'Can add Course Payment',57,'add_coursepayment'),
(226,'Can change Course Payment',57,'change_coursepayment'),
(227,'Can delete Course Payment',57,'delete_coursepayment'),
(228,'Can view Course Payment',57,'view_coursepayment'),
(229,'Can add Course Payment Group',58,'add_coursepaymentgroup'),
(230,'Can change Course Payment Group',58,'change_coursepaymentgroup'),
(231,'Can delete Course Payment Group',58,'delete_coursepaymentgroup'),
(232,'Can view Course Payment Group',58,'view_coursepaymentgroup'),
(233,'Can add Module Payment',59,'add_modulepayment'),
(234,'Can change Module Payment',59,'change_modulepayment'),
(235,'Can delete Module Payment',59,'delete_modulepayment'),
(236,'Can view Module Payment',59,'view_modulepayment'),
(237,'Can add email signup',60,'add_emailsignup'),
(238,'Can change email signup',60,'change_emailsignup'),
(239,'Can delete email signup',60,'delete_emailsignup'),
(240,'Can view email signup',60,'view_emailsignup'),
(241,'Can add affiliate',61,'add_affiliate'),
(242,'Can change affiliate',61,'change_affiliate'),
(243,'Can delete affiliate',61,'delete_affiliate'),
(244,'Can view affiliate',61,'view_affiliate'),
(245,'Can add referral',62,'add_referral'),
(246,'Can change referral',62,'change_referral'),
(247,'Can delete referral',62,'delete_referral'),
(248,'Can view referral',62,'view_referral'),
(249,'Can add payout request',63,'add_payoutrequest'),
(250,'Can change payout request',63,'change_payoutrequest'),
(251,'Can delete payout request',63,'delete_payoutrequest'),
(252,'Can view payout request',63,'view_payoutrequest'),
(253,'Can add click tracking',64,'add_clicktracking'),
(254,'Can change click tracking',64,'change_clicktracking'),
(255,'Can delete click tracking',64,'delete_clicktracking'),
(256,'Can view click tracking',64,'view_clicktracking'),
(257,'Can add API Configuration',65,'add_apiconfiguration'),
(258,'Can change API Configuration',65,'change_apiconfiguration'),
(259,'Can delete API Configuration',65,'delete_apiconfiguration'),
(260,'Can view API Configuration',65,'view_apiconfiguration'),
(261,'Can add Company',66,'add_company'),
(262,'Can change Company',66,'change_company'),
(263,'Can delete Company',66,'delete_company'),
(264,'Can view Company',66,'view_company'),
(265,'Can add Industry',67,'add_industry'),
(266,'Can change Industry',67,'change_industry'),
(267,'Can delete Industry',67,'delete_industry'),
(268,'Can view Industry',67,'view_industry'),
(269,'Can add Job',68,'add_job'),
(270,'Can change Job',68,'change_job'),
(271,'Can delete Job',68,'delete_job'),
(272,'Can view Job',68,'view_job'),
(273,'Can add Skill',69,'add_skill'),
(274,'Can change Skill',69,'change_skill'),
(275,'Can delete Skill',69,'delete_skill'),
(276,'Can view Skill',69,'view_skill'),
(277,'Can add Saved Job',70,'add_savedjob'),
(278,'Can change Saved Job',70,'change_savedjob'),
(279,'Can delete Saved Job',70,'delete_savedjob'),
(280,'Can view Saved Job',70,'view_savedjob'),
(281,'Can add Job Search Preference',71,'add_jobsearchpreference'),
(282,'Can change Job Search Preference',71,'change_jobsearchpreference'),
(283,'Can delete Job Search Preference',71,'delete_jobsearchpreference'),
(284,'Can view Job Search Preference',71,'view_jobsearchpreference'),
(285,'Can add Job Application',72,'add_jobapplication'),
(286,'Can change Job Application',72,'change_jobapplication'),
(287,'Can delete Job Application',72,'delete_jobapplication'),
(288,'Can view Job Application',72,'view_jobapplication'),
(289,'Can add API Request Log',73,'add_apirequestlog'),
(290,'Can change API Request Log',73,'change_apirequestlog'),
(291,'Can delete API Request Log',73,'delete_apirequestlog'),
(292,'Can view API Request Log',73,'view_apirequestlog'),
(293,'Can add User Job Approval',74,'add_userjobapproval'),
(294,'Can change User Job Approval',74,'change_userjobapproval'),
(295,'Can delete User Job Approval',74,'delete_userjobapproval'),
(296,'Can view User Job Approval',74,'view_userjobapproval'),
(297,'Can add Job Course Recommendation',75,'add_jobcourserecommendation'),
(298,'Can change Job Course Recommendation',75,'change_jobcourserecommendation'),
(299,'Can delete Job Course Recommendation',75,'delete_jobcourserecommendation'),
(300,'Can view Job Course Recommendation',75,'view_jobcourserecommendation');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user`
--

LOCK TABLES `auth_user` WRITE;
/*!40000 ALTER TABLE `auth_user` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_groups`
--

LOCK TABLES `auth_user_groups` WRITE;
/*!40000 ALTER TABLE `auth_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_user_user_permissions`
--

LOCK TABLES `auth_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `auth_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `chatbotapp_chatmessage`
--

DROP TABLE IF EXISTS `chatbotapp_chatmessage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `chatbotapp_chatmessage` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_message` longtext NOT NULL,
  `bot_response` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `chatbotapp_chatmessage_user_id_5c42049c_fk_auth_user_id` (`user_id`),
  CONSTRAINT `chatbotapp_chatmessage_user_id_5c42049c_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `chatbotapp_chatmessage`
--

LOCK TABLES `chatbotapp_chatmessage` WRITE;
/*!40000 ALTER TABLE `chatbotapp_chatmessage` DISABLE KEYS */;
/*!40000 ALTER TABLE `chatbotapp_chatmessage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `chatbotapp_unauthenticatedchatmessage`
--

DROP TABLE IF EXISTS `chatbotapp_unauthenticatedchatmessage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `chatbotapp_unauthenticatedchatmessage` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_message` longtext NOT NULL,
  `bot_response` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `session_key` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `chatbotapp_unauthenticatedchatmessage`
--

LOCK TABLES `chatbotapp_unauthenticatedchatmessage` WRITE;
/*!40000 ALTER TABLE `chatbotapp_unauthenticatedchatmessage` DISABLE KEYS */;
/*!40000 ALTER TABLE `chatbotapp_unauthenticatedchatmessage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_accountdeletionrequest`
--

DROP TABLE IF EXISTS `core_accountdeletionrequest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_accountdeletionrequest` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `full_name` varchar(200) NOT NULL,
  `email` varchar(254) NOT NULL,
  `phone_number` varchar(20) NOT NULL,
  `product` varchar(20) NOT NULL,
  `reason` longtext NOT NULL,
  `consent_confirmed` tinyint(1) NOT NULL,
  `status` varchar(20) NOT NULL,
  `admin_notes` longtext NOT NULL,
  `requested_at` datetime(6) NOT NULL,
  `reviewed_at` datetime(6) DEFAULT NULL,
  `reviewed_by_id` int(11) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `core_accountdeletion_reviewed_by_id_e87dfa37_fk_auth_user` (`reviewed_by_id`),
  KEY `core_accountdeletionrequest_user_id_5f53db2a_fk_auth_user_id` (`user_id`),
  CONSTRAINT `core_accountdeletion_reviewed_by_id_e87dfa37_fk_auth_user` FOREIGN KEY (`reviewed_by_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `core_accountdeletionrequest_user_id_5f53db2a_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_accountdeletionrequest`
--

LOCK TABLES `core_accountdeletionrequest` WRITE;
/*!40000 ALTER TABLE `core_accountdeletionrequest` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_accountdeletionrequest` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_banners`
--

DROP TABLE IF EXISTS `core_banners`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_banners` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) DEFAULT NULL,
  `image` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_banners`
--

LOCK TABLES `core_banners` WRITE;
/*!40000 ALTER TABLE `core_banners` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_banners` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_blog`
--

DROP TABLE IF EXISTS `core_blog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_blog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `content` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `author_id` int(11) NOT NULL,
  `thumbnail` varchar(100) DEFAULT NULL,
  `is_markdown` tinyint(1) NOT NULL,
  `thumbnail_webp` varchar(100) DEFAULT NULL,
  `slug` varchar(250) DEFAULT NULL,
  `category` varchar(100) DEFAULT NULL,
  `thumbnail_cloudinary` varchar(500) DEFAULT NULL,
  `upload_method` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `core_blog_author_id_1575e3e5_fk_auth_user_id` (`author_id`),
  CONSTRAINT `core_blog_author_id_1575e3e5_fk_auth_user_id` FOREIGN KEY (`author_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_blog`
--

LOCK TABLES `core_blog` WRITE;
/*!40000 ALTER TABLE `core_blog` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_blog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_cart`
--

DROP TABLE IF EXISTS `core_cart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_cart` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `quantity` int(10) unsigned NOT NULL CHECK (`quantity` >= 0),
  `user_id` int(11) NOT NULL,
  `product_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `core_cart_user_id_2ebeb843_fk_auth_user_id` (`user_id`),
  KEY `core_cart_product_id_8a783d81_fk_core_product_id` (`product_id`),
  CONSTRAINT `core_cart_product_id_8a783d81_fk_core_product_id` FOREIGN KEY (`product_id`) REFERENCES `core_product` (`id`),
  CONSTRAINT `core_cart_user_id_2ebeb843_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_cart`
--

LOCK TABLES `core_cart` WRITE;
/*!40000 ALTER TABLE `core_cart` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_cart` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_customer`
--

DROP TABLE IF EXISTS `core_customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_customer` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `university` varchar(200) DEFAULT NULL,
  `college` varchar(200) DEFAULT NULL,
  `block_number` varchar(200) DEFAULT NULL,
  `room_number` varchar(200) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `subscription_id` bigint(20) DEFAULT NULL,
  `phone_number` varchar(15) DEFAULT NULL,
  `is_university_student` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `core_customer_subscription_id_917b8c06_fk_core_subscription_id` (`subscription_id`),
  CONSTRAINT `core_customer_subscription_id_917b8c06_fk_core_subscription_id` FOREIGN KEY (`subscription_id`) REFERENCES `core_subscription` (`id`),
  CONSTRAINT `core_customer_user_id_76763a70_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_customer`
--

LOCK TABLES `core_customer` WRITE;
/*!40000 ALTER TABLE `core_customer` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_customer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_newslettersendlog`
--

DROP TABLE IF EXISTS `core_newslettersendlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_newslettersendlog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `subscriber_email` varchar(254) NOT NULL,
  `sent_date` date NOT NULL,
  `categories` varchar(255) NOT NULL,
  `sent_at` datetime(6) NOT NULL,
  `status` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `core_newslettersendlog_subscriber_email_sent_date_05713bf9_uniq` (`subscriber_email`,`sent_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_newslettersendlog`
--

LOCK TABLES `core_newslettersendlog` WRITE;
/*!40000 ALTER TABLE `core_newslettersendlog` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_newslettersendlog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_newslettersubscriber`
--

DROP TABLE IF EXISTS `core_newslettersubscriber`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_newslettersubscriber` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `source` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_subscribed` datetime(6) NOT NULL,
  `last_updated` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_newslettersubscriber`
--

LOCK TABLES `core_newslettersubscriber` WRITE;
/*!40000 ALTER TABLE `core_newslettersubscriber` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_newslettersubscriber` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_newslettertestsend`
--

DROP TABLE IF EXISTS `core_newslettertestsend`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_newslettertestsend` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `recipient_email` varchar(254) NOT NULL,
  `categories` varchar(255) NOT NULL,
  `sent_at` datetime(6) NOT NULL,
  `status` varchar(20) NOT NULL,
  `sent_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `core_newslettertestsend_sent_by_id_11afd721_fk_auth_user_id` (`sent_by_id`),
  CONSTRAINT `core_newslettertestsend_sent_by_id_11afd721_fk_auth_user_id` FOREIGN KEY (`sent_by_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_newslettertestsend`
--

LOCK TABLES `core_newslettertestsend` WRITE;
/*!40000 ALTER TABLE `core_newslettertestsend` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_newslettertestsend` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_orderplaced`
--

DROP TABLE IF EXISTS `core_orderplaced`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_orderplaced` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `quantity` int(10) unsigned NOT NULL CHECK (`quantity` >= 0),
  `ordered_date` datetime(6) NOT NULL,
  `price` varchar(100) DEFAULT NULL,
  `status` varchar(200) NOT NULL,
  `customer_id` bigint(20) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `product_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `core_orderplaced_customer_id_60a2ca74_fk_core_customer_id` (`customer_id`),
  KEY `core_orderplaced_user_id_99f0bc0c_fk_auth_user_id` (`user_id`),
  KEY `core_orderplaced_product_id_5dbe4d9d_fk_core_product_id` (`product_id`),
  CONSTRAINT `core_orderplaced_customer_id_60a2ca74_fk_core_customer_id` FOREIGN KEY (`customer_id`) REFERENCES `core_customer` (`id`),
  CONSTRAINT `core_orderplaced_product_id_5dbe4d9d_fk_core_product_id` FOREIGN KEY (`product_id`) REFERENCES `core_product` (`id`),
  CONSTRAINT `core_orderplaced_user_id_99f0bc0c_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_orderplaced`
--

LOCK TABLES `core_orderplaced` WRITE;
/*!40000 ALTER TABLE `core_orderplaced` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_orderplaced` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_product`
--

DROP TABLE IF EXISTS `core_product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_product` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `category` varchar(2) NOT NULL,
  `description` longtext NOT NULL,
  `price` double NOT NULL,
  `discount_price` double DEFAULT NULL,
  `image` varchar(100) NOT NULL,
  `user_id` int(11) NOT NULL,
  `image_webp` varchar(100) DEFAULT NULL,
  `slug` varchar(255) DEFAULT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  `updated_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `core_product_user_id_794bff72_fk_auth_user_id` (`user_id`),
  CONSTRAINT `core_product_user_id_794bff72_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_product`
--

LOCK TABLES `core_product` WRITE;
/*!40000 ALTER TABLE `core_product` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_product` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_sentemail`
--

DROP TABLE IF EXISTS `core_sentemail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_sentemail` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `recipient_email` varchar(254) NOT NULL,
  `recipient_name` varchar(200) NOT NULL,
  `subject` varchar(300) NOT NULL,
  `body` longtext NOT NULL,
  `sent_at` datetime(6) NOT NULL,
  `status` varchar(20) NOT NULL,
  `sent_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `core_sentemail_sent_by_id_9ba36e19_fk_auth_user_id` (`sent_by_id`),
  CONSTRAINT `core_sentemail_sent_by_id_9ba36e19_fk_auth_user_id` FOREIGN KEY (`sent_by_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_sentemail`
--

LOCK TABLES `core_sentemail` WRITE;
/*!40000 ALTER TABLE `core_sentemail` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_sentemail` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_subscription`
--

DROP TABLE IF EXISTS `core_subscription`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_subscription` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `level` varchar(10) NOT NULL,
  `price` double NOT NULL,
  `benefits` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_subscription`
--

LOCK TABLES `core_subscription` WRITE;
/*!40000 ALTER TABLE `core_subscription` DISABLE KEYS */;
INSERT INTO `core_subscription` VALUES
(1,'Free',0,'Basic access to the platform, limited product listings, basic support'),
(2,'Bronze',2000,'Increased product listings, priority support, access to promotional tools'),
(3,'Silver',5000,'All Bronze benefits, featured product placement, advanced analytics, most popular'),
(4,'Gold',10000,'All Silver benefits, unlimited product listings, dedicated account manager, premium support');
/*!40000 ALTER TABLE `core_subscription` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_subscriptionpayment`
--

DROP TABLE IF EXISTS `core_subscriptionpayment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_subscriptionpayment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `payment_proof` varchar(100) NOT NULL,
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `customer_id` bigint(20) NOT NULL,
  `subscription_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `core_subscriptionpay_customer_id_44e6bf2e_fk_core_cust` (`customer_id`),
  KEY `core_subscriptionpay_subscription_id_8d7dce18_fk_core_subs` (`subscription_id`),
  CONSTRAINT `core_subscriptionpay_customer_id_44e6bf2e_fk_core_cust` FOREIGN KEY (`customer_id`) REFERENCES `core_customer` (`id`),
  CONSTRAINT `core_subscriptionpay_subscription_id_8d7dce18_fk_core_subs` FOREIGN KEY (`subscription_id`) REFERENCES `core_subscription` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_subscriptionpayment`
--

LOCK TABLES `core_subscriptionpayment` WRITE;
/*!40000 ALTER TABLE `core_subscriptionpayment` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_subscriptionpayment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_usernewsletterpreference`
--

DROP TABLE IF EXISTS `core_usernewsletterpreference`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_usernewsletterpreference` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `newsletter` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `core_usernewsletterpreference_user_id_15822db5_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_usernewsletterpreference`
--

LOCK TABLES `core_usernewsletterpreference` WRITE;
/*!40000 ALTER TABLE `core_usernewsletterpreference` DISABLE KEYS */;
/*!40000 ALTER TABLE `core_usernewsletterpreference` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=76 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES
(1,'admin','logentry'),
(61,'affiliates','affiliate'),
(64,'affiliates','clicktracking'),
(63,'affiliates','payoutrequest'),
(62,'affiliates','referral'),
(3,'auth','group'),
(2,'auth','permission'),
(4,'auth','user'),
(28,'chatbotapp','chatmessage'),
(29,'chatbotapp','unauthenticatedchatmessage'),
(5,'contenttypes','contenttype'),
(20,'core','accountdeletionrequest'),
(11,'core','banners'),
(16,'core','blog'),
(15,'core','cart'),
(12,'core','customer'),
(24,'core','newslettersendlog'),
(19,'core','newslettersubscriber'),
(23,'core','newslettertestsend'),
(14,'core','orderplaced'),
(13,'core','product'),
(22,'core','sentemail'),
(17,'core','subscription'),
(18,'core','subscriptionpayment'),
(21,'core','usernewsletterpreference'),
(65,'jobs','apiconfiguration'),
(73,'jobs','apirequestlog'),
(66,'jobs','company'),
(67,'jobs','industry'),
(68,'jobs','job'),
(72,'jobs','jobapplication'),
(75,'jobs','jobcourserecommendation'),
(71,'jobs','jobsearchpreference'),
(70,'jobs','savedjob'),
(69,'jobs','skill'),
(74,'jobs','userjobapproval'),
(60,'landing','emailsignup'),
(30,'lms','activitylog'),
(50,'lms','adexemptuser'),
(56,'lms','certificatepayment'),
(52,'lms','certificatetemplate'),
(31,'lms','choice'),
(48,'lms','contentaccess'),
(32,'lms','course'),
(44,'lms','coursecontent'),
(43,'lms','courseenrollment'),
(33,'lms','coursemodule'),
(57,'lms','coursepayment'),
(58,'lms','coursepaymentgroup'),
(39,'lms','essay_question'),
(46,'lms','grade'),
(47,'lms','instructorrequest'),
(34,'lms','lmsprofile'),
(40,'lms','mcquestion'),
(59,'lms','modulepayment'),
(54,'lms','moduleprogress'),
(51,'lms','paymentmethod'),
(35,'lms','program'),
(36,'lms','question'),
(37,'lms','quiz'),
(55,'lms','quizgenerationjob'),
(38,'lms','quiztaker'),
(42,'lms','semester'),
(49,'lms','sitesettings'),
(45,'lms','studentanswer'),
(53,'lms','studentcertificate'),
(41,'lms','tf_question'),
(6,'sessions','session'),
(7,'sites','site'),
(26,'talents','comment'),
(27,'talents','like'),
(25,'talents','talent'),
(8,'webpush','group'),
(9,'webpush','pushinformation'),
(10,'webpush','subscriptioninfo');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=111 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES
(1,'contenttypes','0001_initial','2026-07-31 17:48:53'),
(2,'auth','0001_initial','2026-07-31 17:48:54'),
(3,'admin','0001_initial','2026-07-31 17:48:55'),
(4,'admin','0002_logentry_remove_auto_add','2026-07-31 17:48:55'),
(5,'admin','0003_logentry_add_action_flag_choices','2026-07-31 17:48:55'),
(6,'contenttypes','0002_remove_content_type_name','2026-07-31 17:48:55'),
(7,'affiliates','0001_initial','2026-07-31 17:48:56'),
(8,'auth','0002_alter_permission_name_max_length','2026-07-31 17:48:56'),
(9,'auth','0003_alter_user_email_max_length','2026-07-31 17:48:56'),
(10,'auth','0004_alter_user_username_opts','2026-07-31 17:48:56'),
(11,'auth','0005_alter_user_last_login_null','2026-07-31 17:48:56'),
(12,'auth','0006_require_contenttypes_0002','2026-07-31 17:48:56'),
(13,'auth','0007_alter_validators_add_error_messages','2026-07-31 17:48:56'),
(14,'auth','0008_alter_user_username_max_length','2026-07-31 17:48:57'),
(15,'auth','0009_alter_user_last_name_max_length','2026-07-31 17:48:57'),
(16,'auth','0010_alter_group_name_max_length','2026-07-31 17:48:57'),
(17,'auth','0011_update_proxy_permissions','2026-07-31 17:48:57'),
(18,'auth','0012_alter_user_first_name_max_length','2026-07-31 17:48:57'),
(19,'chatbotapp','0001_initial','2026-07-31 17:48:57'),
(20,'chatbotapp','0002_chatmessage_user','2026-07-31 17:48:57'),
(21,'chatbotapp','0003_chatmessage_session_key','2026-07-31 17:48:57'),
(22,'chatbotapp','0004_unauthenticatedchatmessage','2026-07-31 17:48:57'),
(23,'chatbotapp','0005_add_session_key_to_unauthenticatedchatmessage','2026-07-31 17:48:57'),
(24,'core','0001_initial','2026-07-31 17:48:59'),
(25,'core','webp_migration','2026-07-31 17:48:59'),
(26,'core','0002_blog','2026-07-31 17:49:00'),
(27,'core','0003_product_customer','2026-07-31 17:49:00'),
(28,'core','0004_remove_product_customer','2026-07-31 17:49:00'),
(29,'core','0005_blog_thumbnail','2026-07-31 17:49:00'),
(30,'core','0006_subscription_customer_subscription','2026-07-31 17:49:01'),
(31,'core','0007_alter_customer_subscription','2026-07-31 17:49:01'),
(32,'core','0008_customer_phone_number','2026-07-31 17:49:01'),
(33,'core','0009_subscriptionpayment','2026-07-31 17:49:01'),
(34,'core','0010_alter_product_category','2026-07-31 17:49:01'),
(35,'core','0011_alter_customer_block_number_and_more','2026-07-31 17:49:02'),
(36,'core','0012_customer_is_university_student_and_more','2026-07-31 17:49:02'),
(37,'core','0013_add_is_university_student','2026-07-31 17:49:02'),
(38,'core','0014_newslettersubscriber','2026-07-31 17:49:02'),
(39,'core','0015_merge_0014_newslettersubscriber_webp_migration','2026-07-31 17:49:02'),
(40,'core','0016_product_image_webp','2026-07-31 17:49:03'),
(41,'core','0017_add_blog_thumbnail_webp','2026-07-31 17:49:03'),
(42,'core','0018_product_slug','2026-07-31 17:49:03'),
(43,'core','0019_auto_generate_slugs','2026-07-31 17:49:03'),
(44,'core','0020_product_created_at_product_updated_at','2026-07-31 17:49:04'),
(45,'core','0021_ensure_all_products_have_slugs','2026-07-31 17:49:04'),
(46,'core','0022_remove_product_created_at_remove_product_updated_at','2026-07-31 17:49:04'),
(47,'core','0023_product_created_at_product_updated_at','2026-07-31 17:49:04'),
(48,'core','0024_add_blog_slug','2026-07-31 17:49:05'),
(49,'core','0025_blog_category_alter_blog_is_markdown','2026-07-31 17:49:05'),
(50,'core','0003_fix_apscheduler_key_length','2026-07-31 17:49:05'),
(51,'core','0004_update_charset_collation','2026-07-31 17:49:05'),
(52,'core','0026_merge_charset_collation_and_blog_category','2026-07-31 17:49:05'),
(53,'core','0027_blog_thumbnail_cloudinary_blog_upload_method_and_more','2026-07-31 17:49:06'),
(54,'core','0028_accountdeletionrequest','2026-07-31 17:49:06'),
(55,'core','0029_usernewsletterpreference','2026-07-31 17:49:07'),
(56,'core','0030_sentemail','2026-07-31 17:49:07'),
(57,'core','0031_newslettertestsend_newslettersendlog','2026-07-31 17:49:08'),
(58,'lms','0001_initial','2026-07-31 17:49:14'),
(59,'lms','0002_instructorrequest','2026-07-31 17:49:14'),
(60,'lms','0003_contentaccess','2026-07-31 17:49:15'),
(61,'lms','0004_course_is_free','2026-07-31 17:49:15'),
(62,'lms','0005_sitesettings','2026-07-31 17:49:15'),
(63,'lms','0006_create_initial_site_settings','2026-07-31 17:49:16'),
(64,'lms','0007_course_course_type_alter_course_code_and_more','2026-07-31 17:49:18'),
(65,'lms','0008_increase_slug_length','2026-07-31 17:49:18'),
(66,'lms','0009_ensure_site_settings','2026-07-31 17:49:18'),
(67,'lms','0010_add_ad_exempt_user','2026-07-31 17:49:19'),
(68,'lms','0011_paymentmethod_courseenrollment_payment_approved_by_and_more','2026-07-31 17:49:21'),
(69,'lms','0012_remove_paymentmethod_phone_number_and_more','2026-07-31 17:49:22'),
(70,'lms','0013_course_is_pinned','2026-07-31 17:49:22'),
(71,'lms','0014_course_price','2026-07-31 17:49:22'),
(72,'lms','0015_course_content','2026-07-31 17:49:22'),
(73,'lms','0016_coursemodule_description_nullable','2026-07-31 17:49:23'),
(74,'lms','0017_alter_course_content_alter_course_summary','2026-07-31 17:49:23'),
(75,'lms','0018_sitesettings_show_list_ads','2026-07-31 17:49:23'),
(76,'lms','0019_certificatetemplate_alter_quiz_pass_mark_and_more','2026-07-31 17:49:24'),
(77,'lms','0020_coursemodule_skip_assessment','2026-07-31 17:49:25'),
(78,'lms','0021_quiz_generated_for_quiz_generation_completed_at_and_more','2026-07-31 17:49:26'),
(79,'lms','0022_alter_quiz_slug_length','2026-07-31 17:49:26'),
(80,'lms','0023_dedupe_ai_module_quizzes_and_constraints','2026-07-31 17:49:26'),
(81,'lms','0024_alter_certificatetemplate_accent_color_and_more','2026-07-31 17:49:27'),
(82,'lms','0025_lmsprofile_legal_name','2026-07-31 17:49:27'),
(83,'lms','0026_alter_quiz_slug_alter_quiz_title','2026-07-31 17:49:27'),
(84,'lms','0027_quizgenerationjob','2026-07-31 17:49:28'),
(85,'lms','0028_quiz_ai_generated','2026-07-31 17:49:28'),
(86,'lms','0029_course_created_at','2026-07-31 17:49:28'),
(87,'jobs','0001_initial','2026-07-31 17:49:34'),
(88,'jobs','0002_alter_apiconfiguration_name','2026-07-31 17:49:34'),
(89,'jobs','0003_job_is_approved','2026-07-31 17:49:34'),
(90,'jobs','0004_remove_job_is_approved_userjobapproval','2026-07-31 17:49:35'),
(91,'jobs','0005_alter_job_company','2026-07-31 17:49:36'),
(92,'jobs','0006_job_job_posting_type_and_more','2026-07-31 17:49:38'),
(93,'jobs','0007_jobcourserecommendation','2026-07-31 17:49:39'),
(94,'jobs','0008_alter_jobcourserecommendation_id_and_more','2026-07-31 17:49:39'),
(95,'landing','0001_initial','2026-07-31 17:49:40'),
(96,'landing','0002_emailsignup_purpose','2026-07-31 17:49:40'),
(97,'lms','0030_certificate_payment','2026-07-31 17:49:40'),
(98,'lms','0031_certificatepayment_webhook_fields','2026-07-31 17:49:41'),
(99,'lms','0032_coursepayment','2026-07-31 17:49:41'),
(100,'lms','0033_courseenrollment_admin_granted_access_and_more','2026-07-31 17:49:43'),
(101,'lms','0034_coursepaymentgroup_and_more','2026-07-31 17:49:45'),
(102,'sessions','0001_initial','2026-07-31 17:49:46'),
(103,'sites','0001_initial','2026-07-31 17:49:46'),
(104,'sites','0002_alter_domain_unique','2026-07-31 17:49:46'),
(105,'talents','0001_initial','2026-07-31 17:49:48'),
(106,'webpush','0001_initial','2026-07-31 17:49:49'),
(107,'webpush','0002_auto_20190603_0005','2026-07-31 17:49:49'),
(108,'webpush','0003_subscriptioninfo_user_agent','2026-07-31 17:49:49'),
(109,'webpush','0004_auto_20220831_1500','2026-07-31 17:49:51'),
(110,'webpush','0005_auto_20230614_1529','2026-07-31 17:49:53');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_site`
--

DROP TABLE IF EXISTS `django_site`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_site` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(100) NOT NULL,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_site_domain_a2e37b91_uniq` (`domain`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_site`
--

LOCK TABLES `django_site` WRITE;
/*!40000 ALTER TABLE `django_site` DISABLE KEYS */;
INSERT INTO `django_site` VALUES
(1,'example.com','example.com');
/*!40000 ALTER TABLE `django_site` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_apiconfiguration`
--

DROP TABLE IF EXISTS `jobs_apiconfiguration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_apiconfiguration` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `api_key` varchar(255) NOT NULL,
  `api_secret` varchar(255) NOT NULL,
  `additional_params` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`additional_params`)),
  `is_active` tinyint(1) NOT NULL,
  `last_fetch_date` datetime(6) DEFAULT NULL,
  `request_count` int(10) unsigned NOT NULL CHECK (`request_count` >= 0),
  `daily_limit` int(10) unsigned DEFAULT NULL CHECK (`daily_limit` >= 0),
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_apiconfiguration`
--

LOCK TABLES `jobs_apiconfiguration` WRITE;
/*!40000 ALTER TABLE `jobs_apiconfiguration` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_apiconfiguration` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_apirequestlog`
--

DROP TABLE IF EXISTS `jobs_apirequestlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_apirequestlog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `endpoint` varchar(255) NOT NULL,
  `request_params` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`request_params`)),
  `response_status` smallint(5) unsigned NOT NULL CHECK (`response_status` >= 0),
  `response_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`response_data`)),
  `error_message` longtext NOT NULL,
  `request_date` datetime(6) NOT NULL,
  `execution_time` double DEFAULT NULL,
  `jobs_fetched` int(10) unsigned NOT NULL CHECK (`jobs_fetched` >= 0),
  `jobs_created` int(10) unsigned NOT NULL CHECK (`jobs_created` >= 0),
  `jobs_updated` int(10) unsigned NOT NULL CHECK (`jobs_updated` >= 0),
  `api_config_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `jobs_apirequestlog_api_config_id_9320a3da_fk_jobs_apic` (`api_config_id`),
  CONSTRAINT `jobs_apirequestlog_api_config_id_9320a3da_fk_jobs_apic` FOREIGN KEY (`api_config_id`) REFERENCES `jobs_apiconfiguration` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_apirequestlog`
--

LOCK TABLES `jobs_apirequestlog` WRITE;
/*!40000 ALTER TABLE `jobs_apirequestlog` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_apirequestlog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_company`
--

DROP TABLE IF EXISTS `jobs_company`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_company` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `website` varchar(200) NOT NULL,
  `logo` varchar(100) DEFAULT NULL,
  `address` varchar(255) NOT NULL,
  `city` varchar(100) NOT NULL,
  `country` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `phone` varchar(30) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `is_verified` tinyint(1) NOT NULL,
  `created_by_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `jobs_company_created_by_id_f5729459_fk_auth_user_id` (`created_by_id`),
  CONSTRAINT `jobs_company_created_by_id_f5729459_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_company`
--

LOCK TABLES `jobs_company` WRITE;
/*!40000 ALTER TABLE `jobs_company` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_company` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_industry`
--

DROP TABLE IF EXISTS `jobs_industry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_industry` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_industry`
--

LOCK TABLES `jobs_industry` WRITE;
/*!40000 ALTER TABLE `jobs_industry` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_industry` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_job`
--

DROP TABLE IF EXISTS `jobs_job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_job` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `location` varchar(100) NOT NULL,
  `is_remote` tinyint(1) NOT NULL,
  `salary_min` decimal(12,2) DEFAULT NULL,
  `salary_max` decimal(12,2) DEFAULT NULL,
  `salary_currency` varchar(10) NOT NULL,
  `job_type` varchar(20) NOT NULL,
  `experience_level` varchar(20) NOT NULL,
  `requirements` longtext NOT NULL,
  `responsibilities` longtext NOT NULL,
  `benefits` longtext NOT NULL,
  `application_deadline` datetime(6) NOT NULL,
  `posted_date` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_featured` tinyint(1) NOT NULL,
  `views_count` int(10) unsigned NOT NULL CHECK (`views_count` >= 0),
  `applications_count` int(10) unsigned NOT NULL CHECK (`applications_count` >= 0),
  `source` varchar(50) NOT NULL,
  `external_id` varchar(255) NOT NULL,
  `external_url` varchar(200) NOT NULL,
  `company_id` bigint(20) DEFAULT NULL,
  `created_by_id` int(11) NOT NULL,
  `industry_id` bigint(20) DEFAULT NULL,
  `job_posting_type` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `jobs_job_title_0e1e41_idx` (`title`),
  KEY `jobs_job_locatio_8b2f8c_idx` (`location`),
  KEY `jobs_job_job_typ_f6c220_idx` (`job_type`),
  KEY `jobs_job_source_e2155e_idx` (`source`),
  KEY `jobs_job_externa_6b51f9_idx` (`external_id`),
  KEY `jobs_job_created_by_id_f3283268_fk_auth_user_id` (`created_by_id`),
  KEY `jobs_job_industry_id_009b1255_fk_jobs_industry_id` (`industry_id`),
  KEY `jobs_job_company_id_1f42ea7c_fk_jobs_company_id` (`company_id`),
  CONSTRAINT `jobs_job_company_id_1f42ea7c_fk_jobs_company_id` FOREIGN KEY (`company_id`) REFERENCES `jobs_company` (`id`),
  CONSTRAINT `jobs_job_created_by_id_f3283268_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `jobs_job_industry_id_009b1255_fk_jobs_industry_id` FOREIGN KEY (`industry_id`) REFERENCES `jobs_industry` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_job`
--

LOCK TABLES `jobs_job` WRITE;
/*!40000 ALTER TABLE `jobs_job` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_job` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_job_skills`
--

DROP TABLE IF EXISTS `jobs_job_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_job_skills` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `job_id` bigint(20) NOT NULL,
  `skill_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `jobs_job_skills_job_id_skill_id_1a073345_uniq` (`job_id`,`skill_id`),
  KEY `jobs_job_skills_skill_id_bfb4f93e_fk_jobs_skill_id` (`skill_id`),
  CONSTRAINT `jobs_job_skills_job_id_81ac3e26_fk_jobs_job_id` FOREIGN KEY (`job_id`) REFERENCES `jobs_job` (`id`),
  CONSTRAINT `jobs_job_skills_skill_id_bfb4f93e_fk_jobs_skill_id` FOREIGN KEY (`skill_id`) REFERENCES `jobs_skill` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_job_skills`
--

LOCK TABLES `jobs_job_skills` WRITE;
/*!40000 ALTER TABLE `jobs_job_skills` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_job_skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_jobapplication`
--

DROP TABLE IF EXISTS `jobs_jobapplication`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_jobapplication` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `cover_letter` longtext NOT NULL,
  `resume` varchar(100) NOT NULL,
  `status` varchar(20) NOT NULL,
  `applied_date` datetime(6) NOT NULL,
  `updated_date` datetime(6) NOT NULL,
  `employer_notes` longtext NOT NULL,
  `applicant_id` int(11) NOT NULL,
  `job_id` bigint(20) NOT NULL,
  `additional_documents` varchar(100) DEFAULT NULL,
  `availability` varchar(100) NOT NULL,
  `phone_number` varchar(20) NOT NULL,
  `portfolio_url` varchar(200) NOT NULL,
  `salary_expectation` decimal(12,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_job_application` (`job_id`,`applicant_id`),
  KEY `jobs_jobapplication_applicant_id_7f41cf6a_fk_auth_user_id` (`applicant_id`),
  CONSTRAINT `jobs_jobapplication_applicant_id_7f41cf6a_fk_auth_user_id` FOREIGN KEY (`applicant_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `jobs_jobapplication_job_id_625fd19d_fk_jobs_job_id` FOREIGN KEY (`job_id`) REFERENCES `jobs_job` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_jobapplication`
--

LOCK TABLES `jobs_jobapplication` WRITE;
/*!40000 ALTER TABLE `jobs_jobapplication` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_jobapplication` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_jobcourserecommendation`
--

DROP TABLE IF EXISTS `jobs_jobcourserecommendation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_jobcourserecommendation` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `reasons` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`reasons`)),
  `source` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `job_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `job_id` (`job_id`),
  CONSTRAINT `jobs_jobcourserecommendation_job_id_f2ca1669_fk_jobs_job_id` FOREIGN KEY (`job_id`) REFERENCES `jobs_job` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_jobcourserecommendation`
--

LOCK TABLES `jobs_jobcourserecommendation` WRITE;
/*!40000 ALTER TABLE `jobs_jobcourserecommendation` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_jobcourserecommendation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_jobcourserecommendation_courses`
--

DROP TABLE IF EXISTS `jobs_jobcourserecommendation_courses`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_jobcourserecommendation_courses` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `jobcourserecommendation_id` bigint(20) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `jobs_jobcourserecommenda_jobcourserecommendation__3eafdf43_uniq` (`jobcourserecommendation_id`,`course_id`),
  KEY `jobs_jobcourserecomm_course_id_2b24f17d_fk_lms_cours` (`course_id`),
  CONSTRAINT `jobs_jobcourserecomm_course_id_2b24f17d_fk_lms_cours` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `jobs_jobcourserecommendat_jobcourserecommendation_i_45d5f873_fk` FOREIGN KEY (`jobcourserecommendation_id`) REFERENCES `jobs_jobcourserecommendation` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_jobcourserecommendation_courses`
--

LOCK TABLES `jobs_jobcourserecommendation_courses` WRITE;
/*!40000 ALTER TABLE `jobs_jobcourserecommendation_courses` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_jobcourserecommendation_courses` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_jobsearchpreference`
--

DROP TABLE IF EXISTS `jobs_jobsearchpreference`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_jobsearchpreference` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `job_types` varchar(255) NOT NULL,
  `locations` varchar(255) NOT NULL,
  `keywords` varchar(255) NOT NULL,
  `experience_levels` varchar(255) NOT NULL,
  `salary_min` decimal(12,2) DEFAULT NULL,
  `email_notifications` tinyint(1) NOT NULL,
  `notification_frequency` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `jobs_jobsearchpreference_user_id_92d4153e_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_jobsearchpreference`
--

LOCK TABLES `jobs_jobsearchpreference` WRITE;
/*!40000 ALTER TABLE `jobs_jobsearchpreference` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_jobsearchpreference` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_jobsearchpreference_industries`
--

DROP TABLE IF EXISTS `jobs_jobsearchpreference_industries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_jobsearchpreference_industries` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `jobsearchpreference_id` bigint(20) NOT NULL,
  `industry_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `jobs_jobsearchpreference_jobsearchpreference_id_i_d8a77450_uniq` (`jobsearchpreference_id`,`industry_id`),
  KEY `jobs_jobsearchprefer_industry_id_04949570_fk_jobs_indu` (`industry_id`),
  CONSTRAINT `jobs_jobsearchprefer_industry_id_04949570_fk_jobs_indu` FOREIGN KEY (`industry_id`) REFERENCES `jobs_industry` (`id`),
  CONSTRAINT `jobs_jobsearchprefer_jobsearchpreference__a6c91193_fk_jobs_jobs` FOREIGN KEY (`jobsearchpreference_id`) REFERENCES `jobs_jobsearchpreference` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_jobsearchpreference_industries`
--

LOCK TABLES `jobs_jobsearchpreference_industries` WRITE;
/*!40000 ALTER TABLE `jobs_jobsearchpreference_industries` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_jobsearchpreference_industries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_jobsearchpreference_skills`
--

DROP TABLE IF EXISTS `jobs_jobsearchpreference_skills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_jobsearchpreference_skills` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `jobsearchpreference_id` bigint(20) NOT NULL,
  `skill_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `jobs_jobsearchpreference_jobsearchpreference_id_s_9a0653a7_uniq` (`jobsearchpreference_id`,`skill_id`),
  KEY `jobs_jobsearchprefer_skill_id_1268d16d_fk_jobs_skil` (`skill_id`),
  CONSTRAINT `jobs_jobsearchprefer_jobsearchpreference__e8a86e8e_fk_jobs_jobs` FOREIGN KEY (`jobsearchpreference_id`) REFERENCES `jobs_jobsearchpreference` (`id`),
  CONSTRAINT `jobs_jobsearchprefer_skill_id_1268d16d_fk_jobs_skil` FOREIGN KEY (`skill_id`) REFERENCES `jobs_skill` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_jobsearchpreference_skills`
--

LOCK TABLES `jobs_jobsearchpreference_skills` WRITE;
/*!40000 ALTER TABLE `jobs_jobsearchpreference_skills` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_jobsearchpreference_skills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_savedjob`
--

DROP TABLE IF EXISTS `jobs_savedjob`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_savedjob` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `saved_date` datetime(6) NOT NULL,
  `job_id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_saved_job` (`job_id`,`user_id`),
  KEY `jobs_savedjob_user_id_49e68f73_fk_auth_user_id` (`user_id`),
  CONSTRAINT `jobs_savedjob_job_id_e069c6bf_fk_jobs_job_id` FOREIGN KEY (`job_id`) REFERENCES `jobs_job` (`id`),
  CONSTRAINT `jobs_savedjob_user_id_49e68f73_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_savedjob`
--

LOCK TABLES `jobs_savedjob` WRITE;
/*!40000 ALTER TABLE `jobs_savedjob` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_savedjob` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_skill`
--

DROP TABLE IF EXISTS `jobs_skill`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_skill` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_skill`
--

LOCK TABLES `jobs_skill` WRITE;
/*!40000 ALTER TABLE `jobs_skill` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_skill` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs_userjobapproval`
--

DROP TABLE IF EXISTS `jobs_userjobapproval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_userjobapproval` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `is_approved` tinyint(1) NOT NULL,
  `approved_date` datetime(6) DEFAULT NULL,
  `reason` longtext NOT NULL,
  `approved_by_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `jobs_userjobapproval_approved_by_id_cb70a8ec_fk_auth_user_id` (`approved_by_id`),
  CONSTRAINT `jobs_userjobapproval_approved_by_id_cb70a8ec_fk_auth_user_id` FOREIGN KEY (`approved_by_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `jobs_userjobapproval_user_id_dd8494dc_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs_userjobapproval`
--

LOCK TABLES `jobs_userjobapproval` WRITE;
/*!40000 ALTER TABLE `jobs_userjobapproval` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs_userjobapproval` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `landing_emailsignup`
--

DROP TABLE IF EXISTS `landing_emailsignup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `landing_emailsignup` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `email` varchar(254) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `purpose` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `landing_emailsignup`
--

LOCK TABLES `landing_emailsignup` WRITE;
/*!40000 ALTER TABLE `landing_emailsignup` DISABLE KEYS */;
/*!40000 ALTER TABLE `landing_emailsignup` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_activitylog`
--

DROP TABLE IF EXISTS `lms_activitylog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_activitylog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `timestamp` datetime(6) NOT NULL,
  `message` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_activitylog`
--

LOCK TABLES `lms_activitylog` WRITE;
/*!40000 ALTER TABLE `lms_activitylog` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_activitylog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_adexemptuser`
--

DROP TABLE IF EXISTS `lms_adexemptuser`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_adexemptuser` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `reason` varchar(255) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `lms_adexemptuser_user_id_d3c9b626_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_adexemptuser`
--

LOCK TABLES `lms_adexemptuser` WRITE;
/*!40000 ALTER TABLE `lms_adexemptuser` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_adexemptuser` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_certificatepayment`
--

DROP TABLE IF EXISTS `lms_certificatepayment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_certificatepayment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `snippe_session_id` varchar(100) NOT NULL,
  `snippe_reference` varchar(100) NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `checkout_url` varchar(200) NOT NULL,
  `payment_link_url` varchar(200) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `certificate_id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `webhook_event_id` varchar(100) NOT NULL,
  `failure_reason` longtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_certificatepayme_certificate_id_9eeed05b_fk_lms_stude` (`certificate_id`),
  KEY `lms_certificatepayment_user_id_662dc2d5_fk_auth_user_id` (`user_id`),
  CONSTRAINT `lms_certificatepayme_certificate_id_9eeed05b_fk_lms_stude` FOREIGN KEY (`certificate_id`) REFERENCES `lms_studentcertificate` (`id`),
  CONSTRAINT `lms_certificatepayment_user_id_662dc2d5_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_certificatepayment`
--

LOCK TABLES `lms_certificatepayment` WRITE;
/*!40000 ALTER TABLE `lms_certificatepayment` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_certificatepayment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_certificatetemplate`
--

DROP TABLE IF EXISTS `lms_certificatetemplate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_certificatetemplate` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `subtitle` varchar(255) NOT NULL,
  `organization_name` varchar(255) NOT NULL,
  `instructor_name` varchar(255) NOT NULL,
  `description` longtext NOT NULL,
  `template_style` varchar(50) NOT NULL,
  `orientation` varchar(20) NOT NULL,
  `primary_color` varchar(20) NOT NULL,
  `secondary_color` varchar(20) NOT NULL,
  `accent_color` varchar(20) NOT NULL,
  `background_style` varchar(50) NOT NULL,
  `border_style` varchar(50) NOT NULL,
  `font_style` varchar(50) NOT NULL,
  `logo` varchar(100) DEFAULT NULL,
  `signature_image` varchar(100) DEFAULT NULL,
  `seal_image` varchar(100) DEFAULT NULL,
  `watermark_image` varchar(100) DEFAULT NULL,
  `certificate_body` longtext NOT NULL,
  `recipient_name_format` varchar(100) NOT NULL,
  `course_name_display` varchar(150) NOT NULL,
  `completion_date_display` varchar(100) NOT NULL,
  `certificate_id_display` varchar(100) NOT NULL,
  `instructor_signature_text` varchar(255) NOT NULL,
  `footer_note` longtext NOT NULL,
  `completion_percentage` int(10) unsigned NOT NULL CHECK (`completion_percentage` >= 0),
  `enable_verification` tinyint(1) NOT NULL,
  `show_qr_code` tinyint(1) NOT NULL,
  `show_certificate_id` tinyint(1) NOT NULL,
  `verification_url_format` varchar(255) NOT NULL,
  `expires` tinyint(1) NOT NULL,
  `validity_months` int(10) unsigned DEFAULT NULL CHECK (`validity_months` >= 0),
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  `certificate_price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_certificatetemplate_course_id_c161fbe1_fk_lms_course_id` (`course_id`),
  CONSTRAINT `lms_certificatetemplate_course_id_c161fbe1_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_certificatetemplate`
--

LOCK TABLES `lms_certificatetemplate` WRITE;
/*!40000 ALTER TABLE `lms_certificatetemplate` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_certificatetemplate` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_choice`
--

DROP TABLE IF EXISTS `lms_choice`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_choice` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `content` longtext NOT NULL,
  `correct` tinyint(1) NOT NULL,
  `question_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_choice_question_id_913bf082_fk_lms_mcque` (`question_id`),
  CONSTRAINT `lms_choice_question_id_913bf082_fk_lms_mcque` FOREIGN KEY (`question_id`) REFERENCES `lms_mcquestion` (`question_ptr_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_choice`
--

LOCK TABLES `lms_choice` WRITE;
/*!40000 ALTER TABLE `lms_choice` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_choice` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_contentaccess`
--

DROP TABLE IF EXISTS `lms_contentaccess`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_contentaccess` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `accessed_at` datetime(6) NOT NULL,
  `completed` tinyint(1) NOT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `content_id` bigint(20) NOT NULL,
  `student_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_contentaccess_student_id_content_id_98fc0fd9_uniq` (`student_id`,`content_id`),
  KEY `lms_contentaccess_content_id_7dae723f_fk_lms_coursecontent_id` (`content_id`),
  CONSTRAINT `lms_contentaccess_content_id_7dae723f_fk_lms_coursecontent_id` FOREIGN KEY (`content_id`) REFERENCES `lms_coursecontent` (`id`),
  CONSTRAINT `lms_contentaccess_student_id_ce158f9f_fk_lms_lmsprofile_id` FOREIGN KEY (`student_id`) REFERENCES `lms_lmsprofile` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_contentaccess`
--

LOCK TABLES `lms_contentaccess` WRITE;
/*!40000 ALTER TABLE `lms_contentaccess` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_contentaccess` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_course`
--

DROP TABLE IF EXISTS `lms_course`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_course` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `slug` varchar(100) NOT NULL,
  `code` varchar(20) DEFAULT NULL,
  `credit` int(11) DEFAULT NULL,
  `summary` longtext NOT NULL,
  `level` varchar(2) DEFAULT NULL,
  `year` int(11) DEFAULT NULL,
  `semester` varchar(10) DEFAULT NULL,
  `is_elective` tinyint(1) NOT NULL,
  `image` varchar(100) DEFAULT NULL,
  `program_id` bigint(20) DEFAULT NULL,
  `is_free` tinyint(1) NOT NULL,
  `course_type` varchar(10) NOT NULL,
  `is_pinned` tinyint(1) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `content` longtext NOT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  UNIQUE KEY `code` (`code`),
  KEY `lms_course_program_id_f7b59f67_fk_lms_program_id` (`program_id`),
  CONSTRAINT `lms_course_program_id_f7b59f67_fk_lms_program_id` FOREIGN KEY (`program_id`) REFERENCES `lms_program` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_course`
--

LOCK TABLES `lms_course` WRITE;
/*!40000 ALTER TABLE `lms_course` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_course` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_course_instructors`
--

DROP TABLE IF EXISTS `lms_course_instructors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_course_instructors` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `course_id` bigint(20) NOT NULL,
  `lmsprofile_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_course_instructors_course_id_lmsprofile_id_4413693c_uniq` (`course_id`,`lmsprofile_id`),
  KEY `lms_course_instructo_lmsprofile_id_fd57c502_fk_lms_lmspr` (`lmsprofile_id`),
  CONSTRAINT `lms_course_instructo_lmsprofile_id_fd57c502_fk_lms_lmspr` FOREIGN KEY (`lmsprofile_id`) REFERENCES `lms_lmsprofile` (`id`),
  CONSTRAINT `lms_course_instructors_course_id_1783d40c_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_course_instructors`
--

LOCK TABLES `lms_course_instructors` WRITE;
/*!40000 ALTER TABLE `lms_course_instructors` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_course_instructors` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_coursecontent`
--

DROP TABLE IF EXISTS `lms_coursecontent`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_coursecontent` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `content_type` varchar(10) NOT NULL,
  `document` varchar(100) DEFAULT NULL,
  `video_url` varchar(200) DEFAULT NULL,
  `external_link` varchar(200) DEFAULT NULL,
  `text_content` longtext DEFAULT NULL,
  `order` int(10) unsigned NOT NULL CHECK (`order` >= 0),
  `date_added` datetime(6) NOT NULL,
  `module_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_coursecontent_module_id_49d1b298_fk_lms_coursemodule_id` (`module_id`),
  CONSTRAINT `lms_coursecontent_module_id_49d1b298_fk_lms_coursemodule_id` FOREIGN KEY (`module_id`) REFERENCES `lms_coursemodule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_coursecontent`
--

LOCK TABLES `lms_coursecontent` WRITE;
/*!40000 ALTER TABLE `lms_coursecontent` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_coursecontent` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_courseenrollment`
--

DROP TABLE IF EXISTS `lms_courseenrollment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_courseenrollment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `date_enrolled` datetime(6) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  `student_id` bigint(20) NOT NULL,
  `payment_approved_by_id` int(11) DEFAULT NULL,
  `payment_approved_date` datetime(6) DEFAULT NULL,
  `payment_date` datetime(6) DEFAULT NULL,
  `payment_notes` longtext DEFAULT NULL,
  `payment_proof` varchar(100) DEFAULT NULL,
  `payment_status` varchar(20) NOT NULL,
  `payment_method_id` bigint(20) DEFAULT NULL,
  `admin_granted_access` tinyint(1) NOT NULL,
  `admin_granted_certificate` tinyint(1) NOT NULL,
  `granted_by_id` int(11) DEFAULT NULL,
  `certificate_prepaid` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_courseenrollment_student_id_course_id_b8646491_uniq` (`student_id`,`course_id`),
  KEY `lms_courseenrollment_course_id_c726a049_fk_lms_course_id` (`course_id`),
  KEY `lms_courseenrollment_payment_approved_by__ef34c5a8_fk_auth_user` (`payment_approved_by_id`),
  KEY `lms_courseenrollment_payment_method_id_ca0e49f8_fk_lms_payme` (`payment_method_id`),
  KEY `lms_courseenrollment_granted_by_id_4d1b36b0_fk_auth_user_id` (`granted_by_id`),
  CONSTRAINT `lms_courseenrollment_course_id_c726a049_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `lms_courseenrollment_granted_by_id_4d1b36b0_fk_auth_user_id` FOREIGN KEY (`granted_by_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `lms_courseenrollment_payment_approved_by__ef34c5a8_fk_auth_user` FOREIGN KEY (`payment_approved_by_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `lms_courseenrollment_payment_method_id_ca0e49f8_fk_lms_payme` FOREIGN KEY (`payment_method_id`) REFERENCES `lms_paymentmethod` (`id`),
  CONSTRAINT `lms_courseenrollment_student_id_3001df67_fk_lms_lmsprofile_id` FOREIGN KEY (`student_id`) REFERENCES `lms_lmsprofile` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_courseenrollment`
--

LOCK TABLES `lms_courseenrollment` WRITE;
/*!40000 ALTER TABLE `lms_courseenrollment` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_courseenrollment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_coursemodule`
--

DROP TABLE IF EXISTS `lms_coursemodule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_coursemodule` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `description` longtext NOT NULL,
  `order` int(10) unsigned NOT NULL CHECK (`order` >= 0),
  `course_id` bigint(20) NOT NULL,
  `skip_assessment` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_coursemodule_course_id_033dda8b_fk_lms_course_id` (`course_id`),
  CONSTRAINT `lms_coursemodule_course_id_033dda8b_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_coursemodule`
--

LOCK TABLES `lms_coursemodule` WRITE;
/*!40000 ALTER TABLE `lms_coursemodule` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_coursemodule` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_coursepayment`
--

DROP TABLE IF EXISTS `lms_coursepayment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_coursepayment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `snippe_session_id` varchar(100) NOT NULL,
  `snippe_reference` varchar(100) NOT NULL,
  `webhook_event_id` varchar(100) NOT NULL,
  `failure_reason` longtext NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `checkout_url` varchar(200) NOT NULL,
  `payment_link_url` varchar(200) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_coursepayment_course_id_1a4b6350_fk_lms_course_id` (`course_id`),
  KEY `lms_coursepayment_user_id_83ac2593_fk_auth_user_id` (`user_id`),
  CONSTRAINT `lms_coursepayment_course_id_1a4b6350_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `lms_coursepayment_user_id_83ac2593_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_coursepayment`
--

LOCK TABLES `lms_coursepayment` WRITE;
/*!40000 ALTER TABLE `lms_coursepayment` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_coursepayment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_coursepaymentgroup`
--

DROP TABLE IF EXISTS `lms_coursepaymentgroup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_coursepaymentgroup` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_number` int(10) unsigned NOT NULL CHECK (`group_number` >= 0),
  `price` decimal(10,2) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_coursepaymentgroup_course_id_group_number_ff9eafc1_uniq` (`course_id`,`group_number`),
  CONSTRAINT `lms_coursepaymentgroup_course_id_e520a05f_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_coursepaymentgroup`
--

LOCK TABLES `lms_coursepaymentgroup` WRITE;
/*!40000 ALTER TABLE `lms_coursepaymentgroup` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_coursepaymentgroup` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_essay_question`
--

DROP TABLE IF EXISTS `lms_essay_question`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_essay_question` (
  `question_ptr_id` bigint(20) NOT NULL,
  `answer_type` varchar(20) NOT NULL,
  PRIMARY KEY (`question_ptr_id`),
  CONSTRAINT `lms_essay_question_question_ptr_id_55504aac_fk_lms_question_id` FOREIGN KEY (`question_ptr_id`) REFERENCES `lms_question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_essay_question`
--

LOCK TABLES `lms_essay_question` WRITE;
/*!40000 ALTER TABLE `lms_essay_question` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_essay_question` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_grade`
--

DROP TABLE IF EXISTS `lms_grade`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_grade` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `attendance` decimal(5,2) NOT NULL,
  `assignment` decimal(5,2) NOT NULL,
  `mid_exam` decimal(5,2) NOT NULL,
  `final_exam` decimal(5,2) NOT NULL,
  `total` decimal(5,2) NOT NULL,
  `grade` varchar(5) DEFAULT NULL,
  `comment` longtext DEFAULT NULL,
  `course_id` bigint(20) NOT NULL,
  `semester_id` bigint(20) NOT NULL,
  `student_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_grade_student_id_course_id_semester_id_9ce813bf_uniq` (`student_id`,`course_id`,`semester_id`),
  KEY `lms_grade_course_id_ba9d2efb_fk_lms_course_id` (`course_id`),
  KEY `lms_grade_semester_id_db41d3d2_fk_lms_semester_id` (`semester_id`),
  CONSTRAINT `lms_grade_course_id_ba9d2efb_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `lms_grade_semester_id_db41d3d2_fk_lms_semester_id` FOREIGN KEY (`semester_id`) REFERENCES `lms_semester` (`id`),
  CONSTRAINT `lms_grade_student_id_54acab62_fk_lms_lmsprofile_id` FOREIGN KEY (`student_id`) REFERENCES `lms_lmsprofile` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_grade`
--

LOCK TABLES `lms_grade` WRITE;
/*!40000 ALTER TABLE `lms_grade` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_grade` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_instructorrequest`
--

DROP TABLE IF EXISTS `lms_instructorrequest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_instructorrequest` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `reason` longtext NOT NULL,
  `qualifications` longtext NOT NULL,
  `cv` varchar(100) DEFAULT NULL,
  `status` varchar(10) NOT NULL,
  `admin_notes` longtext DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_instructorrequest_user_id_68e3e887_fk_auth_user_id` (`user_id`),
  CONSTRAINT `lms_instructorrequest_user_id_68e3e887_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_instructorrequest`
--

LOCK TABLES `lms_instructorrequest` WRITE;
/*!40000 ALTER TABLE `lms_instructorrequest` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_instructorrequest` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_lmsprofile`
--

DROP TABLE IF EXISTS `lms_lmsprofile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_lmsprofile` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `role` varchar(10) NOT NULL,
  `bio` longtext DEFAULT NULL,
  `profile_picture` varchar(100) DEFAULT NULL,
  `phone_number` varchar(15) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `legal_name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `lms_lmsprofile_user_id_3c0e715f_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_lmsprofile`
--

LOCK TABLES `lms_lmsprofile` WRITE;
/*!40000 ALTER TABLE `lms_lmsprofile` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_lmsprofile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_mcquestion`
--

DROP TABLE IF EXISTS `lms_mcquestion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_mcquestion` (
  `question_ptr_id` bigint(20) NOT NULL,
  `choice_order` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`question_ptr_id`),
  CONSTRAINT `lms_mcquestion_question_ptr_id_d7b2b6a5_fk_lms_question_id` FOREIGN KEY (`question_ptr_id`) REFERENCES `lms_question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_mcquestion`
--

LOCK TABLES `lms_mcquestion` WRITE;
/*!40000 ALTER TABLE `lms_mcquestion` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_mcquestion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_modulepayment`
--

DROP TABLE IF EXISTS `lms_modulepayment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_modulepayment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `mode` varchar(20) NOT NULL,
  `start_group` int(10) unsigned DEFAULT NULL CHECK (`start_group` >= 0),
  `end_group` int(10) unsigned DEFAULT NULL CHECK (`end_group` >= 0),
  `snippe_session_id` varchar(100) NOT NULL,
  `snippe_reference` varchar(100) NOT NULL,
  `webhook_event_id` varchar(100) NOT NULL,
  `failure_reason` longtext NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `status` varchar(20) NOT NULL,
  `checkout_url` varchar(200) NOT NULL,
  `payment_link_url` varchar(200) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  `payment_group_id` bigint(20) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_modulepayment_course_id_65301272_fk_lms_course_id` (`course_id`),
  KEY `lms_modulepayment_payment_group_id_542796a8_fk_lms_cours` (`payment_group_id`),
  KEY `lms_modulepayment_user_id_6c053ff0_fk_auth_user_id` (`user_id`),
  CONSTRAINT `lms_modulepayment_course_id_65301272_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `lms_modulepayment_payment_group_id_542796a8_fk_lms_cours` FOREIGN KEY (`payment_group_id`) REFERENCES `lms_coursepaymentgroup` (`id`),
  CONSTRAINT `lms_modulepayment_user_id_6c053ff0_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_modulepayment`
--

LOCK TABLES `lms_modulepayment` WRITE;
/*!40000 ALTER TABLE `lms_modulepayment` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_modulepayment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_moduleprogress`
--

DROP TABLE IF EXISTS `lms_moduleprogress`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_moduleprogress` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `content_completed` tinyint(1) NOT NULL,
  `assessment_passed` tinyint(1) NOT NULL,
  `best_score` decimal(5,2) NOT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `updated_at` datetime(6) NOT NULL,
  `best_quiz_taker_id` bigint(20) DEFAULT NULL,
  `module_id` bigint(20) NOT NULL,
  `student_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_moduleprogress_student_id_module_id_c85b8a0f_uniq` (`student_id`,`module_id`),
  KEY `lms_moduleprogress_best_quiz_taker_id_a241fcd7_fk_lms_quizt` (`best_quiz_taker_id`),
  KEY `lms_moduleprogress_module_id_503ef257_fk_lms_coursemodule_id` (`module_id`),
  CONSTRAINT `lms_moduleprogress_best_quiz_taker_id_a241fcd7_fk_lms_quizt` FOREIGN KEY (`best_quiz_taker_id`) REFERENCES `lms_quiztaker` (`id`),
  CONSTRAINT `lms_moduleprogress_module_id_503ef257_fk_lms_coursemodule_id` FOREIGN KEY (`module_id`) REFERENCES `lms_coursemodule` (`id`),
  CONSTRAINT `lms_moduleprogress_student_id_11594929_fk_lms_lmsprofile_id` FOREIGN KEY (`student_id`) REFERENCES `lms_lmsprofile` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_moduleprogress`
--

LOCK TABLES `lms_moduleprogress` WRITE;
/*!40000 ALTER TABLE `lms_moduleprogress` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_moduleprogress` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_paymentmethod`
--

DROP TABLE IF EXISTS `lms_paymentmethod`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_paymentmethod` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `instructions` longtext NOT NULL,
  `image` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `instructor_id` bigint(20) DEFAULT NULL,
  `payment_number` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_paymentmethod_instructor_id_802bd0dd_fk_lms_lmsprofile_id` (`instructor_id`),
  CONSTRAINT `lms_paymentmethod_instructor_id_802bd0dd_fk_lms_lmsprofile_id` FOREIGN KEY (`instructor_id`) REFERENCES `lms_lmsprofile` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_paymentmethod`
--

LOCK TABLES `lms_paymentmethod` WRITE;
/*!40000 ALTER TABLE `lms_paymentmethod` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_paymentmethod` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_program`
--

DROP TABLE IF EXISTS `lms_program`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_program` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(150) NOT NULL,
  `summary` longtext NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_program`
--

LOCK TABLES `lms_program` WRITE;
/*!40000 ALTER TABLE `lms_program` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_program` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_question`
--

DROP TABLE IF EXISTS `lms_question`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_question` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `figure` varchar(100) DEFAULT NULL,
  `content` longtext NOT NULL,
  `explanation` longtext NOT NULL,
  `order` int(11) NOT NULL,
  `quiz_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_question_quiz_id_f7fae637_fk_lms_quiz_id` (`quiz_id`),
  CONSTRAINT `lms_question_quiz_id_f7fae637_fk_lms_quiz_id` FOREIGN KEY (`quiz_id`) REFERENCES `lms_quiz` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_question`
--

LOCK TABLES `lms_question` WRITE;
/*!40000 ALTER TABLE `lms_question` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_question` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_quiz`
--

DROP TABLE IF EXISTS `lms_quiz`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_quiz` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `slug` varchar(255) NOT NULL,
  `description` longtext NOT NULL,
  `category` varchar(20) NOT NULL,
  `random_order` tinyint(1) NOT NULL,
  `answers_at_end` tinyint(1) NOT NULL,
  `exam_paper` tinyint(1) NOT NULL,
  `single_attempt` tinyint(1) NOT NULL,
  `pass_mark` smallint(6) NOT NULL,
  `draft` tinyint(1) NOT NULL,
  `due_date` datetime(6) DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  `module_id` bigint(20) DEFAULT NULL,
  `generated_for_id` bigint(20) DEFAULT NULL,
  `generation_completed_at` datetime(6) DEFAULT NULL,
  `generation_message` longtext NOT NULL,
  `generation_started_at` datetime(6) DEFAULT NULL,
  `generation_status` varchar(20) NOT NULL,
  `ai_generated` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `lms_quiz_course_id_b72840ad_fk_lms_course_id` (`course_id`),
  KEY `lms_quiz_module_id_d75cef7d_fk_lms_coursemodule_id` (`module_id`),
  KEY `lms_quiz_generated_for_id_aad252ba_fk_lms_lmsprofile_id` (`generated_for_id`),
  CONSTRAINT `lms_quiz_course_id_b72840ad_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `lms_quiz_generated_for_id_aad252ba_fk_lms_lmsprofile_id` FOREIGN KEY (`generated_for_id`) REFERENCES `lms_lmsprofile` (`id`),
  CONSTRAINT `lms_quiz_module_id_d75cef7d_fk_lms_coursemodule_id` FOREIGN KEY (`module_id`) REFERENCES `lms_coursemodule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_quiz`
--

LOCK TABLES `lms_quiz` WRITE;
/*!40000 ALTER TABLE `lms_quiz` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_quiz` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_quizgenerationjob`
--

DROP TABLE IF EXISTS `lms_quizgenerationjob`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_quizgenerationjob` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `force` tinyint(1) NOT NULL,
  `question_count` int(10) unsigned NOT NULL CHECK (`question_count` >= 0),
  `attempts` int(10) unsigned NOT NULL CHECK (`attempts` >= 0),
  `max_attempts` int(10) unsigned NOT NULL CHECK (`max_attempts` >= 0),
  `error` longtext DEFAULT NULL,
  `locked_at` datetime(6) DEFAULT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `module_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `lms_quizgenerationjob_module_id_8c5f98a9_fk_lms_coursemodule_id` (`module_id`),
  CONSTRAINT `lms_quizgenerationjob_module_id_8c5f98a9_fk_lms_coursemodule_id` FOREIGN KEY (`module_id`) REFERENCES `lms_coursemodule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_quizgenerationjob`
--

LOCK TABLES `lms_quizgenerationjob` WRITE;
/*!40000 ALTER TABLE `lms_quizgenerationjob` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_quizgenerationjob` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_quiztaker`
--

DROP TABLE IF EXISTS `lms_quiztaker`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_quiztaker` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `score` decimal(5,2) NOT NULL,
  `completed` tinyint(1) NOT NULL,
  `date_started` datetime(6) NOT NULL,
  `date_completed` datetime(6) DEFAULT NULL,
  `quiz_id` bigint(20) NOT NULL,
  `user_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_quiztaker_user_id_quiz_id_d3f5b629_uniq` (`user_id`,`quiz_id`),
  KEY `lms_quiztaker_quiz_id_0d4da23e_fk_lms_quiz_id` (`quiz_id`),
  CONSTRAINT `lms_quiztaker_quiz_id_0d4da23e_fk_lms_quiz_id` FOREIGN KEY (`quiz_id`) REFERENCES `lms_quiz` (`id`),
  CONSTRAINT `lms_quiztaker_user_id_1243a028_fk_lms_lmsprofile_id` FOREIGN KEY (`user_id`) REFERENCES `lms_lmsprofile` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_quiztaker`
--

LOCK TABLES `lms_quiztaker` WRITE;
/*!40000 ALTER TABLE `lms_quiztaker` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_quiztaker` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_semester`
--

DROP TABLE IF EXISTS `lms_semester`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_semester` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `year` int(11) NOT NULL,
  `semester` varchar(10) NOT NULL,
  `is_current_semester` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_semester_semester_year_21cd5cae_uniq` (`semester`,`year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_semester`
--

LOCK TABLES `lms_semester` WRITE;
/*!40000 ALTER TABLE `lms_semester` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_semester` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_sitesettings`
--

DROP TABLE IF EXISTS `lms_sitesettings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_sitesettings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `show_ads_before_free_courses` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `show_list_ads` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_sitesettings`
--

LOCK TABLES `lms_sitesettings` WRITE;
/*!40000 ALTER TABLE `lms_sitesettings` DISABLE KEYS */;
INSERT INTO `lms_sitesettings` VALUES
(1,1,'2026-07-31 17:49:16.025420','2026-07-31 17:49:16.025504',1);
/*!40000 ALTER TABLE `lms_sitesettings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_studentanswer`
--

DROP TABLE IF EXISTS `lms_studentanswer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_studentanswer` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `tf_answer` tinyint(1) DEFAULT NULL,
  `essay_text_answer` longtext DEFAULT NULL,
  `essay_file_answer` varchar(100) DEFAULT NULL,
  `is_correct` tinyint(1) NOT NULL,
  `mc_answer_id` bigint(20) DEFAULT NULL,
  `question_id` bigint(20) NOT NULL,
  `quiz_taker_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `lms_studentanswer_quiz_taker_id_question_id_e1cae295_uniq` (`quiz_taker_id`,`question_id`),
  KEY `lms_studentanswer_mc_answer_id_8104fe9e_fk_lms_choice_id` (`mc_answer_id`),
  KEY `lms_studentanswer_question_id_b081bd99_fk_lms_question_id` (`question_id`),
  CONSTRAINT `lms_studentanswer_mc_answer_id_8104fe9e_fk_lms_choice_id` FOREIGN KEY (`mc_answer_id`) REFERENCES `lms_choice` (`id`),
  CONSTRAINT `lms_studentanswer_question_id_b081bd99_fk_lms_question_id` FOREIGN KEY (`question_id`) REFERENCES `lms_question` (`id`),
  CONSTRAINT `lms_studentanswer_quiz_taker_id_a3aca66d_fk_lms_quiztaker_id` FOREIGN KEY (`quiz_taker_id`) REFERENCES `lms_quiztaker` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_studentanswer`
--

LOCK TABLES `lms_studentanswer` WRITE;
/*!40000 ALTER TABLE `lms_studentanswer` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_studentanswer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_studentcertificate`
--

DROP TABLE IF EXISTS `lms_studentcertificate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_studentcertificate` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `certificate_id` varchar(100) NOT NULL,
  `issued_at` datetime(6) NOT NULL,
  `expires_at` datetime(6) DEFAULT NULL,
  `is_valid` tinyint(1) NOT NULL,
  `course_id` bigint(20) NOT NULL,
  `student_id` int(11) NOT NULL,
  `template_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `certificate_id` (`certificate_id`),
  UNIQUE KEY `lms_studentcertificate_student_id_course_id_1e399b32_uniq` (`student_id`,`course_id`),
  KEY `lms_studentcertificate_course_id_c5b9eb81_fk_lms_course_id` (`course_id`),
  KEY `lms_studentcertifica_template_id_c229005b_fk_lms_certi` (`template_id`),
  CONSTRAINT `lms_studentcertifica_template_id_c229005b_fk_lms_certi` FOREIGN KEY (`template_id`) REFERENCES `lms_certificatetemplate` (`id`),
  CONSTRAINT `lms_studentcertificate_course_id_c5b9eb81_fk_lms_course_id` FOREIGN KEY (`course_id`) REFERENCES `lms_course` (`id`),
  CONSTRAINT `lms_studentcertificate_student_id_239c0a14_fk_auth_user_id` FOREIGN KEY (`student_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_studentcertificate`
--

LOCK TABLES `lms_studentcertificate` WRITE;
/*!40000 ALTER TABLE `lms_studentcertificate` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_studentcertificate` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lms_tf_question`
--

DROP TABLE IF EXISTS `lms_tf_question`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lms_tf_question` (
  `question_ptr_id` bigint(20) NOT NULL,
  `correct` tinyint(1) NOT NULL,
  PRIMARY KEY (`question_ptr_id`),
  CONSTRAINT `lms_tf_question_question_ptr_id_be9daf12_fk_lms_question_id` FOREIGN KEY (`question_ptr_id`) REFERENCES `lms_question` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lms_tf_question`
--

LOCK TABLES `lms_tf_question` WRITE;
/*!40000 ALTER TABLE `lms_tf_question` DISABLE KEYS */;
/*!40000 ALTER TABLE `lms_tf_question` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `talents_comment`
--

DROP TABLE IF EXISTS `talents_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `talents_comment` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `text` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  `talent_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `talents_comment_user_id_92e1e9de_fk_auth_user_id` (`user_id`),
  KEY `talents_comment_talent_id_9ccd69c2_fk_talents_talent_id` (`talent_id`),
  CONSTRAINT `talents_comment_talent_id_9ccd69c2_fk_talents_talent_id` FOREIGN KEY (`talent_id`) REFERENCES `talents_talent` (`id`),
  CONSTRAINT `talents_comment_user_id_92e1e9de_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `talents_comment`
--

LOCK TABLES `talents_comment` WRITE;
/*!40000 ALTER TABLE `talents_comment` DISABLE KEYS */;
/*!40000 ALTER TABLE `talents_comment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `talents_like`
--

DROP TABLE IF EXISTS `talents_like`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `talents_like` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `talent_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `talents_like_talent_id_user_id_dab7eb6f_uniq` (`talent_id`,`user_id`),
  KEY `talents_like_user_id_cc41a35a_fk_auth_user_id` (`user_id`),
  CONSTRAINT `talents_like_talent_id_563f17ad_fk_talents_talent_id` FOREIGN KEY (`talent_id`) REFERENCES `talents_talent` (`id`),
  CONSTRAINT `talents_like_user_id_cc41a35a_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `talents_like`
--

LOCK TABLES `talents_like` WRITE;
/*!40000 ALTER TABLE `talents_like` DISABLE KEYS */;
/*!40000 ALTER TABLE `talents_like` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `talents_talent`
--

DROP TABLE IF EXISTS `talents_talent`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `talents_talent` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` longtext NOT NULL,
  `category` varchar(50) NOT NULL,
  `media` varchar(100) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `talents_talent_user_id_1b43e4a8_fk_auth_user_id` (`user_id`),
  CONSTRAINT `talents_talent_user_id_1b43e4a8_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `talents_talent`
--

LOCK TABLES `talents_talent` WRITE;
/*!40000 ALTER TABLE `talents_talent` DISABLE KEYS */;
/*!40000 ALTER TABLE `talents_talent` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `webpush_group`
--

DROP TABLE IF EXISTS `webpush_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `webpush_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `webpush_group`
--

LOCK TABLES `webpush_group` WRITE;
/*!40000 ALTER TABLE `webpush_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `webpush_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `webpush_pushinformation`
--

DROP TABLE IF EXISTS `webpush_pushinformation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `webpush_pushinformation` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) DEFAULT NULL,
  `subscription_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `webpush_pushinformation_user_id_5e083b7f_fk_auth_user_id` (`user_id`),
  KEY `webpush_pushinformation_group_id_262dcc9a_fk` (`group_id`),
  KEY `webpush_pushinformation_subscription_id_7989aa34_fk` (`subscription_id`),
  CONSTRAINT `webpush_pushinformation_group_id_262dcc9a_fk` FOREIGN KEY (`group_id`) REFERENCES `webpush_group` (`id`),
  CONSTRAINT `webpush_pushinformation_subscription_id_7989aa34_fk` FOREIGN KEY (`subscription_id`) REFERENCES `webpush_subscriptioninfo` (`id`),
  CONSTRAINT `webpush_pushinformation_user_id_5e083b7f_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `webpush_pushinformation`
--

LOCK TABLES `webpush_pushinformation` WRITE;
/*!40000 ALTER TABLE `webpush_pushinformation` DISABLE KEYS */;
/*!40000 ALTER TABLE `webpush_pushinformation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `webpush_subscriptioninfo`
--

DROP TABLE IF EXISTS `webpush_subscriptioninfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `webpush_subscriptioninfo` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `browser` varchar(100) NOT NULL,
  `endpoint` varchar(500) NOT NULL,
  `auth` varchar(100) NOT NULL,
  `p256dh` varchar(100) NOT NULL,
  `user_agent` varchar(500) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `webpush_subscriptioninfo`
--

LOCK TABLES `webpush_subscriptioninfo` WRITE;
/*!40000 ALTER TABLE `webpush_subscriptioninfo` DISABLE KEYS */;
/*!40000 ALTER TABLE `webpush_subscriptioninfo` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-31 20:50:44
