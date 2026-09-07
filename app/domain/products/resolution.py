from dataclasses import dataclass
from typing import Protocol

from app.domain.products.product import Product


@dataclass(frozen=True, kw_only=True)
class ResolvedProduct:
    product: Product


class ProductResolver(Protocol):
    async def resolve(self, product: Product) -> ResolvedProduct: ...
