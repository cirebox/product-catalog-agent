"""
Sale Service — Product Catalog Agent
Gerencia vendas no SQLite (substitui order_service + payment_service).
"""

import json
import logging
import uuid
from datetime import datetime, date, timedelta
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# Prazos de pagamento em dias
PAYMENT_DAYS = {"15": 15, "30": 30, "60": 60, "90": 90}


class SaleService:
    """Gerencia vendas no SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create_sale(
        self,
        items: list,
        customer_id: str = None,
        payment_method: str = "pix",
        discount: float = 0,
        payment_days: int = None,
        session_id: str = None,
    ) -> dict:
        """
        Cria uma nova venda.
        - items: [{"ref": "CAL-001", "description": "...", "price": 29.90, "quantity": 2}]
        - payment_method: 'pix'|'cartao'|'dinheiro'|'prazo'
        - payment_days: 15|30|60|90 (apenas para 'prazo')
        """
        # Validação: prazo exige cliente
        if payment_method == "prazo" and not customer_id:
            raise ValueError("Venda a prazo requer cliente identificado")

        # Validar método de pagamento
        valid_methods = {"pix", "cartao", "dinheiro", "prazo"}
        if payment_method not in valid_methods:
            raise ValueError(f"Método inválido: {payment_method}. Use: {valid_methods}")

        # Validar payment_days para prazo
        valid_days = {15, 30, 60, 90}
        if payment_method == "prazo" and payment_days not in valid_days:
            raise ValueError(f"Prazo inválido: {payment_days}. Use: {valid_days}")

        sale_id = str(uuid.uuid4())
        sale_date = date.today().isoformat()

        # Calcular total
        total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
        total = round(total - discount, 2)

        # Calcular due_date se prazo
        due_date = None
        if payment_method == "prazo" and payment_days:
            due_date = (date.today() + timedelta(days=payment_days)).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # Inserir venda
            await db.execute(
                """INSERT INTO sales
                   (id, customer_id, session_id, total, discount, payment_method,
                    payment_days, sale_date, due_date, payment_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sale_id,
                    customer_id,
                    session_id,
                    total,
                    discount,
                    payment_method,
                    payment_days,
                    sale_date,
                    due_date,
                    "pendente",
                ),
            )

            # Inserir itens
            for item in items:
                item_total = item.get("price", 0) * item.get("quantity", 1)
                await db.execute(
                    """INSERT INTO sale_items
                       (sale_id, product_id, product_name, variant_color,
                        variant_size, quantity, unit_price, cost_price, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        sale_id,
                        item.get("ref", ""),
                        item.get("description", ""),
                        item.get("color", ""),
                        item.get("size", ""),
                        item.get("quantity", 1),
                        item.get("price", 0),
                        item.get("cost_price", 0),
                        round(item_total, 2),
                    ),
                )

            # Baixa estoque
            for item in items:
                ref = item.get("ref", "")
                qty = item.get("quantity", 1)
                await db.execute(
                    """UPDATE products
                       SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP
                       WHERE ref = ? AND deleted_at IS NULL AND stock >= ?""",
                    (qty, ref, qty),
                )

            await db.commit()

        logger.info(
            "Sale created: %s (total: R$%.2f, method: %s)",
            sale_id, total, payment_method,
        )
        return await self.get_sale(sale_id)

    async def get_sale(self, sale_id: str) -> Optional[dict]:
        """Busca venda por ID com itens."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                "SELECT * FROM sales WHERE id = ?", (sale_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                sale = dict(row)

            # Buscar itens
            async with db.execute(
                "SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,)
            ) as cursor:
                items = [dict(r) for r in await cursor.fetchall()]
                sale["items"] = items

            return sale

    async def list_sales(
        self,
        customer_id: str = None,
        payment_status: str = None,
        date_from: str = None,
        date_to: str = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Lista vendas com filtros e paginação."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            where_clauses = []
            params: list = []

            if customer_id:
                where_clauses.append("s.customer_id = ?")
                params.append(customer_id)

            if payment_status:
                where_clauses.append("s.payment_status = ?")
                params.append(payment_status)

            if date_from:
                where_clauses.append("s.sale_date >= ?")
                params.append(date_from)

            if date_to:
                where_clauses.append("s.sale_date <= ?")
                params.append(date_to)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            count_sql = f"SELECT COUNT(*) FROM sales s WHERE {where_sql}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            offset = (page - 1) * limit
            query_sql = f"""
                SELECT s.*, c.name as customer_name, c.phone as customer_phone
                FROM sales s
                LEFT JOIN customers c ON s.customer_id = c.id
                WHERE {where_sql}
                ORDER BY s.sale_date DESC, s.created_at DESC
                LIMIT ? OFFSET ?
            """
            async with db.execute(query_sql, params + [limit, offset]) as cursor:
                rows = await cursor.fetchall()

            items = []
            for row in rows:
                sale = dict(row)
                # Buscar itens da venda
                async with db.execute(
                    "SELECT * FROM sale_items WHERE sale_id = ?", (sale["id"],)
                ) as items_cursor:
                    sale["items"] = [dict(r) for r in await items_cursor.fetchall()]
                items.append(sale)

            pages = (total + limit - 1) // limit if limit > 0 else 1

            return {
                "items": items,
                "total": total,
                "page": page,
                "pages": pages,
            }

    async def confirm_payment(
        self,
        sale_id: str,
        paid_date: str = None,
        paid_amount: float = None,
        payment_method: str = None,
        payment_note: str = None,
    ) -> dict:
        """Confirma pagamento de uma venda."""
        sale = await self.get_sale(sale_id)
        if not sale:
            raise ValueError(f"Venda '{sale_id}' não encontrada")

        if sale["payment_status"] == "pago":
            raise ValueError(f"Venda '{sale_id}' já foi paga")

        if not paid_date:
            paid_date = date.today().isoformat()

        if not paid_amount:
            paid_amount = sale["total"]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE sales
                   SET payment_status = 'pago',
                       paid_date = ?,
                       paid_amount = ?,
                       payment_note = ?
                   WHERE id = ?""",
                (paid_date, paid_amount, payment_note, sale_id),
            )
            await db.commit()

        logger.info("Payment confirmed for sale %s: R$%.2f", sale_id, paid_amount)
        return await self.get_sale(sale_id)

    async def get_daily_report(self, report_date: str = None) -> dict:
        """Gera relatório do dia."""
        if not report_date:
            report_date = date.today().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            # Total de vendas do dia
            async with db.execute(
                """SELECT COUNT(*), COALESCE(SUM(total), 0)
                   FROM sales WHERE sale_date = ?""",
                (report_date,),
            ) as cursor:
                row = await cursor.fetchone()
                total_orders = row[0]
                total_revenue = row[1]

            # Vendas por método
            async with db.execute(
                """SELECT payment_method, COUNT(*), COALESCE(SUM(total), 0)
                   FROM sales WHERE sale_date = ?
                   GROUP BY payment_method""",
                (report_date,),
            ) as cursor:
                rows = await cursor.fetchall()
                by_method = {row[0]: {"count": row[1], "total": row[2]} for row in rows}

            # Vendas pagas no dia
            async with db.execute(
                """SELECT COUNT(*), COALESCE(SUM(paid_amount), 0)
                   FROM sales WHERE paid_date = ?""",
                (report_date,),
            ) as cursor:
                row = await cursor.fetchone()
                paid_count = row[0]
                paid_total = row[1]

            # Pendentes
            async with db.execute(
                """SELECT COUNT(*), COALESCE(SUM(total), 0)
                   FROM sales WHERE payment_status = 'pendente'"""
            ) as cursor:
                row = await cursor.fetchone()
                pending_count = row[0]
                pending_total = row[1]

            return {
                "date": report_date,
                "sales": {
                    "count": total_orders,
                    "total": round(total_revenue, 2),
                    "by_method": by_method,
                },
                "payments_received": {
                    "count": paid_count,
                    "total": round(paid_total, 2),
                },
                "pending": {
                    "count": pending_count,
                    "total": round(pending_total, 2),
                },
            }

    async def simulate_installments(self, amount: float, installments: int) -> dict:
        """Simula parcelamento."""
        if installments < 1:
            installments = 1

        installment_value = amount / installments
        return {
            "amount": round(amount, 2),
            "installments": installments,
            "installment_value": round(installment_value, 2),
            "total": round(amount, 2),
            "details": [
                {"number": i + 1, "value": round(installment_value, 2)}
                for i in range(installments)
            ],
        }
