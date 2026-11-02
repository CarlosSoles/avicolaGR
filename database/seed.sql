-- ==============================================================================
-- DATOS INICIALES Y SEMILLA DEL SISTEMA - AVÍCOLA GR
-- Archivo: backend/database/seed.sql
-- Incluye: Catálogos, 23 Granjas, Galpones, Lotes, Clientes, Flota y Pedidos
-- ==============================================================================

-- 1. Catálogo Base de Motivos de Bloqueo
INSERT INTO public.catalogs (catalog_type, code, name, description) VALUES
('BLOQUEO_GALPON', 'VACIO_SANITARIO', 'Vacío Sanitario Preventivo', 'Período sanitario obligatorio entre camadas'),
('BLOQUEO_GALPON', 'BROTE_ENFERMEDAD', 'Sospecha o Brote de Enfermedad', 'Aislamiento epidemiológico'),
('BLOQUEO_GALPON', 'REPARACION_INFRAESTRUCTURA', 'Mantenimiento o Falla de Infraestructura', 'Reparación de comederos o bebederos'),
('BLOQUEO_GALPON', 'CALIDAD_AGUA', 'Falla en Suministro de Agua', 'Corte o contaminación hídrica temporal'),
('BLOQUEO_GALPON', 'DECISION_VETERINARIA', 'Cuarentena Médico-Veterinaria', 'Bloqueo preventivo por salud avícola')
ON CONFLICT (catalog_type, code) DO NOTHING;

-- 2. Catálogo de Motivos de Aves Especiales
INSERT INTO public.catalogs (catalog_type, code, name, description) VALUES
('MOTIVO_ESPECIAL', 'TARA_FISICA', 'Tara Física / Lesión de Pata', 'Ave con problema locomotor'),
('MOTIVO_ESPECIAL', 'DESCARTE_PESO', 'Descarte por Peso Fuera de Rango', 'Ave que no alcanza peso comercial'),
('MOTIVO_ESPECIAL', 'DEFECTO_PLUMA', 'Defecto en Plumaje / No Comercial', 'Ave no apta para mercado de primera'),
('MOTIVO_ESPECIAL', 'SINTOMA_RESPIRATORIO', 'Aislamiento Preventivo Sanitario', 'Ave en monitoreo respiratorio'),
('MOTIVO_ESPECIAL', 'OTRO', 'Otros Defectos Morfológicos', 'Otras incidencias zootécnicas')
ON CONFLICT (catalog_type, code) DO NOTHING;

-- 3. Parámetros Técnicos del Sistema
INSERT INTO public.technical_parameters (param_key, param_value, data_type, description) VALUES
('PESO_MINIMO_PLAUSIBLE_KG', '0.500', 'FLOAT', 'Límite inferior para validar pesos individuales en pesajes.'),
('PESO_MAXIMO_PLAUSIBLE_KG', '5.500', 'FLOAT', 'Límite superior para validar pesos individuales en pesajes.'),
('DIAS_VIGENCIA_PESAJE', '5', 'INT', 'Días máximos que un pesaje se considera fresco antes de emitir alerta de desactualizado.'),
('TAMANO_MUESTRA_MINIMO', '100', 'INT', 'Cantidad mínima de aves requerida para considerar válida una muestra de pesaje.'),
('EDAD_SACAL_CRITICA_DIAS', '45', 'INT', 'Edad biológica en la cual se prioriza saca inmediata para evitar merma y sobrecosto de alimento.')
ON CONFLICT (param_key) DO NOTHING;

-- 4. Las 23 Granjas Oficiales de Avícola GR
INSERT INTO public.farms (name, code, zone_code) VALUES
('Tradisa 1', 'TRAD1', 'ZONA_NORTE'),
('Tradisa II', 'TRAD2', 'ZONA_NORTE'),
('Pacifico 6', 'PACI6', 'ZONA_SUR'),
('San Jose 3', 'PAC67', 'ZONA_SUR'),
('San Jose 2', 'PACI7', 'ZONA_SUR'),
('Pacifico 1', 'PACI1', 'ZONA_SUR'),
('Pacifico 2', 'PACI2', 'ZONA_SUR'),
('San Jose 1', 'PACI5', 'ZONA_SUR'),
('Santa Isabel 2', 'SISA2', 'ZONA_CENTRO'),
('Semillero A', 'SEMIA', 'ZONA_NORTE'),
('Santa Isabel 3', 'SISA3', 'ZONA_CENTRO'),
('Santa Isabel 1', 'SISA1', 'ZONA_CENTRO'),
('Semillero B', 'SEMIB', 'ZONA_NORTE'),
('Nucleo 9', 'NUC-9', 'ZONA_CENTRO'),
('R4GB', 'R4G-B', 'ZONA_SUR'),
('Nucleo B', 'NUC-B', 'ZONA_CENTRO'),
('Esmeralda', 'ESMER', 'ZONA_NORTE'),
('R4GC', 'R4G-C', 'ZONA_SUR'),
('R4GA', 'R4G-A', 'ZONA_SUR'),
('Quebaga', 'QBAGA', 'ZONA_NORTE'),
('Puerto Mori 2', 'MORI2', 'ZONA_NORTE'),
('507', '507', 'ZONA_CENTRO'),
('Harco 2', 'HARC2', 'ZONA_SUR')
ON CONFLICT (code) DO NOTHING;

