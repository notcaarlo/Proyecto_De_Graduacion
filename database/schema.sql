CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) DEFAULT 'conductor',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vehiculos (
    id_vehiculo SERIAL PRIMARY KEY,
    marca VARCHAR(50),
    modelo VARCHAR(50),
    anio INT,
    placa VARCHAR(20),
    estado VARCHAR(20) DEFAULT 'activo',
    asignado_a INT REFERENCES usuarios(id_usuario)
);

CREATE TABLE alertas (
    id_alerta SERIAL PRIMARY KEY,
    id_usuario INT REFERENCES usuarios(id_usuario),
    id_vehiculo INT REFERENCES vehiculos(id_vehiculo),
    fecha DATE,
    hora TIME,
    duracion FLOAT,
    nota TEXT,
    nivel_somnolencia VARCHAR(20)
);