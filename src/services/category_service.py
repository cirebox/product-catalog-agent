"""
Category Service — Product Catalog Agent
Gerencia categorias de produtos no SQLite.
"""

import logging
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


class CategoryService:
    """Gerencia categorias de produtos."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def create(self, name: str, description: str = "") -> dict:
        """Cria uma nova categoria. Nome deve ser único."""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO categories (name, description) VALUES (?, ?)",
                    (name.strip(), description.strip()),
                )
                await db.commit()
                logger.info("Category created: %s", name)
                return await self.get_by_name(name.strip())
            except aiosqlite.IntegrityError:
                raise ValueError(f"Categoria '{name}' já existe")

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Busca categoria por nome."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM categories WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_all(self) -> list:
        """Lista todas as categorias ordenadas por nome."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM categories ORDER BY name"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update(self, name: str, new_name: str = None, description: str = None) -> dict:
        """Atualiza uma categoria."""
        category = await self.get_by_name(name)
        if not category:
            raise ValueError(f"Categoria '{name}' não encontrada")

        updates = {}
        if new_name and new_name.strip() != name:
            # Verificar se novo nome já existe
            existing = await self.get_by_name(new_name.strip())
            if existing:
                raise ValueError(f"Categoria '{new_name}' já existe")
            updates["name"] = new_name.strip()
        if description is not None:
            updates["description"] = description.strip()

        if not updates:
            return category

        set_clauses = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [name]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"UPDATE categories SET {set_clauses} WHERE name = ?",
                values,
            )
            await db.commit()

        final_name = updates.get("name", name)
        logger.info("Category updated: %s → %s", name, final_name)
        return await self.get_by_name(final_name)

    async def delete(self, name: str) -> bool:
        """Remove uma categoria (só se não houver produtos associados)."""
        async with aiosqlite.connect(self.db_path) as db:
            # Verificar se há produtos com esta categoria
            async with db.execute(
                "SELECT COUNT(*) FROM products WHERE category = ? AND deleted_at IS NULL",
                (name,),
            ) as cursor:
                count = (await cursor.fetchone())[0]
                if count > 0:
                    raise ValueError(
                        f"Não é possível excluir: {count} produto(s) usa(m) esta categoria"
                    )

            await db.execute("DELETE FROM categories WHERE name = ?", (name,))
            await db.commit()

        logger.info("Category deleted: %s", name)
        return True

    async def seed_defaults(self) -> int:
        """Cria categorias padrão se a tabela estiver vazia."""
        existing = await self.list_all()
        if existing:
            return 0

        defaults = [
            ("calcinhas", "Calcinhas femininas"),
            ("cuecas", "Cuecas masculinas"),
            ("sutiãs", "Sutiãs femininos"),
            ("camisetas", "Camisetas íntimas"),
            ("pijamas", "Pijamas e conjuntos"),
            ("meias", "Meias"),
            ("acessórios", "Acessórios diversos"),
        ]

        count = 0
        for name, desc in defaults:
            try:
                await self.create(name, desc)
                count += 1
            except ValueError:
                pass

        logger.info("Seeded %d default categories", count)
        return count
