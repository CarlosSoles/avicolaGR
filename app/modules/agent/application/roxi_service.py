# ==============================================================================
# SERVICIO DE APLICACIÓN DEL AGENTE ROXI
# Archivo: backend/app/modules/agent/application/roxi_service.py
# ==============================================================================

import re
import time
import unicodedata
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent.domain.schemas import (
    RoxiRecommendRequest,
    RoxiAllocationResponse,
    RoxiChatRequest,
    RoxiChatResponse,
)
from app.modules.agent.infrastructure.distances import (
    get_farm_distance_km,
    distance_to_delivery_point,
)
from app.modules.agent.infrastructure.gemini_client import RoxiGeminiClient
from app.modules.pecuaria.application.service import PecuariaService
from app.modules.comercial.application.service import ComercialService


class RoxiAgentService:
    """Servicio coordinador del agente inteligente ROXI."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.gemini_client = RoxiGeminiClient()

    async def _get_live_barn_inventory(self) -> List[Dict[str, Any]]:
        """
        Recupera el inventario en vivo desde la base de datos PostgreSQL de Supabase
        a través de la Tabla General de Saldo de Pecuaria.
        """
        if self.db:
            try:
                saldo_res = await PecuariaService.get_tabla_general_saldo(self.db)
                if saldo_res and saldo_res.data:
                    live_list = []
                    for item in saldo_res.data:
                        live_list.append({
                            "farm_code": item.farm_code,
                            "farm_name": item.farm_name,
                            "barn_code": item.barn_code,
                            "age_days": float(item.bird_age_days),
                            "available_birds": int(item.barn_balance_available),
                            "current_weight": float(item.average_weight_kg) if item.average_weight_kg else 2.40,
                            "sex": item.sex.upper() if item.sex else "INDISTINTO",
                            "status": item.barn_status,
                        })
                    if live_list:
                        return live_list
            except Exception as e:
                print(f"[ROXI] Error leyendo inventario en vivo de galpones: {e}")

        return []

    async def _get_farm_coordinates(self) -> Dict[str, tuple]:
        """Coordenadas reales de las granjas (para calcular cercanía al punto de entrega)."""
        if not self.db:
            return {}
        try:
            from sqlalchemy import text as sql_text

            res = await self.db.execute(
                sql_text("""
                    SELECT UPPER(code), latitude, longitude
                    FROM public.farms
                    WHERE is_active = TRUE AND latitude IS NOT NULL AND longitude IS NOT NULL
                """)
            )
            return {
                row[0]: (float(row[1]), float(row[2]))
                for row in res.fetchall()
            }
        except Exception as e:
            print(f"[ROXI] No se pudieron leer coordenadas de granjas: {e}")
            return {}

    async def _resolve_delivery_coords(self, req: RoxiRecommendRequest) -> Optional[tuple]:
        """
        Coordenadas del punto de entrega, con respaldo en el pedido y en la ficha del cliente
        cuando la solicitud no las trae (pedidos antiguos o creados sin coordenadas).
        """
        if req.delivery_latitude is not None and req.delivery_longitude is not None:
            return (req.delivery_latitude, req.delivery_longitude)

        if not self.db or not req.order_id:
            return None

        try:
            from sqlalchemy import text as sql_text

            order = await ComercialService.get_order_by_id(req.order_id, db=self.db)
            if order.delivery_latitude is not None and order.delivery_longitude is not None:
                return (order.delivery_latitude, order.delivery_longitude)

            if order.client_id:
                row = (await self.db.execute(
                    sql_text("""
                        SELECT latitude, longitude FROM public.clients
                        WHERE id = CAST(:cid AS uuid)
                          AND latitude IS NOT NULL AND longitude IS NOT NULL
                    """),
                    {"cid": str(order.client_id)},
                )).first()
                if row:
                    return (float(row[0]), float(row[1]))
        except Exception as e:
            print(f"[ROXI] No se pudieron resolver coordenadas del pedido: {e}")

        return None

    async def recommend_barn(self, req: RoxiRecommendRequest) -> RoxiAllocationResponse:
        """
        Calcula y recomienda el galpón óptimo para una solicitud comercial dada.
        Aplica arquitectura híbrida: Filtro Rígido en Python + Razonamiento de Gemini Flash.
        """
        start_time = time.time()
        live_inventory = await self._get_live_barn_inventory()

        target_sex = (req.sex or "Indistinto").upper().strip()
        min_w = req.min_weight
        max_w = req.max_weight
        zone = (req.zone_code or "CENTRO").upper().strip()

        # Punto de entrega: solicitud → pedido → ficha del cliente
        delivery_coords = await self._resolve_delivery_coords(req)
        farm_coords = await self._get_farm_coordinates()

        # ======================================================================
        # FASE 1: FILTRO RÍGIDO DETERMINISTA (HARD CONSTRAINTS)
        # ======================================================================
        candidates = []
        for barn in live_inventory:
            # 1. Filtro de estado
            if barn.get("status") in ("CERRADO", "CUARENTENA", "MANTENIMIENTO"):
                continue

            # 2. Filtro de saldo disponible
            if barn.get("available_birds", 0) <= 0:
                continue

            # 3. Filtro estricto de sexo
            barn_sex = barn.get("sex", "INDISTINTO").upper()
            if target_sex != "INDISTINTO" and barn_sex != "INDISTINTO" and barn_sex != target_sex:
                continue

            # 4. Filtro de tolerancia de peso (+- 0.18 kg)
            b_weight = barn.get("current_weight", 2.40)
            if b_weight < (min_w - 0.18) or b_weight > (max_w + 0.18):
                continue

            # 5. Distancia real granja → punto de entrega (coordenadas si existen)
            dist_km, dist_source = distance_to_delivery_point(
                farm_coords.get((barn["farm_code"] or "").upper()),
                delivery_coords,
                barn["farm_code"],
                zone,
            )

            candidates.append({
                "farm_code": barn["farm_code"],
                "farm_name": barn["farm_name"],
                "barn_code": barn["barn_code"],
                "current_age_days": barn["age_days"],
                "current_weight_kg": b_weight,
                "available_balance": barn["available_birds"],
                "sex": barn_sex,
                "distance_km": dist_km,
                "distance_source": dist_source,
            })

        # Si ningún galpón pasa el filtro rígido con tolerancia estricta,
        # se flexibiliza la ventana para no dejar la respuesta vacía
        if not candidates:
            for barn in live_inventory:
                if barn.get("available_birds", 0) > 0:
                    dist_km, dist_source = distance_to_delivery_point(
                        farm_coords.get((barn["farm_code"] or "").upper()),
                        delivery_coords,
                        barn["farm_code"],
                        zone,
                    )
                    candidates.append({
                        "farm_code": barn["farm_code"],
                        "farm_name": barn["farm_name"],
                        "barn_code": barn["barn_code"],
                        "current_age_days": barn.get("age_days", 42.0),
                        "current_weight_kg": barn.get("current_weight", 2.40),
                        "available_balance": barn.get("available_birds", 5000),
                        "sex": barn.get("sex", "INDISTINTO"),
                        "distance_km": dist_km,
                        "distance_source": dist_source,
                    })

        if not candidates:
            raise HTTPException(
                status_code=404,
                detail="No hay galpones operativos con saldo disponible en la base de datos.",
            )

        # Pre-evaluación multicriterio: pondera edad (40), distancia real al cliente (30),
        # calibre de peso (20) y saldo disponible (10), evitando que un solo criterio domine al 100%.
        distances = [c["distance_km"] for c in candidates] or [0.0]
        min_d, max_d = min(distances), max(distances)
        scored_candidates = []
        for c in candidates:
            total_pts, _ = self.gemini_client._score_candidate(
                c, req.quantity_birds, min_w, max_w, min_d, max_d
            )
            scored_candidates.append((total_pts, c))

        scored_candidates.sort(key=lambda item: (-item[0], item[1]["distance_km"], -item[1]["current_age_days"]))

        # Garantizar diversidad de granjas en los candidatos enviados a ROXI (máx. 2 galpones por granja)
        top_candidates = []
        per_farm_count: Dict[str, int] = {}
        for _, c in scored_candidates:
            fcode = (c["farm_code"] or "").upper()
            if per_farm_count.get(fcode, 0) >= 2:
                continue
            per_farm_count[fcode] = per_farm_count.get(fcode, 0) + 1
            top_candidates.append(c)
            if len(top_candidates) >= 8:
                break

        if len(top_candidates) < 8:
            seen = {(c["farm_code"], c["barn_code"]) for c in top_candidates}
            for _, c in scored_candidates:
                if (c["farm_code"], c["barn_code"]) not in seen:
                    top_candidates.append(c)
                    seen.add((c["farm_code"], c["barn_code"]))
                if len(top_candidates) >= 8:
                    break

        # ======================================================================
        # FASE 2: INFERENCIA DE ROXI (GEMINI FLASH CON STRUCTURED OUTPUTS)
        # ======================================================================
        order_dict = req.model_dump()
        response = await self.gemini_client.generate_allocation(
            order_request=order_dict,
            candidates=top_candidates,
            user_role=req.user_role or "vendedor",
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        response.execution_time_ms = elapsed_ms
        return response

    async def reassign_order(self, order_id: str, reason: str = "Ajuste operativo") -> RoxiAllocationResponse:
        """
        Reasigna un pedido existente cuando el galpón reservado sufre un imprevisto
        (descartes, mortandad o sobreventa).
        """
        try:
            order = await ComercialService.get_order_by_id(order_id, db=self.db)
        except Exception as exc:
            raise ValueError(f"No se encontró el pedido con ID {order_id}") from exc

        delivery_date_str = str(order.target_delivery_date)

        req = RoxiRecommendRequest(
            order_id=order.id,
            client_name=order.client_name,
            quantity_birds=order.requested_quantity,
            sex=order.sex_preference or "INDISTINTO",
            min_weight=order.min_weight_kg,
            max_weight=order.max_weight_kg,
            zone_code=order.zone_code,
            delivery_address=order.delivery_address,
            delivery_latitude=order.delivery_latitude,
            delivery_longitude=order.delivery_longitude,
            scheduled_date=delivery_date_str,
            user_role="gestor_comercial",
        )

        res = await self.recommend_barn(req)
        res.gestor_technical_notes = f"[REASIGNACIÓN ACTIVADA]: {reason}. {res.gestor_technical_notes}"
        return res

    @staticmethod
    def _normalize_search_text(text: str) -> str:
        if not text:
            return ""
        nfkd = unicodedata.normalize("NFKD", text)
        no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
        lowered = no_accents.lower()
        lowered = re.sub(r"\b(balpon|calpon|galpones)\b", "galpon", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    @classmethod
    def _extract_barn_number(cls, normalized_query: str) -> Optional[int]:
        patterns = [
            r"\bg[-\s]*0*(\d{1,2})\b",
            r"\bgalpon\s*(?:numero|nro|n°|#|)?\s*0*(\d{1,2})\b",
        ]
        for pat in patterns:
            m = re.search(pat, normalized_query)
            if m:
                return int(m.group(1))
        return None

    async def _build_operational_snapshot(
        self,
        order_id: Optional[str] = None,
        order_context: Optional[Dict[str, Any]] = None,
        user_role: str = "gestor_comercial",
        query_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Construye un resumen compacto de KPIs reales, pedidos pendientes, galpones
        críticos y coincidencia específica de la consulta desde BD.
        """
        snapshot: Dict[str, Any] = {
            "pedidos_resumen": {
                "total_activos": 0,
                "preprogramados": 0,
                "con_observacion": 0,
                "pendientes_completar_granja": 0,
                "listos_para_programar": 0,
                "programados": 0,
                "programados_con_camion": 0,
                "confirmados": 0,
                "despachados": 0,
                "terminados": 0,
                "sin_camion": 0,
                "sin_aris_con_camion": 0,
                "aves_activas_total": 0,
            },
            "saldos_resumen": {
                "galpones_operativos": 0,
                "aves_disponibles_total": 0,
                "galpones_criticos_45d_count": 0,
                "galpones_criticos_45d": [],
            },
            "pedidos_pendientes_top": [],
            "pedido_en_foco": None,
            "consulta_especifica": None,
        }

        norm_query = self._normalize_search_text(query_text or "")
        orders: List[Any] = []

        if self.db is not None:
            try:
                orders = await ComercialService.get_orders(
                    db=self.db,
                    exclude_drafts=True,
                )
                active_orders = [o for o in orders if o.status != "CANCELADO" and o.status != "BORRADOR"]
                resumen = snapshot["pedidos_resumen"]
                resumen["total_activos"] = len(active_orders)

                pending_list = []
                focus_order = None

                for o in active_orders:
                    qty = int(o.allocated_quantity or o.requested_quantity or 0)
                    resumen["aves_activas_total"] += qty

                    if order_id and o.id == order_id:
                        focus_order = o
                    elif not focus_order and norm_query:
                        ord_num = self._normalize_search_text(getattr(o, "order_number", "") or "")
                        cli_name = self._normalize_search_text(getattr(o, "client_name", "") or "")
                        if (ord_num and ord_num in norm_query) or (cli_name and len(cli_name) >= 4 and cli_name in norm_query):
                            focus_order = o

                    if o.status == "CON_OBSERVACION":
                        resumen["con_observacion"] += 1
                    elif o.status == "REGISTRADO":
                        resumen["preprogramados"] += 1

                    if o.status in ("REGISTRADO", "CON_OBSERVACION"):
                        if o.suggested_farm_code and o.suggested_barn_code:
                            resumen["listos_para_programar"] += 1
                        else:
                            resumen["pendientes_completar_granja"] += 1
                        pending_list.append({
                            "order_id": o.id,
                            "order_number": o.order_number,
                            "client_name": o.client_name,
                            "zone_code": o.zone_code,
                            "requested_quantity": o.requested_quantity,
                            "target_delivery_date": str(o.target_delivery_date)[:10],
                            "granja_sugerida": o.suggested_farm_code,
                            "galpon_sugerido": o.suggested_barn_code,
                        })
                    elif o.status == "APROBADO_RESERVADO":
                        if o.dispatch_phase == "ENTREGADO_CONFORME":
                            resumen["terminados"] += 1
                        elif o.dispatch_phase == "EN_TRANSITO":
                            resumen["despachados"] += 1
                        elif o.dispatch_phase == "EN_GRANJA_CARGANDO":
                            resumen["confirmados"] += 1
                        elif o.transport_assigned:
                            resumen["programados_con_camion"] += 1
                        else:
                            resumen["programados"] += 1
                            resumen["sin_camion"] += 1

                        if o.transport_assigned and not o.codigo_aris and o.dispatch_phase != "ENTREGADO_CONFORME":
                            resumen["sin_aris_con_camion"] += 1
                    elif o.status == "DESPACHADO":
                        if o.dispatch_phase == "ENTREGADO_CONFORME":
                            resumen["terminados"] += 1
                        else:
                            resumen["despachados"] += 1

                snapshot["pedidos_pendientes_top"] = pending_list[:5]

                if focus_order is None and active_orders:
                    # Priorizar un pedido pendiente de programar si existe
                    pre = [o for o in active_orders if o.status in ("REGISTRADO", "CON_OBSERVACION")]
                    focus_order = pre[0] if pre else active_orders[0]

                if focus_order is not None:
                    try:
                        rec_req = RoxiRecommendRequest(
                            order_id=focus_order.id,
                            client_name=focus_order.client_name,
                            quantity_birds=max(1, int(focus_order.requested_quantity or 1000)),
                            sex=focus_order.sex_preference or "INDISTINTO",
                            min_weight=float(focus_order.min_weight_kg or 2.2),
                            max_weight=float(focus_order.max_weight_kg or 2.8),
                            zone_code=focus_order.zone_code or "METROPOLITANA",
                            delivery_address=focus_order.delivery_address,
                            delivery_latitude=focus_order.delivery_latitude,
                            delivery_longitude=focus_order.delivery_longitude,
                            scheduled_date=str(focus_order.target_delivery_date)[:10],
                            user_role=user_role,
                        )
                        rec = await self.recommend_barn(rec_req)
                        snapshot["pedido_en_foco"] = {
                            "order_id": focus_order.id,
                            "order_number": focus_order.order_number,
                            "client_name": focus_order.client_name,
                            "requested_quantity": focus_order.requested_quantity,
                            "status": focus_order.status,
                            "recomendacion": {
                                "farm_code": rec.recommended_barn.farm_code,
                                "farm_name": rec.recommended_barn.farm_name,
                                "barn_code": rec.recommended_barn.barn_code,
                                "age_days": rec.recommended_barn.current_age_days,
                                "available_balance": rec.recommended_barn.available_balance,
                                "distance_km": rec.recommended_barn.distance_km,
                                "score_total": rec.recommended_barn.score_total,
                                "split_enabled": rec.split_recommendation.enabled,
                            },
                        }
                    except Exception as e:
                        print(f"[ROXI] Error en recomendación de pedido en foco: {e}")
                        try:
                            await self.db.rollback()
                        except Exception:
                            pass
                elif norm_query:
                    try:
                        from sqlalchemy import text as sql_text

                        cli_rows = (await self.db.execute(
                            sql_text("""
                                SELECT business_name, zone_code, address, latitude, longitude
                                FROM public.clients
                                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                            """)
                        )).fetchall()
                        matched_client = None
                        for row in cli_rows:
                            cname_norm = self._normalize_search_text(row[0] or "")
                            if cname_norm and len(cname_norm) >= 4 and cname_norm in norm_query:
                                matched_client = row
                                break
                        if matched_client:
                            rec_req = RoxiRecommendRequest(
                                client_name=matched_client[0],
                                quantity_birds=2000,
                                sex="INDISTINTO",
                                min_weight=2.2,
                                max_weight=2.8,
                                zone_code=matched_client[1] or "METROPOLITANA",
                                delivery_address=matched_client[2],
                                delivery_latitude=float(matched_client[3]),
                                delivery_longitude=float(matched_client[4]),
                                user_role=user_role,
                            )
                            rec = await self.recommend_barn(rec_req)
                            snapshot["pedido_en_foco"] = {
                                "order_id": None,
                                "order_number": "CONSULTA_CLIENTE",
                                "client_name": matched_client[0],
                                "requested_quantity": 2000,
                                "status": "COTIZACION",
                                "recomendacion": {
                                    "farm_code": rec.recommended_barn.farm_code,
                                    "farm_name": rec.recommended_barn.farm_name,
                                    "barn_code": rec.recommended_barn.barn_code,
                                    "age_days": rec.recommended_barn.current_age_days,
                                    "available_balance": rec.recommended_barn.available_balance,
                                    "distance_km": rec.recommended_barn.distance_km,
                                    "score_total": rec.recommended_barn.score_total,
                                    "split_enabled": rec.split_recommendation.enabled,
                                },
                            }
                    except Exception as e:
                        print(f"[ROXI] Error resolviendo cliente en consulta: {e}")
                        try:
                            await self.db.rollback()
                        except Exception:
                            pass
            except Exception as e:
                print(f"[ROXI] Error leyendo pedidos en snapshot: {e}")
                try:
                    await self.db.rollback()
                except Exception:
                    pass

            try:
                saldo_res = await PecuariaService.get_tabla_general_saldo(self.db)
                saldos = saldo_res.data if saldo_res and getattr(saldo_res, "data", None) else []
                open_barns = [
                    b for b in saldos
                    if not getattr(b, "is_closed", False)
                    and str(getattr(b, "barn_status", "")).upper() != "CERRADO"
                    and (getattr(b, "barn_balance_available", 0) or 0) > 0
                ]
                saldos_res = snapshot["saldos_resumen"]
                saldos_res["galpones_operativos"] = len(open_barns)
                saldos_res["aves_disponibles_total"] = sum(
                    int(getattr(b, "barn_balance_available", 0) or 0) for b in open_barns
                )

                criticos = sorted(
                    [b for b in open_barns if (getattr(b, "bird_age_days", 0) or 0) >= 45],
                    key=lambda b: -(getattr(b, "bird_age_days", 0) or 0),
                )
                saldos_res["galpones_criticos_45d_count"] = len(criticos)
                saldos_res["galpones_criticos_45d"] = [
                    {
                        "farm_code": b.farm_code,
                        "farm_name": b.farm_name,
                        "barn_code": b.barn_code,
                        "age_days": round(float(b.bird_age_days or 0), 1),
                        "available_birds": int(b.barn_balance_available or 0),
                        "avg_weight_kg": round(float(b.average_weight_kg or 0), 2)
                        if getattr(b, "average_weight_kg", None)
                        else None,
                    }
                    for b in criticos[:5]
                ]

                # Resolver consulta específica por granja/galpón si el usuario preguntó por uno puntual
                if norm_query and saldos:
                    target_barn_num = self._extract_barn_number(norm_query)
                    farm_matches = []
                    for b in saldos:
                        f_code = self._normalize_search_text(getattr(b, "farm_code", "") or "")
                        f_name = self._normalize_search_text(getattr(b, "farm_name", "") or "")
                        if (f_code and len(f_code) >= 3 and f_code in norm_query) or (
                            f_name and len(f_name) >= 4 and f_name in norm_query
                        ):
                            farm_matches.append(b)

                    if farm_matches:
                        if target_barn_num is not None:
                            exact_barns = [
                                b for b in farm_matches if getattr(b, "barn_number", None) == target_barn_num
                            ]
                            if exact_barns:
                                b = exact_barns[0]
                                snapshot["consulta_especifica"] = {
                                    "tipo": "galpon",
                                    "farm_code": b.farm_code,
                                    "farm_name": b.farm_name,
                                    "barn_code": b.barn_code,
                                    "barn_status": str(getattr(b, "barn_status", "")),
                                    "available_birds": int(getattr(b, "barn_balance_available", 0) or 0),
                                    "age_days": round(float(getattr(b, "bird_age_days", 0) or 0), 1),
                                    "avg_weight_kg": round(float(b.average_weight_kg), 2)
                                    if getattr(b, "average_weight_kg", None)
                                    else None,
                                    "sex": getattr(b, "sex", None),
                                }
                            else:
                                f0 = farm_matches[0]
                                snapshot["consulta_especifica"] = {
                                    "tipo": "galpon_no_encontrado",
                                    "farm_code": f0.farm_code,
                                    "farm_name": f0.farm_name,
                                    "barn_code": f"G-{target_barn_num:02d}",
                                    "galpones_disponibles": [
                                        {
                                            "barn_code": x.barn_code,
                                            "available_birds": int(getattr(x, "barn_balance_available", 0) or 0),
                                            "age_days": round(float(getattr(x, "bird_age_days", 0) or 0), 1),
                                        }
                                        for x in farm_matches[:6]
                                    ],
                                }
                        else:
                            f0 = farm_matches[0]
                            snapshot["consulta_especifica"] = {
                                "tipo": "granja",
                                "farm_code": f0.farm_code,
                                "farm_name": f0.farm_name,
                                "galpones": [
                                    {
                                        "barn_code": x.barn_code,
                                        "barn_status": str(getattr(x, "barn_status", "")),
                                        "available_birds": int(getattr(x, "barn_balance_available", 0) or 0),
                                        "age_days": round(float(getattr(x, "bird_age_days", 0) or 0), 1),
                                        "avg_weight_kg": round(float(x.average_weight_kg), 2)
                                        if getattr(x, "average_weight_kg", None)
                                        else None,
                                    }
                                    for x in sorted(farm_matches, key=lambda i: getattr(i, "barn_number", 0))[:10]
                                ],
                            }
            except Exception as e:
                print(f"[ROXI] Error consultando saldos de Pecuaria: {e}")

        if order_context:
            snapshot["contexto_ui"] = order_context

        # Enriquecimiento ejecutivo para Gerente General o consultas de alto nivel
        if user_role == "gerente_general" or (norm_query and any(k in norm_query for k in ("kpi", "gerent", "ejecutiv", "directiv", "ranking", "desempen", "cumplimiento", "tonelad"))):
            if self.db is not None:
                try:
                    from app.modules.gerencia_general.application.service import GerenciaGeneralService
                    gg_service = GerenciaGeneralService(self.db)
                    gg_rep = await gg_service.get_consolidated_report()
                    snapshot["gerencia_ejecutiva"] = {
                        "total_birds_sold": gg_rep.kpis.total_birds_sold,
                        "total_tons_sold": gg_rep.kpis.total_tons_sold,
                        "fulfillment_rate": gg_rep.kpis.fulfillment_rate,
                        "birds_in_stock": gg_rep.kpis.birds_in_stock,
                        "active_barns": gg_rep.kpis.active_barns,
                        "avg_weight_kg": gg_rep.kpis.avg_weight_kg,
                        "top_clients": [c.model_dump() for c in gg_rep.sales.top_clients[:5]],
                        "sellers_ranking": [s.model_dump() for s in gg_rep.staff.sellers_ranking[:5]],
                        "drivers_performance": [d.model_dump() for d in gg_rep.staff.drivers_performance[:5]],
                        "logistics": gg_rep.logistics.model_dump(),
                    }
                except Exception as e:
                    print(f"[ROXI] Error enriqueciendo contexto ejecutivo: {e}")

        return snapshot

    async def chat(self, req: RoxiChatRequest) -> RoxiChatResponse:
        """Responde consultas conversacionales del Vendedor o Gestor con KPIs reales."""
        user_role = req.user_role or "vendedor"
        snapshot = await self._build_operational_snapshot(
            order_id=req.order_id,
            order_context=req.order_context,
            user_role=user_role,
            query_text=req.message,
        )
        history_list = [{"role": h.role, "text": h.text} for h in (req.history or [])[-6:]]
        res_dict = await self.gemini_client.chat(
            request_msg=req.message,
            user_role=user_role,
            context=snapshot,
            history=history_list,
        )
        res_dict["kpis_snapshot"] = snapshot
        return RoxiChatResponse.model_validate(res_dict)
