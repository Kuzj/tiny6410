BEGIN TRANSACTION;
CREATE TABLE `daqd_sensors` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT,
	`interface_id`	INTEGER NOT NULL,
	`enable`	INTEGER,
	`desc`	TEXT,
	`action_id`	INTEGER,
	`counter`	INTEGER DEFAULT 0,
	FOREIGN KEY(`interface_id`) REFERENCES daqd_interfaces(id),
	FOREIGN KEY(`action_id`) REFERENCES daqd_actions(id),
	FOREIGN KEY(`counter`) REFERENCES daqd_counters(id)
);
INSERT INTO `daqd_sensors` VALUES (1,'wire_pir_sensor',2,1,'Проводной датчик движения',1,0);
INSERT INTO `daqd_sensors` VALUES (2,'wireless_temp_sensor',3,1,'Беспроводной датчик температуры',1,0);
INSERT INTO `daqd_sensors` VALUES (3,'wireless_motion_sensor',3,0,'Беспроводной датчик движения',1,0);
INSERT INTO `daqd_sensors` VALUES (4,'wireless_motion_sensor',3,0,'Беспроводной датчик движения',1,0);
CREATE TABLE `daqd_interfaces` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`table_name`	TEXT NOT NULL,
	`desc`	TEXT
);
INSERT INTO `daqd_interfaces` VALUES (1,'daqd_interface_fs','Интерфейс для работы через файловую систему, используя функции Openscada.');
INSERT INTO `daqd_interfaces` VALUES (2,'daqd_interface_gpio','Интерфейс связи между демоном daqd.py и Openscada.');
INSERT INTO `daqd_interfaces` VALUES (3,'daqd_interface_cc1101','Интерфейс связи между cc1101 и Openscada.');
CREATE TABLE `daqd_interface_fs` (
	`sensor_id`	INTEGER NOT NULL,
	`path`	TEXT NOT NULL,
	`func`	TEXT,
	`prm_name`	TEXT,
	`schedule`	TEXT,
	`prm_fld`	TEXT,
	`desc`	TEXT,
	FOREIGN KEY(`sensor_id`) REFERENCES daqd_sensors(id)
);
CREATE TABLE `daqd_interface_gpio` (
	`sensor_id`	INTEGER NOT NULL,
	`gpio_number`	INTEGER NOT NULL,
	`edge_id`	INTEGER NOT NULL,
    `direction`  CHAR(3),
    `active`  INTEGER(1),
    FOREIGN KEY(`sensor_id`) REFERENCES daqd_sensors(id),
	FOREIGN KEY(`edge_id`) REFERENCES daqd_gpio_edge(id)
);
INSERT INTO `daqd_interface_gpio` VALUES (1,130,2,'in',1);
CREATE TABLE `daqd_gpio_edge` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`value`	TEXT NOT NULL
);
INSERT INTO `daqd_gpio_edge` VALUES (1,'none');
INSERT INTO `daqd_gpio_edge` VALUES (2,'rising');
INSERT INTO `daqd_gpio_edge` VALUES (3,'falling');
INSERT INTO `daqd_gpio_edge` VALUES (4,'both');
CREATE TABLE `daqd_actions` (
    `id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    `func`  TEXT NOT NULL,
    `desc`  TEXT
);
CREATE TABLE `daqd_events` (
    `sensor_id` INTEGER NOT NULL,
    `request`   TEXT,
    `action_id` INTEGER,
    `datetime`  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(`sensor_id`) REFERENCES daqd_sensors ( id ),
    FOREIGN KEY(`action_id`) REFERENCES daqd_actions ( id )
);
CREATE TABLE `daqd_counters` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	`sensor_id`	INTEGER NOT NULL,
	`value`	REAL NOT NULL DEFAULT 0,
	`step`	REAL NOT NULL DEFAULT 1,
	FOREIGN KEY(`sensor_id`) REFERENCES daqd_sensors(id)
);
COMMIT;
