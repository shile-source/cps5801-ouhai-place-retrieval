from dataclasses import dataclass

@dataclass(frozen=True)
class POI:
    poi_id: str
    name: str
    category: str = ''
    address: str = ''
    description: str = ''
    is_synthetic: bool = False

    @property
    def search_text(self) -> str:
        # 所有检索模型使用相同字段和顺序，缺失字段不填造信息。
        return '\n'.join(value.strip() for value in
                         (self.name, self.category, self.address, self.description)
                         if value.strip())
