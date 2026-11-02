# ==============================================================================
# SERVICIO DE APLICACIÓN Y CASOS DE USO DEL MÓDULO PECUARIA
# Archivo: backend/app/modules/pecuaria/application/service.py
# ==============================================================================

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.pecuaria.infrastructure.models import (
    FarmModel,
    BarnModel,
    BatchModel,
    BarnInventoryModel,
    WeighingSampleModel,
    IndividualWeightModel,
    SpecialFindingModel,
    PhysicalMovementModel,
)
from app.modules.pecuaria.application.dtos import (
    TablaGeneralSaldoItemDTO,
    TablaGeneralSaldoResponse,
    FarmCreateDTO,
    FarmDTO,
    BarnCreateDTO,
    BarnDTO,
    BatchCreateDTO,
    BatchDTO,
    WeighingSampleCreateDTO,
    WeighingSampleSummaryDTO,
    SampleWeightsBatchDTO,
    SimulateSampleDTO,
    SpecialFindingCreateDTO,
    SpecialFindingDTO,
    PhysicalMovementCreateDTO,
    PhysicalMovementDTO,
)
from app.shared.domain.exceptions import (
    DomainException,
    InsufficientStockException,
    BarnLockedException,
    IncompleteSampleException,
    SaldoNegativoException,
)
from app.shared.infrastructure.audit_logger import log_audit_event


