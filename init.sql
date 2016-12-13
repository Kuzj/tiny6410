BEGIN TRANSACTION;
CREATE TABLE `sensors` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT,
	`interface_id`	INTEGER NOT NULL,
	`enable`	INTEGER,
	`desc`	TEXT,
    `action_id`integer,
	FOREIGN KEY(`interface_id`) REFERENCES interfaces(id)
    FOREIGN KEY(`action_id`) REFERENCES actions (id)
);
INSERT INTO `sensors` VALUES (1,'wire_pir_sensor',2,1,'Проводной датчик движения');
CREATE TABLE `interfaces` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`table_name`	TEXT NOT NULL,
	`desc`	TEXT
);
INSERT INTO `interfaces` VALUES (1,'interface_fs','Интерфейс для работы через файловую систему, используя функции Openscada.');
INSERT INTO `interfaces` VALUES (2,'interface_daqd_gpio','Интерфейс связи между демоном daqd.py и Openscada.');
INSERT INTO `interfaces` VALUES (3,'interface_daqd_cc1101','Интерфейс связи между cc1101 и Openscada.');
CREATE TABLE `interface_fs` (
	`sensor_id`	INTEGER NOT NULL,
	`path`	TEXT NOT NULL,
	`func`	TEXT,
	`prm_name`	TEXT,
	`schedule`	TEXT,
	`prm_fld`	TEXT,
	`desc`	TEXT,
	FOREIGN KEY(`sensor_id`) REFERENCES sensors(id)
);
CREATE TABLE `interface_daqd_gpio` (
	`sensor_id`	INTEGER NOT NULL,
	`gpio_number`	INTEGER NOT NULL,
	`edge_id`	INTEGER NOT NULL,
    `direction`  CHAR(3),
    `active`  INTEGER(1),
    FOREIGN KEY(`sensor_id`) REFERENCES sensors(id),
	FOREIGN KEY(`edge_id`) REFERENCES gpio_edge(id)
);
INSERT INTO `interface_daqd_gpio` VALUES (1,130,2,'in',1);
CREATE TABLE `gpio_edge` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`value`	TEXT NOT NULL
);
INSERT INTO `gpio_edge` VALUES (1,'none');
INSERT INTO `gpio_edge` VALUES (2,'rising');
INSERT INTO `gpio_edge` VALUES (3,'falling');
INSERT INTO `gpio_edge` VALUES (4,'both');
CREATE TABLE `actions` (
    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    `func`  TEXT NOT NULL,
    `desc`  TEXT
);
CREATE TABLE `events` (
    `sensor_id` INTEGER NOT NULL,
    `request`   TEXT,
    `action_id` INTEGER,
    `datetime`  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(`sensor_id`) REFERENCES sensors ( id ),
    FOREIGN KEY(`action_id`) REFERENCES actions ( id )
);
COMMIT;
