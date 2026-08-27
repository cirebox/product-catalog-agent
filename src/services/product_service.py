"""
Product Service — Product Catalog Agent
CRUD de produtos no SQLite com reindexação automática do ChromaDB.
"""

import csv
import io
import logging
import unicodedata
from datetime import datetime
from typing import List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


def _remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


class ProductService:
    """Gerencia produtos no SQLite e mantém ChromaDB sincronizado."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def create(
        self,
        ref: str,
        description: str,
        price: float = 0,
        cost_price: float = 0,
        margin: float = 0,
        stock: int = 0,
        manufacturer: str = "",
        material: str = "",
        size: str = "",
        category: str = "",
    ) -> dict:
        """Cadastra um novo produto. Preço = custo + (custo * margem / 100)."""
        now = datetime.utcnow().isoformat()

        # Calcular preço de venda se cost_price e margin fornecidos
        if cost_price > 0 and margin > 0:
            price = round(cost_price + (cost_price * margin / 100), 2)
        elif cost_price > 0 and price == 0:
            price = cost_price

        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """INSERT INTO products
                       (ref, description, price, cost_price, margin, stock,
                        manufacturer, material, size, category,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (ref, description, price, cost_price, margin, stock,
                     manufacturer, material, size, category, now, now),
                )
                await db.commit()
                logger.info("Product created: ref=%s", ref)
                return await self.get_by_ref(ref)
            except aiosqlite.IntegrityError:
                raise ValueError(f"Product with ref '{ref}' already exists")

    async def get_by_ref(self, ref: str) -> Optional[dict]:
        """Busca produto por referência."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM products WHERE ref = ? AND deleted_at IS NULL",
                (ref,),
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def search_products(self, query: str, limit: int = 10) -> List[dict]:
        """Busca por referência ou descrição, ignorando caixa e acentos."""
        normalized_query = _remove_accents(query.strip()).lower()
        if not normalized_query:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.create_function("remove_accents", 1, _remove_accents)
            pattern = f"%{normalized_query}%"
            async with db.execute(
                """SELECT * FROM products
                   WHERE deleted_at IS NULL
                     AND (LOWER(remove_accents(ref)) LIKE ?
                          OR LOWER(remove_accents(description)) LIKE ?)
                   ORDER BY CASE WHEN LOWER(remove_accents(ref)) = ? THEN 0 ELSE 1 END,
                            ref
                   LIMIT ?""",
                (pattern, pattern, normalized_query, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def list_products(
        self,
        search: str = None,
        category: str = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Lista produtos com filtros e paginação."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            where_clauses = ["deleted_at IS NULL"]
            params: list = []

            if search:
                where_clauses.append("(description LIKE ? OR ref LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

            if category:
                where_clauses.append("category = ?")
                params.append(category)

            where_sql = " AND ".join(where_clauses)

            # Count total
            count_sql = f"SELECT COUNT(*) FROM products WHERE {where_sql}"
            async with db.execute(count_sql, params) as cursor:
                total = (await cursor.fetchone())[0]

            # Fetch page
            offset = (page - 1) * limit
            query_sql = f"""
                SELECT * FROM products
                WHERE {where_sql}
                ORDER BY ref
                LIMIT ? OFFSET ?
            """
            async with db.execute(query_sql, params + [limit, offset]) as cursor:
                rows = await cursor.fetchall()

            items = [dict(row) for row in rows]
            pages = (total + limit - 1) // limit if limit > 0 else 1

            return {
                "items": items,
                "total": total,
                "page": page,
                "pages": pages,
            }

    async def update(self, ref: str, **fields) -> dict:
        """Atualiza um produto existente."""
        allowed_fields = {
            "description", "price", "cost_price", "margin", "stock",
            "manufacturer", "material", "size", "category",
        }
        updates = {k: v for k, v in fields.items() if k in allowed_fields and v is not None}

        if not updates:
            raise ValueError("No valid fields to update")

        # Recalcular preço se cost_price ou margin mudaram
        if "cost_price" in updates or "margin" in updates:
            # Buscar valores atuais
            current = await self.get_by_ref(ref)
            cp = updates.get("cost_price", current.get("cost_price", 0))
            mg = updates.get("margin", current.get("margin", 0))
            if cp > 0 and mg > 0:
                updates["price"] = round(cp + (cp * mg / 100), 2)

        updates["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [ref]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE products SET {set_clause} WHERE ref = ? AND deleted_at IS NULL",
                values,
            )
            await db.commit()

        logger.info("Product updated: ref=%s fields=%s", ref, list(updates.keys()))
        return await self.get_by_ref(ref)

    async def delete(self, ref: str) -> bool:
        """Soft delete de um produto."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE products SET deleted_at = CURRENT_TIMESTAMP
                   WHERE ref = ? AND deleted_at IS NULL""",
                (ref,),
            )
            await db.commit()

        logger.info("Product deleted (soft): ref=%s", ref)
        return True

    async def reduce_stock(self, ref: str, quantity: int) -> dict:
        """Reduz estoque de um produto (baixa)."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT stock FROM products WHERE ref = ? AND deleted_at IS NULL",
                (ref,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Product '{ref}' not found")

                current_stock = row["stock"]
                if current_stock < quantity:
                    raise ValueError(
                        f"Insufficient stock: has {current_stock}, requested {quantity}"
                    )

            new_stock = current_stock - quantity
            await db.execute(
                """UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE ref = ? AND deleted_at IS NULL""",
                (new_stock, ref),
            )
            await db.commit()

        logger.info("Stock reduced: ref=%s %d→%d", ref, current_stock, new_stock)
        return await self.get_by_ref(ref)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def count(self) -> int:
        """Conta produtos ativos."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL"
            ) as cursor:
                return (await cursor.fetchone())[0]

    async def count_by_category(self, category: str) -> int:
        """Conta produtos ativos de uma categoria específica."""
        category_lower = _remove_accents(category.lower().strip())
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND LOWER(category) = ?",
                (category_lower,),
            ) as cursor:
                return (await cursor.fetchone())[0]

    async def list_all_active(self) -> List[dict]:
        """Retorna todos os produtos ativos (para RAG indexing)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM products WHERE deleted_at IS NULL ORDER BY ref"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # CSV import / export
    # ------------------------------------------------------------------

    async def upsert_from_csv(self, csv_content: str) -> dict:
        """Importa CSV fazendo update ou insert pelo ref.
        Formato CSV: ref,description,price,stock,manufacturer,material,size,category[,category_id]
        Retorna {created, updated, errors}.
        """
        created = 0
        updated = 0
        errors = []

        # Remover BOM se presente
        if csv_content and csv_content[0] == '\ufeff':
            csv_content = csv_content[1:]

        reader = csv.reader(io.StringIO(csv_content), delimiter=",", quotechar='"')
        for i, row in enumerate(reader, 1):
            if len(row) < 3:
                errors.append(f"Linha {i}: dados insuficientes (mínimo: ref,descrição,preço)")
                continue

            ref = row[0].strip()
            desc = row[1].strip()
            price_str = row[2].strip().replace(",", ".")
            stock_str = row[3].strip() if len(row) > 3 else "0"
            manufacturer = row[4].strip() if len(row) > 4 else ""
            material = row[5].strip() if len(row) > 5 else ""
            size = row[6].strip() if len(row) > 6 else ""
            category = row[7].strip() if len(row) > 7 else ""

            try:
                price = float(price_str)
            except ValueError:
                errors.append(f"Linha {i}: preço inválido '{price_str}'")
                continue

            try:
                stock = int(stock_str)
            except ValueError:
                stock = 0

            # cost_price e margin são preenchidos manualmente (não estão no CSV)
            cost_price = 0.0
            margin = 0.0

            # Se category não estiver vazia, garantir que existe na tabela categories
            if category:
                await self._ensure_category_exists(category)

            existing = await self.get_by_ref(ref)
            try:
                if existing:
                    await self.update(
                        ref,
                        description=desc,
                        price=price,
                        cost_price=cost_price,
                        margin=margin,
                        stock=stock,
                        category=category,
                        manufacturer=manufacturer,
                        material=material,
                        size=size,
                    )
                    updated += 1
                else:
                    await self.create(
                        ref=ref,
                        description=desc,
                        price=price,
                        cost_price=cost_price,
                        margin=margin,
                        stock=stock,
                        category=category,
                        manufacturer=manufacturer,
                        material=material,
                        size=size,
                    )
                    created += 1
            except Exception as e:
                errors.append(f"Linha {i} ({ref}): {str(e)}")

        logger.info("CSV upsert: %d created, %d updated, %d errors", created, updated, len(errors))
        return {"created": created, "updated": updated, "errors": errors}

    async def _ensure_category_exists(self, category_name: str) -> None:
        """Garante que a categoria existe na tabela categories. Cria se não existir."""
        if not category_name:
            return
        async with aiosqlite.connect(self.db_path) as db:
            # Verificar se já existe
            async with db.execute(
                "SELECT id FROM categories WHERE name = ?", (category_name,)
            ) as cursor:
                exists = await cursor.fetchone()
                if exists:
                    return
            # Criar categoria se não existir
            try:
                await db.execute(
                    "INSERT INTO categories (name, description) VALUES (?, ?)",
                    (category_name, ""),
                )
                await db.commit()
                logger.info("Auto-created category: %s", category_name)
            except aiosqlite.IntegrityError:
                # Categoria já foi criada por outra thread
                pass

    async def seed_from_csv(self, csv_path: str) -> int:
        """Importa produtos do CSV para o SQLite. Retorna quantidade importada.

        Formato CSV: ref,description,price,stock,manufacturer,material,size,category
        """
        import os
        if not os.path.exists(csv_path):
            logger.warning("CSV not found: %s", csv_path)
            return 0

        count = 0
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')
            for row in reader:
                if len(row) < 3:
                    continue

                ref = row[0].strip()
                desc = row[1].strip()
                price_str = row[2].strip().replace(",", ".")
                stock_str = row[3].strip() if len(row) > 3 else "0"
                manufacturer = row[4].strip() if len(row) > 4 else ""
                material = row[5].strip() if len(row) > 5 else ""
                size = row[6].strip() if len(row) > 6 else ""
                category = row[7].strip() if len(row) > 7 else ""

                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                try:
                    stock = int(stock_str)
                except ValueError:
                    stock = 0

                # cost_price = price (margem 0 por padrão)
                cost_price = price

                # Garantir que categoria existe
                if category:
                    await self._ensure_category_exists(category)

                # Skip if already exists
                existing = await self.get_by_ref(ref)
                if existing:
                    continue

                try:
                    await self.create(
                        ref=ref,
                        description=desc,
                        price=price,
                        cost_price=cost_price,
                        margin=0,
                        stock=stock,
                        category=category,
                        manufacturer=manufacturer,
                        material=material,
                        size=size,
                    )
                    count += 1
                except Exception as e:
                    logger.error("Failed to seed product %s: %s", ref, e)

        logger.info("Seeded %d products from CSV", count)
        return count

    async def export_csv(self, path: str) -> str:
        """Exporta produtos ativos para CSV. Retorna o path do arquivo."""
        products = await self.list_all_active()

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=",", quotechar='"')
            for p in products:
                price_str = f"{p['price']:.2f}".replace(".", ",")
                writer.writerow([
                    p["ref"],
                    p["description"],
                    price_str,
                    p["stock"],
                    p.get("manufacturer", ""),
                    p.get("material", ""),
                    p.get("size", ""),
                    p.get("category", ""),
                ])

        logger.info("Exported %d products to %s", len(products), path)
        return path