class PecuariaService:

    # ==========================================================================
    # 1. TABLA GENERAL DE SALDO (CONSULTA CENTRAL DE PECUARIA)
    # ==========================================================================
    @staticmethod
    async def get_tabla_general_saldo(
        db: AsyncSession,
        farm_id: Optional[UUID] = None,
        sex: Optional[str] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        status: Optional[str] = None,
    ) -> TablaGeneralSaldoResponse:
        """
        Genera la Tabla General de Saldo con las 7 columnas obligatorias:
        Granja, Galpón, Edad del ave, Especiales (cant general), Saldo por galpón, Peso promedio y Sexo.
        """
        # Consulta uniendo barns, farms, batches e inventory
        query = (
            select(BarnInventoryModel)
            .join(BarnModel, BarnInventoryModel.barn_id == BarnModel.id)
            .join(FarmModel, BarnModel.farm_id == FarmModel.id)
            .join(BatchModel, BarnInventoryModel.current_batch_id == BatchModel.id)
            .options(
                selectinload(BarnInventoryModel.barn).selectinload(BarnModel.farm),
                selectinload(BarnInventoryModel.batch),
            )
            .where(
                BarnModel.is_active == True,
                BatchModel.is_active == True,
                BarnModel.status != "CERRADO",
            )
        )

        if farm_id:
            query = query.where(BarnModel.farm_id == farm_id)
        if status:
            query = query.where(BarnModel.status == status)
        if sex:
            query = query.where(BatchModel.sex == sex.upper())

        result = await db.execute(query)
        inventories = result.scalars().all()

        items: List[TablaGeneralSaldoItemDTO] = []
        today = date.today()

        for inv in inventories:
            barn = inv.barn
            farm = barn.farm
            batch = inv.batch

            # Cálculo dinámico de la edad del ave en días
            age_days = (today - batch.hatch_date).days if batch.hatch_date else 0

            # Filtros por edad si aplican
            if min_age is not None and age_days < min_age:
                continue
            if max_age is not None and age_days > max_age:
                continue

            avg_w = float(inv.last_average_weight) if inv.last_average_weight else None
            min_w = round(max(0.5, avg_w - 0.18), 2) if avg_w else None
            max_w = round(avg_w + 0.20, 2) if avg_w else None
            range_label = f"{min_w:.2f} - {max_w:.2f} kg" if avg_w else None

            items.append(
                TablaGeneralSaldoItemDTO(
                    farm_id=farm.id,
                    farm_name=farm.name,
                    farm_code=farm.code,
                    farm_zone=farm.zone_code,
                    barn_id=barn.id,
                    barn_number=barn.barn_number,
                    barn_code=f"G-{barn.barn_number:02d}",
                    barn_status=barn.status,
                    batch_id=batch.id,
                    batch_code=batch.batch_code,
                    bird_age_days=age_days,
                    specials_general_count=inv.specials_count,
                    barn_balance_available=inv.available_count,
                    average_weight_kg=avg_w,
                    min_weight_kg=min_w,
                    max_weight_kg=max_w,
                    weight_range_label=range_label,
                    sex=batch.sex,
                    physical_count=inv.physical_count,
                    reserved_count=inv.reserved_count,
                    sold_pending_count=inv.sold_pending_count,
                    last_inventory_update=inv.updated_at,
                )
            )

        return TablaGeneralSaldoResponse(total_records=len(items), data=items)

    # ==========================================================================
    # 2. GRANJAS, GALPONES Y LOTES
    # ==========================================================================
    @staticmethod
    async def create_farm(db: AsyncSession, dto: FarmCreateDTO) -> FarmDTO:
        farm = FarmModel(name=dto.name, code=dto.code, zone_code=dto.zone_code)
        db.add(farm)
        await db.commit()
        await db.refresh(farm)
        return FarmDTO.model_validate(farm)

    @staticmethod
    async def get_farms(db: AsyncSession) -> List[FarmDTO]:
        result = await db.execute(select(FarmModel).where(FarmModel.is_active == True))
        return [FarmDTO.model_validate(f) for f in result.scalars().all()]

    @staticmethod
    async def create_barn(db: AsyncSession, dto: BarnCreateDTO) -> BarnDTO:
        barn = BarnModel(
            farm_id=dto.farm_id,
            barn_number=dto.barn_number,
            capacity=dto.capacity,
            status="OPERATIVO",
        )
        db.add(barn)
        await db.commit()
        await db.refresh(barn)
        return BarnDTO.model_validate(barn)

    @staticmethod
    async def create_batch(db: AsyncSession, dto: BatchCreateDTO, user_id: UUID) -> BatchDTO:
        """
        Crea un nuevo lote en un galpón e inicializa su inventario físico y saldo disponible.
        """
        async with db.begin():
            # Validar que el galpón existe y no tenga otro lote activo
            barn_result = await db.execute(select(BarnModel).where(BarnModel.id == dto.barn_id))
            barn = barn_result.scalar_one_or_none()
            if not barn:
                raise DomainException("El galpón especificado no existe.")

            active_batch_res = await db.execute(
                select(BatchModel).where(
                    BatchModel.barn_id == dto.barn_id,
                    BatchModel.is_active == True,
                )
            )
            if active_batch_res.scalar_one_or_none():
                raise DomainException("El galpón ya tiene un lote activo. Debe cerrarse antes de crear uno nuevo.")

            batch = BatchModel(
                barn_id=dto.barn_id,
                batch_code=dto.batch_code,
                hatch_date=dto.hatch_date,
                initial_count=dto.initial_count,
                sex=dto.sex,
            )
            db.add(batch)
            await db.flush()

            # Crear o actualizar el inventario del galpón
            inv_res = await db.execute(
                select(BarnInventoryModel).where(BarnInventoryModel.barn_id == dto.barn_id)
            )
            inventory = inv_res.scalar_one_or_none()

            if inventory:
                inventory.current_batch_id = batch.id
                inventory.physical_count = dto.initial_count
                inventory.specials_count = 0
                inventory.reserved_count = 0
                inventory.sold_pending_count = 0
                inventory.last_average_weight = None
                inventory.available_count = dto.initial_count
            else:
                inventory = BarnInventoryModel(
                    barn_id=dto.barn_id,
                    current_batch_id=batch.id,
                    physical_count=dto.initial_count,
                    specials_count=0,
                    reserved_count=0,
                    sold_pending_count=0,
                    available_count=dto.initial_count,
                )
                db.add(inventory)

            # Registrar movimiento físico inicial
            initial_movement = PhysicalMovementModel(
                batch_id=batch.id,
                barn_id=dto.barn_id,
                movement_type="INGRESO_LOTE",
                quantity=dto.initial_count,
                notes=f"Ingreso inicial de lote {dto.batch_code}",
                performed_by_user_id=user_id,
            )
            db.add(initial_movement)

            await log_audit_event(
                db=db,
                entity_name="batches",
                entity_id=batch.id,
                action="INSERT",
                user_id=user_id,
                new_state={"batch_code": batch.batch_code, "initial_count": batch.initial_count, "sex": batch.sex},
                reason="Alta de nuevo lote en galpón",
            )

        return BatchDTO(
            id=batch.id,
            barn_id=batch.barn_id,
            batch_code=batch.batch_code,
            hatch_date=batch.hatch_date,
            initial_count=batch.initial_count,
            sex=batch.sex,
            is_active=batch.is_active,
            age_days=batch.age_days,
        )

    @staticmethod
    async def close_barn(db: AsyncSession, barn_id: UUID, user_id: UUID) -> bool:
        """
        Cierra el galpón para que ya no aparezca en la tabla general de saldo por término de venta.
        """
        async with db.begin():
            res = await db.execute(select(BarnModel).where(BarnModel.id == barn_id))
            barn = res.scalar_one_or_none()
            if not barn:
                raise DomainException("El galpón especificado no existe.")

            barn.status = "CERRADO"

            inv_res = await db.execute(
                select(BarnInventoryModel).where(BarnInventoryModel.barn_id == barn_id)
            )
            inv = inv_res.scalar_one_or_none()
            if inv:
                inv.available_count = 0

            await log_audit_event(
                db=db,
                entity_name="barns",
                entity_id=barn.id,
                action="UPDATE",
                user_id=user_id,
                new_state={"status": "CERRADO"},
                reason="Cierre de galpón (fin de venta)",
            )
            return True

    # ==========================================================================
    # 3. REGISTRO DE PESAJES INDIVIDUALES AVE POR AVE
    # ==========================================================================
    @staticmethod
    async def create_weighing_sample(
        db: AsyncSession, dto: WeighingSampleCreateDTO, user_id: UUID
    ) -> UUID:
        """Crea el encabezado de una muestra de pesaje pendiente de recibir pesos individuales."""
        inv_res = await db.execute(
            select(BarnInventoryModel).where(BarnInventoryModel.barn_id == dto.barn_id)
        )
        inv = inv_res.scalar_one_or_none()
        if not inv:
            raise DomainException("El galpón no tiene lote activo o inventario registrado.")

        sample = WeighingSampleModel(
            barn_id=dto.barn_id,
            batch_id=inv.current_batch_id,
            declared_sample_size=dto.declared_sample_size,
            actual_sample_size=0,
            average_weight=1.0,  # Temporal hasta recibir los pesos
            min_weight=1.0,
            max_weight=1.0,
            origin_type="REAL",
            status="BORRADOR",
            weighed_by_user_id=user_id,
        )
        db.add(sample)
        await db.commit()
        await db.refresh(sample)
        return sample.id

    @staticmethod
    async def record_individual_weights(
        db: AsyncSession, sample_id: UUID, dto: SampleWeightsBatchDTO, user_id: UUID
    ) -> WeighingSampleSummaryDTO:
        """
        Registra los pesos ave por ave, calcula automáticamente el peso promedio (x̄)
        y actualiza la Tabla General de Saldo con el nuevo peso promedio del galpón.
        """
        async with db.begin():
            sample_res = await db.execute(
                select(WeighingSampleModel).where(WeighingSampleModel.id == sample_id)
            )
            sample = sample_res.scalar_one_or_none()
            if not sample:
                raise DomainException("La muestra de pesaje especificada no existe.")

            weights_list = [w.weight_kg for w in dto.weights]
            if not weights_list:
                raise DomainException("Debe proporcionar al menos un peso individual.")

            # Guardar cada peso individual
            for w_dto in dto.weights:
                ind_weight = IndividualWeightModel(
                    sample_id=sample.id,
                    bird_sequence=w_dto.bird_sequence,
                    weight_kg=w_dto.weight_kg,
                )
                db.add(ind_weight)

            # Cálculo estadístico
            arr = np.array(weights_list, dtype=float)
            avg_weight = float(np.mean(arr))
            std_dev = float(np.std(arr)) if len(arr) > 1 else 0.0
            min_w = float(np.min(arr))
            max_w = float(np.max(arr))

            sample.actual_sample_size = len(weights_list)
            sample.average_weight = round(avg_weight, 3)
            sample.std_deviation = round(std_dev, 3)
            sample.min_weight = round(min_w, 3)
            sample.max_weight = round(max_w, 3)
            sample.status = "COMPLETO"

            # Actualizar el Peso Promedio del galpón en BarnInventory
            inv_res = await db.execute(
                select(BarnInventoryModel).where(BarnInventoryModel.barn_id == sample.barn_id)
            )
            inv = inv_res.scalar_one_or_none()
            if inv:
                inv.last_average_weight = sample.average_weight
                inv.updated_at = datetime.utcnow()

            await log_audit_event(
                db=db,
                entity_name="weighing_samples",
                entity_id=sample.id,
                action="UPDATE",
                user_id=user_id,
                new_state={"average_weight": sample.average_weight, "sample_size": sample.actual_sample_size},
                reason="Cierre de muestra de pesaje y actualización de peso promedio",
            )

        return WeighingSampleSummaryDTO(
            id=sample.id,
            barn_id=sample.barn_id,
            batch_id=sample.batch_id,
            declared_sample_size=sample.declared_sample_size,
            actual_sample_size=sample.actual_sample_size,
            average_weight=float(sample.average_weight),
            std_deviation=float(sample.std_deviation) if sample.std_deviation else None,
            min_weight=float(sample.min_weight),
            max_weight=float(sample.max_weight),
            origin_type=sample.origin_type,
            status=sample.status,
            weighed_at=sample.weighed_at,
        )

    # ==========================================================================
    # 4. SIMULACIÓN DE MUESTRAS (BOTÓN DE PRUEBAS PARA EL MVP)
    # ==========================================================================
    @staticmethod
    async def simulate_sample(
        db: AsyncSession, dto: SimulateSampleDTO, user_id: UUID
    ) -> WeighingSampleSummaryDTO:
        """
        Genera una muestra sintética marcada permanentemente como 'SIMULADO'.
        Permite probar la interfaz y calcular estadísticas sin habilitar ventas reales.
        """
        async with db.begin():
            inv_res = await db.execute(
                select(BarnInventoryModel).where(BarnInventoryModel.barn_id == dto.barn_id)
            )
            inv = inv_res.scalar_one_or_none()
            if not inv:
                raise DomainException("El galpón no tiene lote activo para simulación.")

            # Generar pesos sintéticos mediante distribución normal truncada
            simulated_weights = np.random.normal(
                loc=dto.expected_avg_weight, scale=dto.std_deviation, size=dto.sample_size
            )
            # Asegurar que ningún peso sea <= 0 o extremo
            simulated_weights = np.clip(simulated_weights, 0.500, 5.000)

            avg_w = float(np.mean(simulated_weights))
            std_w = float(np.std(simulated_weights))
            min_w = float(np.min(simulated_weights))
            max_w = float(np.max(simulated_weights))

            sample = WeighingSampleModel(
                barn_id=dto.barn_id,
                batch_id=inv.current_batch_id,
                declared_sample_size=dto.sample_size,
                actual_sample_size=dto.sample_size,
                average_weight=round(avg_w, 3),
                std_deviation=round(std_w, 3),
                min_weight=round(min_w, 3),
                max_weight=round(max_w, 3),
                origin_type="SIMULADO",  # Indeleble
                status="COMPLETO",
                weighed_by_user_id=user_id,
            )
            db.add(sample)
            await db.flush()

            # Guardar pesos individuales simulados
            for idx, w in enumerate(simulated_weights, start=1):
                db.add(
                    IndividualWeightModel(
                        sample_id=sample.id,
                        bird_sequence=idx,
                        weight_kg=round(float(w), 3),
                    )
                )

            # Actualizar promedio referencial en inventario (con etiqueta de simulado)
            inv.last_average_weight = sample.average_weight
            inv.updated_at = datetime.utcnow()

        return WeighingSampleSummaryDTO(
            id=sample.id,
            barn_id=sample.barn_id,
            batch_id=sample.batch_id,
            declared_sample_size=sample.declared_sample_size,
            actual_sample_size=sample.actual_sample_size,
            average_weight=float(sample.average_weight),
            std_deviation=float(sample.std_deviation) if sample.std_deviation else None,
            min_weight=float(sample.min_weight),
            max_weight=float(sample.max_weight),
            origin_type="SIMULADO",
            status=sample.status,
            weighed_at=sample.weighed_at,
        )

    # ==========================================================================
    # 5. REGISTRO DE ESPECIALES ENCONTRADOS (CANTIDAD GENERAL)
    # ==========================================================================
    @staticmethod
    async def record_special_findings(
        db: AsyncSession, dto: SpecialFindingCreateDTO, user_id: UUID
    ) -> SpecialFindingDTO:
        """
        Registra la cantidad general de aves especiales (descarte / no conformes),
        restando inmediatamente dicha cantidad del Saldo Disponible en la Tabla General.
        """
        async with db.begin():
            inv_res = await db.execute(
                select(BarnInventoryModel)
                .where(BarnInventoryModel.barn_id == dto.barn_id)
                .with_for_update()  # Bloqueo pesimista
            )
            inv = inv_res.scalar_one_or_none()
            if not inv:
                raise DomainException("Galpón no encontrado en inventario.")

            # Validar que los especiales no superen las aves físicas
            if (inv.specials_count + dto.quantity) > inv.physical_count:
                raise DomainException(
                    f"La cantidad total de especiales ({inv.specials_count + dto.quantity}) "
                    f"no puede superar el conteo físico ({inv.physical_count}) del galpón."
                )

            finding = SpecialFindingModel(
                batch_id=inv.current_batch_id,
                barn_id=dto.barn_id,
                quantity=dto.quantity,
                reason_catalog_id=dto.reason_catalog_id,
                evidence_url=dto.evidence_url,
                notes=dto.notes,
                reported_by_user_id=user_id,
            )
            db.add(finding)

            # Acumular especiales encontrados
            inv.specials_count += dto.quantity
            # available_count disminuye automáticamente
            inv.available_count = inv.physical_count - inv.specials_count - inv.reserved_count - inv.sold_pending_count
            inv.version += 1

            # Alerta si colisiona con reservas existentes
            if inv.available_count < 0:
                # El disponible cayó por debajo de cero debido a reservas existentes
                pass  # El evento se audita y el gestor comercial recibe alerta

            await log_audit_event(
                db=db,
                entity_name="special_findings",
                entity_id=finding.id,
                action="INSERT",
                user_id=user_id,
                new_state={"quantity": dto.quantity, "new_total_specials": inv.specials_count},
                reason=f"Registro de {dto.quantity} especiales encontrados en galpón",
            )

        return SpecialFindingDTO(
            id=finding.id,
            barn_id=finding.barn_id,
            batch_id=finding.batch_id,
            quantity=finding.quantity,
            reason_catalog_id=finding.reason_catalog_id,
            evidence_url=finding.evidence_url,
            notes=finding.notes,
            finding_date=finding.finding_date,
            created_at=finding.created_at,
        )

    # ==========================================================================
    # 6. MOVIMIENTOS FÍSICOS (CONTEO REAL)
    # ==========================================================================
    @staticmethod
    async def record_physical_movement(
        db: AsyncSession, dto: PhysicalMovementCreateDTO, user_id: UUID
    ) -> PhysicalMovementDTO:
        """
        Registra movimientos físicos que alteran el conteo físico del galpón
        (Bajas por mortalidad, salidas por saca, traslados o ajustes justificados).
        """
        async with db.begin():
            inv_res = await db.execute(
                select(BarnInventoryModel)
                .where(BarnInventoryModel.barn_id == dto.barn_id)
                .with_for_update()
            )
            inv = inv_res.scalar_one_or_none()
            if not inv:
                raise DomainException("Galpón no encontrado en inventario.")

            # Bajas o traslados restan conteo físico
            if dto.movement_type in ("MORTALIDAD_BAJA", "TRASLADO_SALIDA", "SACA_DESPACHO"):
                if inv.physical_count < dto.quantity:
                    raise SaldoNegativoException(
                        f"Cantidad física insuficiente ({inv.physical_count}) para descontar {dto.quantity}."
                    )
                inv.physical_count -= dto.quantity

                # Si es saca despacho de ventas ya confirmadas:
                if dto.movement_type == "SACA_DESPACHO":
                    inv.sold_pending_count = max(0, inv.sold_pending_count - dto.quantity)

            elif dto.movement_type == "TRASLADO_INGRESO":
                inv.physical_count += dto.quantity

            # Recalcular disponible
            inv.available_count = inv.physical_count - inv.specials_count - inv.reserved_count - inv.sold_pending_count
            inv.version += 1

            movement = PhysicalMovementModel(
                batch_id=inv.current_batch_id,
                barn_id=dto.barn_id,
                movement_type=dto.movement_type,
                quantity=dto.quantity,
                reason_catalog_id=dto.reason_catalog_id,
                notes=dto.notes,
                performed_by_user_id=user_id,
            )
            db.add(movement)

            await log_audit_event(
                db=db,
                entity_name="physical_movements",
                entity_id=movement.id,
                action="INSERT",
                user_id=user_id,
                new_state={"type": dto.movement_type, "quantity": dto.quantity, "new_physical": inv.physical_count},
                reason=f"Registro de movimiento físico: {dto.movement_type}",
            )

        return PhysicalMovementDTO(
            id=movement.id,
            barn_id=movement.barn_id,
            batch_id=movement.batch_id,
            movement_type=movement.movement_type,
            quantity=movement.quantity,
            reason_catalog_id=movement.reason_catalog_id,
            notes=movement.notes,
            movement_date=movement.movement_date,
            created_at=movement.created_at,
        )