-- 5. Generación de 10 Galpones por cada Granja
DO $$
DECLARE
    f RECORD;
    b INT;
BEGIN
    FOR f IN SELECT id FROM public.farms LOOP
        FOR b IN 1..10 LOOP
            INSERT INTO public.barns (farm_id, barn_number, capacity, status)
            VALUES (f.id, b, 12000, 'OPERATIVO')
            ON CONFLICT (farm_id, barn_number) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;

-- 6. Flota Oficial de Vehículos de Transporte
INSERT INTO public.transport_vehicles (id, plate, driver_name, driver_phone, shift, capacity_birds, capacity_kg, status, current_zone) VALUES
('VH-001', 'B8X-710', 'Carlos Mendoza Vargas', '+51 984 123 456', 'Madrugada (02:00 - 08:00)', 4200, 10500.00, 'DISPONIBLE', 'CENTRO'),
('VH-002', 'C4P-920', 'Jorge Luis Ramos', '+51 992 456 789', 'Madrugada (02:00 - 08:00)', 3800, 9500.00, 'DISPONIBLE', 'NORTE'),
('VH-003', 'F1T-330', 'Miguel Ángel Quispe', '+51 971 789 123', 'Mañana (08:00 - 14:00)', 5000, 12500.00, 'DISPONIBLE', 'SUR'),
('VH-004', 'D9M-415', 'Walter Fernández Solís', '+51 965 321 654', 'Noche (20:00 - 02:00)', 4000, 10000.00, 'DISPONIBLE', 'METROPOLITANA'),
('VH-005', 'A2Z-808', 'Hernán Castillo Peña', '+51 954 654 987', 'Madrugada (02:00 - 08:00)', 4500, 11250.00, 'DISPONIBLE', 'CENTRO')
ON CONFLICT (id) DO UPDATE SET 
    driver_name = EXCLUDED.driver_name,
    driver_phone = EXCLUDED.driver_phone;

-- 7. Clientes Autorizados del Área Comercial
INSERT INTO public.clients (id, business_name, tax_id, zone_code, address, contact_phone, preferred_min_weight, preferred_max_weight, is_active) VALUES
('c1000000-0000-0000-0000-000000000001', 'Distribuidora Santa Anita S.A.C.', '20548963211', 'CENTRO', 'Av. Nicolás Ayllón 3800, Mercado Mayorista Santa Anita (Rampa 2)', '+51 987 654 321', 2.20, 2.50, TRUE),
('c1000000-0000-0000-0000-000000000002', 'Pollerías Norky''s Corp S.A.', '20100456789', 'METROPOLITANA', 'Av. Javier Prado Este 2890, San Borja, Lima', '+51 991 223 344', 2.15, 2.35, TRUE),
('c1000000-0000-0000-0000-000000000003', 'Supermercados Metro / Cencosud Perú', '20456123987', 'NORTE', 'Panamericana Norte Km 24.5, Centro de Distribución Los Olivos', '+51 976 543 210', 2.30, 2.60, TRUE),
('c1000000-0000-0000-0000-000000000004', 'Comercializadora Unicachi El Sol S.R.L.', '20601234567', 'NORTE', 'Mercado Mayorista Unicachi, Puesto 84 - Comas, Lima', '+51 954 321 876', 2.25, 2.45, TRUE),
('c1000000-0000-0000-0000-000000000005', 'Avícola Mayorista Villa Sur E.I.R.L.', '20512398745', 'SUR', 'Av. Pachacútec 1200, Villa El Salvador, Lima', '+51 945 678 123', 2.20, 2.55, TRUE)
ON CONFLICT (tax_id) DO NOTHING;

-- 8. Pedidos Iniciales de Prueba
INSERT INTO public.orders (
    order_number, client_id, zone_code, target_delivery_date, status,
    requested_quantity, allocated_quantity, min_weight_kg, max_weight_kg, sex_preference,
    suggested_farm_code, suggested_barn_code, assigned_farm_code, assigned_barn_code,
    delivery_address, notes
) VALUES
('PED-2026-0001', 'c1000000-0000-0000-0000-000000000001', 'CENTRO', CURRENT_DATE + 1, 'REGISTRADO',
 3500, 0, 2.20, 2.50, 'MACHO',
 'SISA1', 'G-01', NULL, NULL,
 'Mercado Mayorista Santa Anita, Rampa 2', 'Entrega primera hora de madrugada'),

('PED-2026-0002', 'c1000000-0000-0000-0000-000000000002', 'METROPOLITANA', CURRENT_DATE + 1, 'APROBADO_RESERVADO',
 2800, 2800, 2.15, 2.35, 'HEMBRA',
 'TRAD1', 'G-02', 'TRAD1', 'G-02',
 'Av. Javier Prado Este 2890, San Borja', 'Aprobado formalmente con galpón Tradisa 1 G-02'),

('PED-2026-0003', 'c1000000-0000-0000-0000-000000000003', 'NORTE', CURRENT_DATE + 2, 'CON_OBSERVACION',
 4200, 0, 2.30, 2.60, 'MACHO',
 'TRAD2', 'G-03', NULL, NULL,
 'Panamericana Norte Km 24.5', 'Observado: requiere confirmación de pesaje actualizado en granja')
ON CONFLICT (order_number) DO NOTHING;
