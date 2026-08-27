"""
Customer Service — Product Catalog Agent
Gerencia clientes, observações e fiado no SQLite.
"""

import logging
import uuid
from datetime import datetime, date
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


class CustomerService:
    """Gerencia clientes e suas observações no SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # -------------------------------------------------------------------------
    # CRUD de Clientes
    # -------------------------------------------------------------------------

    async def create(self, name: str, phone: str, email: str = None) -> dict:
        """Cria um novo cliente. Telefone deve ser único."""
        customer_id = str(uuid.uuid4())

        # Verificar se telefone já existe
        existing = await self.get_by_phone(phone)
        if existing:
            raise ValueError(f"Telefone '{phone}' já cadastrado para {existing['name']}")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO customers (id, name, phone, email)
                   VALUES (?, ?, ?, ?)""",
                (customer_id, name.strip(), phone.strip(), email.strip() if email else None),
            )
            await db.commit()

        logger.info("Customer created: %s (%s)", name, phone)
        return await self.get_by_id(customer_id)

    async def get_by_id(self, customer_id: str) -> Optional[dict]:
        """Busca cliente por ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_by_phone(self, phone: str) -> Optional[dict]:
        """Busca cliente por telefone."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM customers WHERE phone = ?", (phone.strip(),)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_customers(
        self, search: str = None, page: int = 1, limit: int = 20
    ) -> dict:
        """Lista clientes com busca por aproximação em nome ou telefone."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            where_clauses = []
            params: list = []

            if search:
                where_clauses.append("(name LIKE ? OR phone LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            count_sql = f"SELECT COUNT(*) FROM customers WHERE {where_sql}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * limit
            query_sql = f"""
                SELECT * FROM customers
                WHERE {where_sql}
                ORDER BY name ASC
                LIMIT ? OFFSET ?
            """
            async with db.execute(query_sql, params + [limit, offset]) as cursor:
                rows = await cursor.fetchall()

            pages = (total + limit - 1) // limit if limit > 0 else 1

            return {
                "items": [dict(row) for row in rows],
                "total": total,
                "page": page,
                "pages": pages,
            }

    async def list_recent(self, limit: int = 10) -> list:
        """Retorna clientes com última compra recente."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT c.*,
                          s.sale_date as last_sale_date,
                          s.total as last_sale_total
                   FROM customers c
                   LEFT JOIN sales s ON s.customer_id = c.id
                   WHERE s.id = (
                       SELECT s2.id FROM sales s2
                       WHERE s2.customer_id = c.id
                       ORDER BY s2.sale_date DESC LIMIT 1
                   )
                   ORDER BY s.sale_date DESC
                   LIMIT ?""",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update(self, customer_id: str, **fields) -> dict:
        """Atualiza dados do cliente."""
        allowed = {"name", "phone", "email"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}

        if not updates:
            raise ValueError("Nenhum campo para atualizar")

        # Se atualizar telefone, verificar unicidade
        if "phone" in updates:
            existing = await self.get_by_phone(updates["phone"])
            if existing and existing["id"] != customer_id:
                raise ValueError(f"Telefone '{updates['phone']}' já cadastrado")

        set_clauses = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [customer_id]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""UPDATE customers
                    SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?""",
                values,
            )
            await db.commit()

        return await self.get_by_id(customer_id)

    async def delete(self, customer_id: str) -> bool:
        """Remove cliente (hard delete)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            await db.commit()
            return True

    # -------------------------------------------------------------------------
    # Observações do Cliente
    # -------------------------------------------------------------------------

    async def add_note(
        self,
        customer_id: str,
        content: str,
        note_type: str = "observacao",
        pinned: bool = False,
    ) -> dict:
        """Adiciona observação ao cliente."""
        # Validar tipo
        valid_types = {"observacao", "preferencia", "pedido_especial"}
        if note_type not in valid_types:
            raise ValueError(f"Tipo inválido: {note_type}. Use: {valid_types}")

        # Se quer fixar, verificar limite de 3
        if pinned:
            pinned_count = await self._count_pinned(customer_id)
            if pinned_count >= 3:
                raise ValueError("Máximo de 3 observações fixadas. Desafixe uma primeiro.")

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO customer_notes (customer_id, note_type, content, pinned)
                   VALUES (?, ?, ?, ?)""",
                (customer_id, note_type, content.strip(), 1 if pinned else 0),
            )
            note_id = cursor.lastrowid
            await db.commit()

        logger.info("Note added for customer %s: type=%s", customer_id, note_type)
        return await self.get_note(customer_id, note_id)

    async def get_note(self, customer_id: str, note_id: int) -> Optional[dict]:
        """Busca uma nota específica."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM customer_notes WHERE id = ? AND customer_id = ?",
                (note_id, customer_id),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_notes(
        self, customer_id: str, note_type: str = None, status: str = None
    ) -> list:
        """Lista notas do cliente. Fixadas primeiro."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            where_clauses = ["customer_id = ?"]
            params: list = [customer_id]

            if note_type:
                where_clauses.append("note_type = ?")
                params.append(note_type)

            if status:
                where_clauses.append("status = ?")
                params.append(status)

            where_sql = " AND ".join(where_clauses)

            query_sql = f"""
                SELECT * FROM customer_notes
                WHERE {where_sql}
                ORDER BY pinned DESC, created_at DESC
            """
            async with db.execute(query_sql, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_note(self, customer_id: str, note_id: int, **fields) -> dict:
        """Atualiza uma nota."""
        allowed = {"content", "note_type", "pinned", "status"}
        updates = {k: v for k, v in fields.items() if k in allowed}

        if not updates:
            raise ValueError("Nenhum campo para atualizar")

        # Se quer fixar, verificar limite
        if updates.get("pinned"):
            note = await self.get_note(customer_id, note_id)
            if note and not note["pinned"]:
                pinned_count = await self._count_pinned(customer_id)
                if pinned_count >= 3:
                    raise ValueError("Máximo de 3 observações fixadas.")

        # Converter bool para int para pinned
        if "pinned" in updates:
            updates["pinned"] = 1 if updates["pinned"] else 0

        set_clauses = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [note_id, customer_id]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""UPDATE customer_notes
                    SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND customer_id = ?""",
                values,
            )
            await db.commit()

        return await self.get_note(customer_id, note_id)

    async def delete_note(self, customer_id: str, note_id: int) -> bool:
        """Remove uma nota."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM customer_notes WHERE id = ? AND customer_id = ?",
                (note_id, customer_id),
            )
            await db.commit()
            return True

    async def _count_pinned(self, customer_id: str) -> int:
        """Conta notas fixadas do cliente."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM customer_notes WHERE customer_id = ? AND pinned = 1",
                (customer_id,),
            ) as cursor:
                return (await cursor.fetchone())[0]

    # -------------------------------------------------------------------------
    # Alertas do PDV
    # -------------------------------------------------------------------------

    async def get_alerts(self, customer_id: str) -> dict:
        """Retorna notas fixadas + pedidos especiais abertos para exibir no PDV."""
        pinned = await self.list_notes(customer_id)
        pinned = [n for n in pinned if n["pinned"]]

        special_open = await self.list_notes(
            customer_id, note_type="pedido_especial", status="aberto"
        )

        return {
            "pinned_notes": pinned,
            "open_special_orders": special_open,
        }

    # -------------------------------------------------------------------------
    # Fiado / Contas a Receber
    # -------------------------------------------------------------------------

    async def get_credit(self, customer_id: str) -> dict:
        """Retorna vendas a prazo pendentes e histórico de pagamentos."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Vendas pendentes
            today = date.today().isoformat()
            async with db.execute(
                """SELECT * FROM sales
                   WHERE customer_id = ?
                     AND payment_method = 'prazo'
                     AND payment_status = 'pendente'
                   ORDER BY due_date ASC""",
                (customer_id,),
            ) as cursor:
                pending_rows = await cursor.fetchall()

            pending = []
            for row in pending_rows:
                sale = dict(row)
                # Calcular status baseado na data
                if sale["due_date"] and sale["due_date"] < today:
                    from datetime import date as d
                    due = d.fromisoformat(sale["due_date"])
                    today_d = d.fromisoformat(today)
                    days_overdue = (today_d - due).days
                    sale["status"] = "atrasado"
                    sale["days_overdue"] = days_overdue
                else:
                    sale["status"] = "em_dia"
                pending.append(sale)

            # Total pendente
            total_pending = sum(s["total"] for s in pending)

            # Histórico de pagos
            async with db.execute(
                """SELECT * FROM sales
                   WHERE customer_id = ?
                     AND payment_status = 'pago'
                   ORDER BY paid_date DESC
                   LIMIT 20""",
                (customer_id,),
            ) as cursor:
                history_rows = await cursor.fetchall()
                history = [dict(row) for row in history_rows]

            return {
                "total_pending": round(total_pending, 2),
                "pending": pending,
                "history": history,
            }

    # -------------------------------------------------------------------------
    # Relatório de Cobrança (todos os clientes com fiado)
    # -------------------------------------------------------------------------

    async def get_all_pending_credit(self) -> list:
        """Retorna todos os clientes com fiado pendente, ordenado por vencimento."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            today = date.today().isoformat()

            async with db.execute(
                """SELECT
                        c.id as customer_id,
                        c.name as customer_name,
                        c.phone as customer_phone,
                        s.id as sale_id,
                        s.total,
                        s.sale_date,
                        s.due_date,
                        s.payment_status
                   FROM sales s
                   JOIN customers c ON s.customer_id = c.id
                   WHERE s.payment_method = 'prazo'
                     AND s.payment_status = 'pendente'
                   ORDER BY s.due_date ASC"""
            ) as cursor:
                rows = await cursor.fetchall()

            results = []
            for row in rows:
                item = dict(row)
                # Calcular status
                if item["due_date"] and item["due_date"] < today:
                    from datetime import date as d
                    due = d.fromisoformat(item["due_date"])
                    today_d = d.fromisoformat(today)
                    item["status"] = "atrasado"
                    item["days_overdue"] = (today_d - due).days
                else:
                    item["status"] = "em_dia"
                    item["days_overdue"] = 0
                results.append(item)

            # Agrupar por cliente
            customers_map = {}
            for item in results:
                cid = item["customer_id"]
                if cid not in customers_map:
                    customers_map[cid] = {
                        "customer_id": cid,
                        "customer_name": item["customer_name"],
                        "customer_phone": item["customer_phone"],
                        "total_pending": 0,
                        "sales": [],
                        "oldest_due": item["due_date"],
                        "has_overdue": False,
                    }
                customers_map[cid]["total_pending"] += item["total"]
                customers_map[cid]["sales"].append({
                    "sale_id": item["sale_id"],
                    "total": item["total"],
                    "sale_date": item["sale_date"],
                    "due_date": item["due_date"],
                    "status": item["status"],
                    "days_overdue": item["days_overdue"],
                })
                if item["status"] == "atrasado":
                    customers_map[cid]["has_overdue"] = True
                if item["due_date"] and (not customers_map[cid]["oldest_due"] or item["due_date"] < customers_map[cid]["oldest_due"]):
                    customers_map[cid]["oldest_due"] = item["due_date"]

            # Ordenar: atrasados primeiro, depois por vencimento
            results_list = sorted(
                customers_map.values(),
                key=lambda x: (0 if x["has_overdue"] else 1, x["oldest_due"] or "9999-99-99")
            )

            # Totais
            total_geral = sum(c["total_pending"] for c in results_list)
            total_atrasado = sum(
                c["total_pending"] for c in results_list if c["has_overdue"]
            )

            return {
                "customers": results_list,
                "summary": {
                    "total_customers": len(results_list),
                    "total_pending": round(total_geral, 2),
                    "total_overdue": round(total_atrasado, 2),
                },
            }
